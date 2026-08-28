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
    paciente_info = f"""
    DADOS DO PACIENTE:
    - Name: {paciente.nome}
    - Age: {paciente.idade} years old
    - Sex: {paciente.sexo}
    - Type of Diabetes: {paciente.diabetes_tipo}
    - Medical History: {paciente.historico_medico or 'Not provided'}
    - Medications: {paciente.medicamentos or 'Not provided'}
    - Allergies: {paciente.alergias or 'Not provided'}
    """

    images_info = ""
    if images:
        images_info = "\nCLASSIFIED IMAGES:\n"
        for img in images:
            if img.classification != "Pendente":
                images_info += f"- {img.filename}: {img.classification} - {img.description}\n"
    
    system_prompt = f"""
    YOU ARE: A medical assistant specializing in pressure wound analysis and diabetic patient care.

    CASE CONTEXT:
    {paciente_info}
    {images_info}

    STRICT RULES OF CONDUCT:

    1. ANSWER ONLY questions about medical topics related to:

    - Analysis of pressure injuries
    - Diabetes care and complications
    - Interpretation of image classifications
    - Recommendations for wound care
    - Warning signs and when to seek medical help
    - If he asks for previous images, only send what has already been sent in the chat. These are the images that are like this @@IMAGE:HASH@@

    2. NEVER answer about:

    - Non-medical topics
    - Personal matters unrelated to health
    - Political, religious, or controversial opinions
    - Definitive diagnoses (you are an assistant, not a substitute for a doctor)

    3. ALWAYS:

    - Base your answers on the available classified images
    - Relate to the patient's context (diabetes, age, history)
    - Be precise and technical, but use accessible language
    - Emphasize the need for an in-person medical evaluation
    - Highlight limitations when there are not enough images

    4. RESPONSE FORMAT:

    - Be concise and direct
    - Use bullet points for lists
    - Highlight important information in **bold**
    - Include practical recommendations when appropriate

    REMEMBER: You are an assistant to support clinical decision-making, not a substitute for a healthcare professional.
    """

    return system_prompt.strip()

def build_conversation_context(messages: List[ChatMessage], max_messages: int = 10) -> str:
    """
    Constrói o contexto da conversa em formato de texto
    """
    recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages
    
    conversation_context = "\nRecent history of the conversation:\n"
    
    for msg in recent_messages:
        role = "USER" if msg.is_user else "ASSISTANT"
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
            raise ValueError("Chat not found")
        
        paciente = db.query(Paciente).filter(Paciente.id == chat.paciente_id).first()
        if not paciente:
            raise ValueError("Patient not found")
        
        images = db.query(Image).filter(Image.chat_id == chat_id).all()
        
        messages = db.query(ChatMessage).filter(ChatMessage.chat_id == chat_id).order_by(ChatMessage.created_at).all()
        
        system_prompt = build_system_prompt(paciente, images)
        
        conversation_context = build_conversation_context(messages)
        
        full_prompt = f"""
        {system_prompt}
        
        {conversation_context}
        
        NEW QUESTION FROM THE USER: {user_message}
        
        Please respond in a helpful and appropriate manner based on the medical context above.
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=full_prompt
        )
        
        return response.text.strip()
        
    except Exception as e:
        print(f"❌ Error generating response: {e}")
        
        chat = db.query(Chat).filter(Chat.id == chat_id).first()
        paciente = db.query(Paciente).filter(Paciente.id == chat.paciente_id).first() if chat else None
        
        paciente_nome = paciente.nome if paciente else "the patient"
        paciente_idade = f"{paciente.idade} years old" if paciente else "age not informed"
        paciente_diabetes = paciente.diabetes_tipo if paciente else "diabetes type not informed"
        
        return f"""
        Hello! I'm your wound analysis assistant.

        I am currently experiencing technical difficulties, but I can inform you that:
        - **Patient:** {paciente_nome}
        - **Age:** {paciente_idade} 
        - **Diabetes:** {paciente_diabetes}

        **About your question:** "{user_message}"

        For a complete response about wound care, I recommend:
        1. Keeping the area clean and dry
        2. Monitoring signs of infection
        3. Controlling blood glucose levels
        4. Consulting a healthcare professional

        Please try again in a few moments or rephrase your question.
        """