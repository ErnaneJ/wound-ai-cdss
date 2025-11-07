import os
import sys
import traceback
from celery import current_task
from .celery_app import celery_app

# Adiciona o backend ao path
sys.path.append('/app/backend')

def classificar_imagem_batch():
    """Task para processar imagens pendentes"""
    try:
        from database import SessionLocal
        from models import Image
        from classification_model import classificar_imagem
        
        print("🎯 INICIANDO PROCESSAMENTO EM LOTE VIA CELERY")
        
        db = SessionLocal()
        
        try:
            # Pega imagens pendentes
            imagens = db.query(Image).filter(Image.classification == "Pendente").all()
            print(f"📊 {len(imagens)} imagens pendentes")
            
            resultados = []
            for i, img in enumerate(imagens, 1):
                print(f"\n--- [{i}/{len(imagens)}] {img.filename} ---")
                
                try:
                    # CORREÇÃO: Usa caminho absoluto
                    image_path = img.image_path
                    print(f"📂 Caminho relativo: {image_path}")
                    
                    # Se o caminho for relativo, converte para absoluto
                    if not image_path.startswith('/'):
                        image_path = f"/app/{image_path}"
                    
                    print(f"📂 Caminho absoluto: {image_path}")
                    
                    if not os.path.exists(image_path):
                        print(f"❌ Arquivo não existe em: {image_path}")
                        # Atualiza status para ERROR
                        img.classification = "ERROR"
                        img.description = "Arquivo não encontrado"
                        db.commit()
                        resultados.append({
                            'image_id': img.id,
                            'filename': img.filename,
                            'status': 'error',
                            'error': 'Arquivo não encontrado'
                        })
                        continue
                    
                    # Classifica
                    resultado = classificar_imagem(image_path)
                    
                    if resultado:
                        # Atualiza banco com sucesso
                        img.classification = resultado['classe']
                        img.description = f"{resultado['classe_traduzida']} ({resultado['confianca']})"
                        db.commit()
                        print(f"✅ Atualizado: {resultado['classe']}")
                        resultados.append({
                            'image_id': img.id,
                            'filename': img.filename,
                            'status': 'success',
                            'classification': resultado['classe'],
                            'description': resultado['classe_traduzida'],
                            'confidence': resultado['confianca']
                        })
                    else:
                        # Classificação falhou
                        print(f"❌ Falha na classificação")
                        img.classification = "ERROR"
                        img.description = "Falha na classificação da imagem"
                        db.commit()
                        resultados.append({
                            'image_id': img.id,
                            'filename': img.filename,
                            'status': 'error',
                            'error': 'Falha na classificação'
                        })
                        
                except Exception as img_error:
                    # Erro específico no processamento desta imagem
                    error_msg = f"Erro no processamento: {str(img_error)}"
                    print(f"💥 ERRO na imagem {img.filename}: {error_msg}")
                    print(traceback.format_exc())
                    
                    # Atualiza status para ERROR
                    img.classification = "ERROR"
                    img.description = error_msg[:255]  # Limita o tamanho
                    db.commit()
                    resultados.append({
                        'image_id': img.id,
                        'filename': img.filename,
                        'status': 'error',
                        'error': error_msg
                    })
                    continue
            
            print(f"\n🎉 CONCLUÍDO! {len([r for r in resultados if r.get('status') == 'success'])} imagens processadas com sucesso")
            print(f"❌ {len([r for r in resultados if r.get('status') == 'error'])} imagens com erro")
            
            return {
                'status': 'completed',
                'total_processed': len(resultados),
                'success_count': len([r for r in resultados if r.get('status') == 'success']),
                'error_count': len([r for r in resultados if r.get('status') == 'error']),
                'results': resultados
            }
            
        except Exception as e:
            # Erro geral no processamento do batch
            error_msg = f"Erro geral no processamento: {str(e)}"
            print(f"💥 ERRO GERAL: {error_msg}")
            print(traceback.format_exc())
            return {
                'status': 'error',
                'error': error_msg,
                'results': []
            }
        finally:
            db.close()
            
    except ImportError as e:
        # Erro de importação (problema de configuração)
        error_msg = f"Erro de importação: {str(e)}"
        print(f"💥 ERRO DE IMPORT: {error_msg}")
        print(traceback.format_exc())
        return {
            'status': 'error',
            'error': error_msg,
            'results': []
        }

@celery_app.task(bind=True, name='app.tasks.processar_imagens_pendentes')
def processar_imagens_pendentes(self):
    """Task Celery para processar imagens pendentes"""
    return classificar_imagem_batch()


@celery_app.task(bind=True, name='app.tasks.classificar_imagem_individual')
def classificar_imagem_individual(self, image_id):
    """Task Celery para classificar uma imagem individual"""
    try:
        from database import SessionLocal
        from models import Image
        from classification_model import classificar_imagem
        
        db = SessionLocal()
        
        try:
            # Busca a imagem específica
            img = db.query(Image).filter(Image.id == image_id).first()
            if not img:
                return {
                    'status': 'error',
                    'error': f'Imagem com ID {image_id} não encontrada'
                }
            
            print(f"🎯 Processando imagem individual: {img.filename} (ID: {image_id})")
            
            # CORREÇÃO: Usa caminho absoluto
            image_path = img.image_path
            if not image_path.startswith('/'):
                image_path = f"/app/{image_path}"
            
            if not os.path.exists(image_path):
                error_msg = f"Arquivo não encontrado: {image_path}"
                img.classification = "ERROR"
                img.description = error_msg
                db.commit()
                return {
                    'status': 'error',
                    'error': error_msg
                }
            
            # Classifica
            resultado = classificar_imagem(image_path)
            
            if resultado:
                img.classification = resultado['classe']
                img.description = f"{resultado['classe_traduzida']} ({resultado['confianca']})"
                db.commit()
                return {
                    'status': 'success',
                    'image_id': image_id,
                    'filename': img.filename,
                    'classification': resultado['classe'],
                    'description': resultado['classe_traduzida'],
                    'confidence': resultado['confianca']
                }
            else:
                error_msg = "Falha na classificação da imagem"
                img.classification = "ERROR"
                img.description = error_msg
                db.commit()
                return {
                    'status': 'error',
                    'error': error_msg
                }
                
        except Exception as e:
            error_msg = f"Erro no processamento: {str(e)}"
            # Tenta atualizar o status para ERROR mesmo em caso de exceção
            try:
                img.classification = "ERROR"
                img.description = error_msg[:255]
                db.commit()
            except:
                pass  # Se não conseguir atualizar, pelo menos loga o erro
            
            return {
                'status': 'error',
                'error': error_msg
            }
        finally:
            db.close()
            
    except ImportError as e:
        return {
            'status': 'error',
            'error': f"Erro de importação: {str(e)}"
        }