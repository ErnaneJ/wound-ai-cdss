from celery import Celery
import os

# Configuração do Celery
redis_url = f"redis://{os.getenv('REDIS_HOST', 'redis')}:6379/0"

celery_app = Celery('worker')
celery_app.conf.broker_url = redis_url
celery_app.conf.result_backend = redis_url

# Agora podemos importar do backend compartilhado
from backend.database_operations import save_image_to_bucket
from backend.database import get_db
from backend.models import Image

@celery_app.task
def process_image_analysis(image_path):
    """Task para processamento de imagens"""
    print(f"Processando imagem: {image_path}")
    # Aqui virá a integração com o modelo de ML e Gemini
    return {"status": "success", "message": f"Imagem {image_path} processada"}

@celery_app.task
def generate_pdf_report(paciente_id):
    """Task para geração de PDF"""
    print(f"Gerando PDF para paciente: {paciente_id}")
    return {"status": "success", "message": f"PDF gerado para paciente {paciente_id}"}

if __name__ == '__main__':
    celery_app.start()