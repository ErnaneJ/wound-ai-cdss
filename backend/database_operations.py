import os
import hashlib
from sqlalchemy.orm import Session
from .database import get_db, SessionLocal
from .models import Paciente, Chat, Image, ChatMessage, ReportPDF

def classify_all_images_in_chat(db: Session, chat_id: int):
    """Classifica todas as imagens em um chat específico"""
    images = db.query(Image).filter(Image.chat_id == chat_id).all()
    
    celery_app = get_celery_app()
    for img in images:
        result = celery_app.send_task(
            'app.tasks.classificar_imagem_individual', 
            args=[img.id]
        )
        print(f"✅ Task enviada para imagem {img.id}: {result.id}")
    
    print(f"🎯 {len(images)} tasks enviadas para processamento")

def get_celery_app():
    """Retorna uma instância configurada do Celery"""
    from celery import Celery
    celery_app = Celery('worker')
    celery_app.conf.broker_url = 'redis://redis:6379/0'
    celery_app.conf.result_backend = 'redis://redis:6379/0'
    return celery_app

def save_image_to_bucket(image_data, filename):
    """Salva imagem no bucket e retorna o hash e caminho"""
    image_hash = hashlib.sha256(image_data).hexdigest()
    
    file_extension = os.path.splitext(filename)[1] if '.' in filename else '.jpg'
    new_filename = f"{image_hash}{file_extension}"
    file_path = f"bucket/images/{new_filename}"
    
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(image_data)
    
    return image_hash, file_path

def create_paciente_with_chat(db: Session, paciente_data, images_data=[]):
    """Cria paciente e chat associado"""
    # Verifica se documento já existe
    if paciente_data.get('documento'):
        existing = db.query(Paciente).filter(Paciente.documento == paciente_data['documento']).first()
        if existing:
            raise ValueError(f"Já existe um paciente com o documento {paciente_data['documento']}")
    
    # Cria paciente
    paciente = Paciente(
        nome=paciente_data['nome'],
        documento=paciente_data.get('documento'),
        idade=paciente_data['idade'],
        sexo=paciente_data['sexo'],
        diabetes_tipo=paciente_data['diabetes_tipo'],
        historico_medico=paciente_data.get('historico_medico', ''),
        medicamentos=paciente_data.get('medicamentos', ''),
        alergias=paciente_data.get('alergias', '')
    )
    db.add(paciente)
    db.flush()
    
    # Cria chat
    chat = Chat(
        paciente_id=paciente.id,
        titulo=f"Chat - {paciente.nome}"
    )
    db.add(chat)
    db.flush()
    
    # Salva imagens
    saved_images = []
    for img_data in images_data:
        image_hash, file_path = save_image_to_bucket(img_data['data'], img_data['filename'])
        
        image = Image(
            chat_id=chat.id,
            image_path=file_path,
            filename=img_data['filename'],
            description="Aguardando processamento...",
            classification="Pendente"
        )
        db.add(image)
        saved_images.append(image)
    
    db.commit()
    
    celery_app = get_celery_app()
    for img in saved_images:
        result = celery_app.send_task(
            'app.tasks.classificar_imagem_individual', 
            args=[img.id],
            queue='celery'  # Especifica a fila
        )
        print(f"✅ Task enviada para imagem {img.id}: {result.id}")
    
    print(f"🎯 {len(saved_images)} tasks enviadas para processamento")

    return {
        "paciente": paciente,
        "chat": chat,
        "images": saved_images
    }

def search_pacientes(db: Session, search_term: str = ""):
    """Busca pacientes por nome ou documento"""
    query = db.query(Paciente)
    
    if search_term:
        query = query.filter(
            (Paciente.nome.ilike(f"%{search_term}%")) | 
            (Paciente.documento.ilike(f"%{search_term}%"))
        )
    
    return query.order_by(Paciente.created_at.desc()).all()

def get_paciente_by_documento(db: Session, documento: str):
    """Busca paciente por documento"""
    return db.query(Paciente).filter(Paciente.documento == documento).first()

def get_paciente_with_chat(db: Session, paciente_id: int):
    """Retorna paciente com chat e informações relacionadas"""
    try:
        paciente = db.query(Paciente).filter(Paciente.id == paciente_id).first()
        if not paciente:
            return None
        
        chat = db.query(Chat).filter(Chat.paciente_id == paciente_id).first()
        images = []
        report = None
        
        if chat:
            images = db.query(Image).filter(Image.chat_id == chat.id).all()
            report = db.query(ReportPDF).filter(ReportPDF.paciente_id == paciente_id).first()
        
        return {
            "paciente": paciente,
            "chat": chat,
            "images": images,
            "report": report
        }
    except Exception as e:
        print(f"❌ Erro em get_paciente_with_chat: {e}")
        raise

def get_chat_status(chat):
    """Retorna status do processamento do chat"""
    if not chat:
        return "Não criado"
    
    images = chat.images
    if not images:
        return "Sem imagens"
    
    processed = all(img.classification != "Pendente" for img in images)
    
    if processed:
        return "Processado"
    elif any(img.classification != "Pendente" for img in images):
        return "Processando"
    else:
        return "Pendente"

def get_chat_images(db: Session, chat_id: int):
    """Retorna imagens associadas a um chat"""
    return db.query(Image).filter(Image.chat_id == chat_id).all()

def add_images_to_chat(db: Session, chat_id: int, images_data: list):
    """Adiciona novas imagens a um chat existente"""
    try:
        # Verifica se o chat existe
        chat = db.query(Chat).filter(Chat.id == chat_id).first()
        if not chat:
            raise ValueError(f"Chat com ID {chat_id} não encontrado")
        
        # Salva imagens
        saved_images = []
        for img_data in images_data:
            image_hash, file_path = save_image_to_bucket(img_data['data'], img_data['filename'])
            
            image = Image(
                chat_id=chat_id,
                image_path=file_path,
                filename=img_data['filename'],
                description="Aguardando processamento...",
                classification="Pendente"
            )
            db.add(image)
            saved_images.append(image)
        
        db.commit()
        
        celery_app = get_celery_app()
        for img in saved_images:
            result = celery_app.send_task(
                'app.tasks.classificar_imagem_individual', 
                args=[img.id]
            )
            print(f"✅ Nova task enviada para imagem {img.id}: {result.id}")
        
        print(f"🎯 {len(saved_images)} nova(s) imagem(ns) enviada(s) para processamento")
    
        return saved_images
        
    except Exception as e:
        db.rollback()
        raise e