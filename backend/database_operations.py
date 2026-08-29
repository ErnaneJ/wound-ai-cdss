import os
import hashlib
from sqlalchemy.orm import Session
from .database import get_db, SessionLocal
from .models import Paciente, Chat, Image, ChatMessage, ReportPDF
from .gemini_service import generate_chat_introduction
from datetime import datetime

def classify_all_images_in_chat(db: Session, chat_id: int):
    """Classifies all images in a specific chat"""
    images = db.query(Image).filter(Image.chat_id == chat_id).all()

    celery_app = get_celery_app()
    for img in images:
        result = celery_app.send_task(
            'app.tasks.classificar_imagem_individual',
            args=[img.id]
        )
        print(f"✅ Task sent for image {img.id}: {result.id}")

    print(f"🎯 {len(images)} tasks sent for processing")

def get_celery_app():
    """Returns a configured Celery instance"""
    from celery import Celery
    celery_app = Celery('worker')
    celery_app.conf.broker_url = 'redis://redis:6379/0'
    celery_app.conf.result_backend = 'redis://redis:6379/0'
    return celery_app

def save_image_to_bucket(image_data, filename):
    """Saves an image to the bucket and returns its hash and path"""
    image_hash = hashlib.sha256(image_data).hexdigest()
    
    file_extension = os.path.splitext(filename)[1] if '.' in filename else '.jpg'
    new_filename = f"{image_hash}{file_extension}"
    file_path = f"bucket/images/{new_filename}"
    
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(image_data)
    
    return image_hash, file_path

def create_paciente_with_chat(db: Session, paciente_data, images_data=[]):
    """Creates a patient and its associated chat"""
    if paciente_data.get('documento'):
        existing = db.query(Paciente).filter(Paciente.documento == paciente_data['documento']).first()
        if existing:
            raise ValueError(f"A patient with document {paciente_data['documento']} already exists")
    
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
    
    chat = Chat(
        paciente_id=paciente.id,
        titulo=f"Chat - {paciente.nome}"
    )
    db.add(chat)
    db.flush()
    
    try:
        introduction_message = generate_chat_introduction({
            'nome': paciente.nome,
            'idade': paciente.idade,
            'sexo': paciente.sexo,
            'diabetes_tipo': paciente.diabetes_tipo,
            'historico_medico': paciente.historico_medico,
            'medicamentos': paciente.medicamentos,
            'alergias': paciente.alergias
        })
        
        chat_message = ChatMessage(
            chat_id=chat.id,
            content=introduction_message,
            is_user=False,
            message_type="text"
        )
        db.add(chat_message)
        print(f"✅ Introduction message created for chat {chat.id}")

    except Exception as e:
        print(f"⚠️  Could not create introduction message: {e}")
        chat_message = ChatMessage(
            chat_id=chat.id,
            content=f"Hello! I'm your pressure wound analysis assistant. Patient: {paciente.nome}, {paciente.idade} years old, Diabetes {paciente.diabetes_tipo}. I'm ready to analyze the wound images.",
            is_user=False,
            message_type="text"
        )
        db.add(chat_message)
    
    saved_images = []
    for img_data in images_data:
        image_hash, file_path = save_image_to_bucket(img_data['data'], img_data['filename'])
        
        image = Image(
            chat_id=chat.id,
            image_path=file_path,
            filename=img_data['filename'],
            description="Waiting for analysis...",
            classification="Pending"
        )
        db.add(image)
        saved_images.append(image)

    db.commit()

    celery_app = get_celery_app()
    for img in saved_images:
        result = celery_app.send_task(
            'app.tasks.classificar_imagem_individual',
            args=[img.id],
            queue='celery'
        )
        print(f"✅ Task sent for image {img.id}: {result.id}")

    celery_app.send_task(
        'app.tasks.inicializar_chat',
        args=[img.id],
        queue='celery'
    )

    print(f"🎯 {len(saved_images)} tasks sent for processing")

    return {
        "paciente": paciente,
        "chat": chat,
        "images": saved_images
    }

def search_pacientes(db: Session, search_term: str = ""):
    """Searches patients by name or document"""
    query = db.query(Paciente)
    
    if search_term:
        query = query.filter(
            (Paciente.nome.ilike(f"%{search_term}%")) | 
            (Paciente.documento.ilike(f"%{search_term}%"))
        )
    
    return query.order_by(Paciente.created_at.desc()).all()

def get_paciente_by_documento(db: Session, documento: str):
    """Looks up a patient by document"""
    return db.query(Paciente).filter(Paciente.documento == documento).first()

def get_paciente_with_chat(db: Session, paciente_id: int):
    """Returns a patient with its chat and related information"""
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
        print(f"❌ Error in get_paciente_with_chat: {e}")
        raise

def get_chat_status(chat):
    """Returns the chat's processing status"""
    if not chat:
        return "No Chat"
    
    images = chat.images
    if not images:
        return "No images"
    
    processed = all(img.classification != "Pending" for img in images)
    
    if processed:
        return "Processed"
    elif any(img.classification != "Pending" for img in images):
        return "Processing"
    else:
        return "Pending"

def get_chat_images(db: Session, chat_id: int):
    """Returns the images associated with a chat"""
    return db.query(Image).filter(Image.chat_id == chat_id).all()

def add_images_to_chat(db: Session, chat_id: int, images_data: list):
    """Adds new images to an existing chat"""
    try:
        chat = db.query(Chat).filter(Chat.id == chat_id).first()
        if not chat:
            raise ValueError(f"Chat with ID {chat_id} not found")
        
        saved_images = []
        for img_data in images_data:
            image_hash, file_path = save_image_to_bucket(img_data['data'], img_data['filename'])
            
            image = Image(
                chat_id=chat_id,
                image_path=file_path,
                filename=img_data['filename'],
                description="Waiting for analysis...",
                classification="Pending"
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
            print(f"✅ New task sent for image {img.id}: {result.id}")

        print(f"🎯 {len(saved_images)} new image(s) sent for processing")

        return saved_images

    except Exception as e:
        db.rollback()
        raise e

def generate_pdf_report(db: Session, paciente_id: int):
    """Generates the PDF report for a patient"""
    try:
        from .pdf_service import generate_report_for_patient
        pdf_path = generate_report_for_patient(db, paciente_id)

        from .models import ReportPDF
        report = ReportPDF(
            paciente_id=paciente_id,
            file_path=pdf_path,
            generated_at=datetime.utcnow()
        )
        db.add(report)
        db.commit()

        return pdf_path

    except Exception as e:
        print(f"❌ Error generating PDF report: {e}")
        raise

def get_pdf_report(db: Session, paciente_id: int):
    """Looks up the patient's most recent PDF report"""
    from .models import ReportPDF
    report = db.query(ReportPDF).filter(
        ReportPDF.paciente_id == paciente_id
    ).order_by(ReportPDF.generated_at.desc()).first()
    
    return report