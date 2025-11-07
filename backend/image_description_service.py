import os
import base64
import mimetypes
from dotenv import load_dotenv

load_dotenv(override=True, verbose=True)

# Métricas do nosso modelo (do seu CSV)
METRICAS_MODELO = {
    'BG': {'precision': 0.9615, 'recall': 1.0, 'f1-score': 0.9804},
    'D': {'precision': 0.8293, 'recall': 0.7391, 'f1-score': 0.7816},
    'N': {'precision': 0.9259, 'recall': 1.0, 'f1-score': 0.9615},
    'P': {'precision': 0.6429, 'recall': 0.2647, 'f1-score': 0.375},
    'S': {'precision': 0.6667, 'recall': 0.5714, 'f1-score': 0.6154},
    'V': {'precision': 0.6556, 'recall': 0.9516, 'f1-score': 0.7763}
}

def get_gemini_client():
    """
    Retorna o cliente do Gemini usando google-genai
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

def describe_image_with_analysis(image_path: str, dados_analise: dict):
    """
    Gera uma descrição técnica detalhada da imagem com base na análise do modelo
    """
    try:
        client = get_gemini_client()
        
        # Lê a imagem
        with open(image_path, "rb") as f:
            image_data = f.read()
        
        # 🔥 CORREÇÃO: Usa as chaves corretas do resultado
        classe_predita = dados_analise.get('classe_predita', 'Desconhecida')
        classe_traduzida = dados_analise.get('classe_traduzida', 'Desconhecida')
        confianca = dados_analise.get('confianca_predita_percentual', 'N/A')
        probabilidades = dados_analise.get('probabilidades_completas', {})
        
        # Prepara o prompt técnico
        prompt = f"""
        Você é um sistema de Inteligência Artificial de Suporte à Decisão Clínica (CDSS) especializado na triagem e classificação inicial de lesões de pele. Seu objetivo é gerar um PRÉ-LAUDO TÉCNICO e um RELATÓRIO DE RISCO conciso, com linguagem estritamente médica, para ser lido e validado por um médico especialista.

        INFORMAÇÕES DE ENTRADA DO MODELO DE CLASSIFICAÇÃO (VGG16 Fine-Tuned):
        1. CLASSE PREDITA: {classe_predita} ({classe_traduzida}) - Confiança: {confianca}
        2. VETOR DE PROBABILIDADES: {probabilidades}
        3. MÉTRICAS HISTÓRICAS DO MODELO:
           - Precision: {METRICAS_MODELO.get(classe_predita, {}).get('precision', 'N/A'):.4f}
           - Recall: {METRICAS_MODELO.get(classe_predita, {}).get('recall', 'N/A'):.4f}
           - F1-Score: {METRICAS_MODELO.get(classe_predita, {}).get('f1-score', 'N/A'):.4f}

        REQUISITOS OBRIGATÓRIOS PARA A RESPOSTA (Não exceder 300 palavras):

        * Identifique a classificação principal e a confiança do modelo.
        * Justifique. Descreva as características visuais da imagem que corroboram com a classificação {classe_predita} ({classe_traduzida}).
        * Realize uma análise diferencial. Comente as 2-3 classes com maior probabilidade após a principal, explicando brevemente as similaridades e diferenças.

        Formate a resposta de forma clara e técnica, usando marcadores quando apropriado mas não use títulos em hipótese alguma. Somente texto comum e formatação em negrito, itálico, listas, etc. Título não. 
        Seja formal e objetivo. NUNCA USE TITULOS NEM SUBTITULOS. NADA DE H1, H2, H3, ETC.
        """

        from google.genai import types
        
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=[
                prompt,
                types.Part.from_bytes(
                    data=image_data,
                    mime_type=mimetypes.guess_type(image_path)[0] or 'image/jpeg'
                )
            ]
        )
        
        return response.text.strip()
        
    except Exception as e:
        print(f"❌ Erro ao gerar descrição da imagem: {e}")
        # Fallback com informações básicas
        return f"""
        **PRÉ-LAUDO TÉCNICO - IMAGEM CLASSIFICADA**

        **Classificação Principal:** {dados_analise.get('classe_predita', 'N/A')} ({dados_analise.get('classe_traduzida', 'N/A')})
        **Confiança do Modelo:** {dados_analise.get('confianca_predita_percentual', 'N/A')}
        **F1-Score Histórico:** {dados_analise.get('metrica_f1_classe_predita', 'N/A'):.4f}

        **Análise Diferencial (Top 3):**
        {', '.join([f"{k}: {v}" for k, v in list(dados_analise.get('probabilidades_completas', {}).items())[:3]])}

        **AVISO:** Este é um pré-laudo gerado por IA e deve ser validado por avaliação clínica direta. 
        Para úlceras por pressão (Classe P), o modelo possui recall histórico de apenas 0.2647.
        """