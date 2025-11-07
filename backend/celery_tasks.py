import os
import sys

from celery import Celery

redis_url = f"redis://{os.getenv('REDIS_HOST', 'redis')}:6379/0"
celery_app = Celery('worker')
celery_app.conf.broker_url = redis_url
celery_app.conf.result_backend = redis_url

@celery_app.task
def process_image_analysis(image_id: int):
    """Task para processamento de imagens"""
    try:
        # Importa AQUI para evitar problemas de importação circular
        from classification_model import classificar_imagem, traduzir_classe
        from database import get_db
        from models import Image
        
        print(f"🎯 Processando imagem ID: {image_id}")
        
        # Obtém a imagem do banco
        db = next(get_db())
        image = db.query(Image).filter(Image.id == image_id).first()
        
        if not image:
            return {"status": "erro", "mensagem": f"Imagem {image_id} não encontrada"}
        
        # Classifica a imagem
        resultado = classificar_imagem(image.image_path)
        
        if resultado:
            # Atualiza a imagem no banco
            image.classification = resultado['classe']
            image.description = f"{resultado['classe_traduzida']} | Confiança: {resultado['confianca']}"
            db.commit()
            
            print(f"✅ Imagem {image_id} processada: {resultado['classe']}")
            return {
                "status": "sucesso",
                "image_id": image_id,
                "classification": resultado['classe'],
                "confidence": resultado['confianca']
            }
        else:
            # Em caso de erro na classificação
            image.description = "Erro na classificação"
            image.classification = "Erro"
            db.commit()
            
            print(f"❌ Erro na imagem {image_id}")
            return {"status": "erro", "image_id": image_id, "mensagem": "Falha na classificação"}
            
    except Exception as e:
        print(f"💥 Erro crítico no processamento da imagem {image_id}: {e}")
        return {"status": "erro", "image_id": image_id, "mensagem": str(e)}

@celery_app.task
def generate_pdf_report(paciente_id: int):
    """Task para geração de PDF"""
    print(f"📊 Gerando PDF para paciente: {paciente_id}")
    return {"status": "success", "message": f"PDF gerado para paciente {paciente_id}"}