import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv(override=True, verbose=True)

def get_gemini_client():
    """
    Retorna o cliente do Gemini
    """
    try:
        from google import genai
        from google.genai import types
        
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY não encontrada nas variáveis de ambiente")
        
        client = genai.Client(api_key=api_key)
        return client
    except ImportError:
        raise ImportError("Biblioteca google-genai não instalada. Execute: pip install google-genai")

def generate_chat_introduction(paciente_data):
    """
    Gera uma mensagem de introdução para o chat baseada nos dados do paciente
    
    Args:
        paciente_data: Dicionário com dados do paciente
    
    Returns:
        str: Mensagem de introdução gerada pelo Gemini
    """
    try:
        client = get_gemini_client()
        
        prompt = f"""
        Você é um sistema de Inteligência Artificial de Suporte à Decisão Clínica (CDSS) especializado na triagem e classificação inicial de lesões de pele. 
        
        Com base nas informações do paciente abaixo, gere uma mensagem técnica conciso, com linguagem estritamente médica, para ser lido e validado por um médico especialista apresentando o paciente abaixo.
        
        DADOS DO PACIENTE:
        - Nome: {paciente_data.get('nome', 'Não informado')}
        - Idade: {paciente_data.get('idade', 'Não informada')} anos
        - Sexo: {paciente_data.get('sexo', 'Não informado')}
        - Tipo de Diabetes: {paciente_data.get('diabetes_tipo', 'Não informado')}
        - Histórico Médico: {paciente_data.get('historico_medico', 'Nenhum histórico informado')}
        - Medicamentos: {paciente_data.get('medicamentos', 'Nenhum medicamento informado')}
        - Alergias: {paciente_data.get('alergias', 'Nenhuma alergia informada')}
        
        A mensagem deve:
        1. Se apresentar brevemente
        2. Confirmar os dados principais do paciente
        3. Explicar que está pronto para analisar as lesões e responder dúvidas
        4. Manter tom profissional mas acolhedor
        5. Ser concisa (máximo 150 palavras)
        
        Responda APENAS com o texto da mensagem.
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        return response.text.strip()
        
    except Exception as e:
        # Fallback em caso de erro
        print(f"❌ Erro ao gerar mensagem com Gemini: {e}")
        return f"""
        Olá! Eu sou um sistema de Inteligência Artificial de Suporte à Decisão Clínica (CDSS) especializado na triagem e classificação inicial de lesões de pele.

        Paciente: {paciente_data.get('nome', 'Não informado')}
        Idade: {paciente_data.get('idade', 'Não informada')} anos
        Tipo de Diabetes: {paciente_data.get('diabetes_tipo', 'Não informado')}

        Estou aqui para analisar as imagens das lesões e responder suas dúvidas sobre o acompanhamento. 
        Por favor, compartilhe suas preocupações ou faça perguntas sobre o caso.
        """