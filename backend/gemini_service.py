import os
from dotenv import load_dotenv

load_dotenv(override=True, verbose=True)

def get_gemini_client():
    """
    Returns the Gemini client
    """
    try:
        from google import genai
        from google.genai import types

        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")

        client = genai.Client(api_key=api_key)
        return client
    except ImportError:
        raise ImportError("google-genai library not installed. Run: pip install google-genai")

def generate_chat_introduction(paciente_data):
    try:
        client = get_gemini_client()
        
        prompt = f"""
        You are a Clinical Decision Support Artificial Intelligence (CDSS) system specialized in the initial screening and classification of skin lesions.

        Based on the patient information below, generate a concise technical message, using strictly medical language, to be read and validated by a specialist physician presenting the patient below.
        
        PATIENT DATA:
        - Name: {paciente_data.get('nome', 'Not provided')}
        - Age: {paciente_data.get('idade', 'Not provided')} years old
        - Sex: {paciente_data.get('sexo', 'Not provided')}
        - Type of Diabetes: {paciente_data.get('diabetes_tipo', 'Not provided')}
        - Medical History: {paciente_data.get('historico_medico', 'Not provided')}
        - Medicaments: {paciente_data.get('medicamentos', 'Not provided')}
        - Allergies: {paciente_data.get('alergias', 'Not provided')}
        
       The message should:

        1. Briefly introduce yourself
        2. Confirm the patient's main information
        3. Explain that you are ready to analyze the lesions and answer questions
        4. Maintain a professional but welcoming tone
        5. Be concise (maximum 150 words)
        
        Please reply ONLY with the text of the message.
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt
        )
        
        return response.text.strip()
        
    except Exception as e:
        print(f"❌ Error generating message with Gemini: {e}")
        return f"""
        Hello! I am a Clinical Decision Support Artificial Intelligence (CDSS) system specialized in the initial screening and classification of skin lesions.
        
        Patient: {paciente_data.get('nome', 'Not provided')}
        Age: {paciente_data.get('idade', 'Not provided')} years old
        Type of Diabetes: {paciente_data.get('diabetes_tipo', 'Not provided')}

        I am here to analyze the images of the skin lesions and answer your questions about the follow-up. 
        Please share your concerns or ask questions about the case.
        """