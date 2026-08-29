import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from typing import List, Dict
from .models import Patient, ChatMessage, Image

load_dotenv(override=True, verbose=True)

def get_gemini_client():
    """
    Returns the Gemini client
    """
    try:
        from google import genai

        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found")

        client = genai.Client(api_key=api_key)
        return client
    except ImportError:
        raise ImportError("google-genai library not installed")

def build_system_prompt(patient: Patient, images: List[Image]) -> str:
    """
    Builds the system prompt from the patient's data and images
    """
    patient_info = f"""
    PATIENT DATA:
    - Name: {patient.name}
    - Age: {patient.age} years old
    - Sex: {patient.sex}
    - Type of Diabetes: {patient.diabetes_type}
    - Medical History: {patient.medical_history or 'Not provided'}
    - Medications: {patient.medications or 'Not provided'}
    - Allergies: {patient.allergies or 'Not provided'}
    """

    images_info = ""
    if images:
        images_info = "\nCLASSIFIED IMAGES:\n"
        for img in images:
            if img.classification != "Pending":
                images_info += f"- {img.filename}: {img.classification} - {img.description}\n"

    system_prompt = f"""
    YOU ARE: A medical assistant specializing in pressure wound analysis and diabetic patient care.

    CASE CONTEXT:
    {patient_info}
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
    Builds the conversation context as plain text
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
    Generates a Gemini response based on the chat history and patient context
    """
    try:
        client = get_gemini_client()

        # Fetch chat and patient data
        from .models import Chat
        chat = db.query(Chat).filter(Chat.id == chat_id).first()
        if not chat:
            raise ValueError("Chat not found")

        patient = db.query(Patient).filter(Patient.id == chat.patient_id).first()
        if not patient:
            raise ValueError("Patient not found")

        images = db.query(Image).filter(Image.chat_id == chat_id).all()

        messages = db.query(ChatMessage).filter(ChatMessage.chat_id == chat_id).order_by(ChatMessage.created_at).all()

        system_prompt = build_system_prompt(patient, images)

        conversation_context = build_conversation_context(messages)

        full_prompt = f"""
        {system_prompt}

        {conversation_context}

        NEW QUESTION FROM THE USER: {user_message}

        Please respond in a helpful and appropriate manner based on the medical context above.
        """

        response = client.models.generate_content(
            model='gemini-3.6-flash',
            contents=full_prompt
        )

        return response.text.strip()

    except Exception as e:
        print(f"❌ Error generating response: {e}")

        chat = db.query(Chat).filter(Chat.id == chat_id).first()
        patient = db.query(Patient).filter(Patient.id == chat.patient_id).first() if chat else None

        patient_name = patient.name if patient else "the patient"
        patient_age = f"{patient.age} years old" if patient else "age not informed"
        patient_diabetes = patient.diabetes_type if patient else "diabetes type not informed"

        return f"""
        Hello! I'm your wound analysis assistant.

        I am currently experiencing technical difficulties, but I can inform you that:
        - **Patient:** {patient_name}
        - **Age:** {patient_age}
        - **Diabetes:** {patient_diabetes}

        **About your question:** "{user_message}"

        For a complete response about wound care, I recommend:
        1. Keeping the area clean and dry
        2. Monitoring signs of infection
        3. Controlling blood glucose levels
        4. Consulting a healthcare professional

        Please try again in a few moments or rephrase your question.
        """
