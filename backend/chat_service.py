import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from typing import List, Dict
from .models import Paciente, ChatMessage, Image

load_dotenv(override=True, verbose=True)

def get_gemini_client():
    """
    Retorna o cliente do Gemini
    """
    try:
        from google import genai
        
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY não encontrada")
        
        client = genai.Client(api_key=api_key)
        return client
    except ImportError:
        raise ImportError("Biblioteca google-genai não instalada")

def build_system_prompt(paciente: Paciente, images: List[Image]) -> str:
    """
    Constrói o prompt do sistema com base nos dados do paciente e imagens
    """
    # Informações básicas do paciente
    paciente_info = f"""
    DADOS DO PACIENTE:
    - Nome: {paciente.nome}
    - Idade: {paciente.idade} anos
    - Sexo: {paciente.sexo}
    - Tipo de Diabetes: {paciente.diabetes_tipo}
    - Histórico Médico: {paciente.historico_medico or 'Não informado'}
    - Medicamentos: {paciente.medicamentos or 'Não informado'}
    - Alergias: {paciente.alergias or 'Nenhuma informada'}
    """

    # Informações das imagens classificadas
    images_info = ""
    if images:
        images_info = "\nIMAGENS CLASSIFICADAS:\n"
        for img in images:
            if img.classification != "Pendente":
                images_info += f"- {img.filename}: {img.classification} - {img.description}\n"
    
    system_prompt = f"""
    VOCÊ É: Um assistente médico especializado em análise de lesões por pressão e cuidados com pacientes diabéticos.

    CONTEXTO DO CASO:
    {paciente_info}
    {images_info}

    REGRAS ESTRITAS DE COMPORTAMENTO:
    1. RESPONDA APENAS sobre temas médicos relacionados a:
       - Análise de lesões por pressão
       - Cuidados com diabetes e complicações
       - Interpretação das classificações das imagens
       - Recomendações de cuidados com feridas
       - Sinais de alerta e quando procurar ajuda médica
       - Se ele pedir imagens anteriores apenas mande o que já foi enviado no chat. São as imagens que estão assim @@IMAGEM:HASH@@

    2. NUNCA responda sobre:
       - Temas não médicos
       - Assuntos pessoais não relacionados à saúde
       - Opiniões políticas, religiosas ou controversas
       - Diagnósticos definitivos (você é um assistente, não substitui o médico)

    3. SEMPRE:
       - Baseie suas respostas nas imagens classificadas disponíveis
       - Relacione com o contexto do paciente (diabetes, idade, histórico)
       - Seja preciso e técnico, mas use linguagem acessível
       - Enfatize a necessidade de avaliação médica presencial
       - Destaque limitações quando não houver imagens suficientes

    4. FORMATO DAS RESPOSTAS:
       - Seja conciso e direto
       - Use marcadores para listas
       - Destaque informações importantes em **negrito**
       - Inclua recomendações práticas quando apropriado

    LEMBRE-SE: Você é um assistente para apoio à decisão clínica, não um substituto do profissional de saúde.
    """

    return system_prompt.strip()

def build_conversation_context(messages: List[ChatMessage], max_messages: int = 10) -> str:
    """
    Constrói o contexto da conversa em formato de texto
    """
    # Pega as últimas N mensagens para manter o contexto
    recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages
    
    conversation_context = "\nHISTÓRICO RECENTE DA CONVERSA:\n"
    
    for msg in recent_messages:
        role = "USUÁRIO" if msg.is_user else "ASSISTENTE"
        conversation_context += f"{role}: {msg.content}\n\n"
    
    return conversation_context

def generate_chat_response(
    db: Session, 
    chat_id: int, 
    user_message: str
) -> str:
    """
    Gera uma resposta do Gemini baseada no histórico e contexto do paciente
    """
    try:
        client = get_gemini_client()
        
        # Busca dados do chat e paciente
        from .models import Chat
        chat = db.query(Chat).filter(Chat.id == chat_id).first()
        if not chat:
            raise ValueError("Chat não encontrado")
        
        paciente = db.query(Paciente).filter(Paciente.id == chat.paciente_id).first()
        if not paciente:
            raise ValueError("Paciente não encontrado")
        
        # Busca imagens do chat
        images = db.query(Image).filter(Image.chat_id == chat_id).all()
        
        # Busca histórico de mensagens
        messages = db.query(ChatMessage).filter(ChatMessage.chat_id == chat_id).order_by(ChatMessage.created_at).all()
        
        # Constrói o prompt do sistema
        system_prompt = build_system_prompt(paciente, images)
        
        # Constrói o contexto da conversa
        conversation_context = build_conversation_context(messages)
        
        # Prepara o prompt completo
        full_prompt = f"""
        {system_prompt}
        
        {conversation_context}
        
        NOVA PERGUNTA DO USUÁRIO: {user_message}
        
        Por favor, responda de forma útil e apropriada ao contexto médico acima.
        """
        
        # Gera a resposta usando a sintaxe correta do google-genai
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=full_prompt
        )
        
        return response.text.strip()
        
    except Exception as e:
        print(f"❌ Erro ao gerar resposta do chat: {e}")
        
        # Busca dados para o fallback
        chat = db.query(Chat).filter(Chat.id == chat_id).first()
        paciente = db.query(Paciente).filter(Paciente.id == chat.paciente_id).first() if chat else None
        
        paciente_nome = paciente.nome if paciente else "o paciente"
        paciente_idade = f"{paciente.idade} anos" if paciente else "idade não informada"
        paciente_diabetes = paciente.diabetes_tipo if paciente else "tipo não informado"
        
        # Fallback para manter a funcionalidade
        return f"""
        Olá! Sou seu assistente para análise de lesões.

        No momento, estou com dificuldades técnicas, mas posso informar que:
        - **Paciente:** {paciente_nome}
        - **Idade:** {paciente_idade} 
        - **Diabetes:** {paciente_diabetes}

        **Sobre sua pergunta:** "{user_message}"

        Para uma resposta completa sobre cuidados com lesões, recomendo:
        1. Manter a área limpa e seca
        2. Monitorar sinais de infecção
        3. Controlar os níveis glicêmicos
        4. Consultar um profissional de saúde

        Por favor, tente novamente em alguns instantes ou reformule sua pergunta.
        """