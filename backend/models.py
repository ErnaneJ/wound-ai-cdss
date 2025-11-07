from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.database import Base

class Paciente(Base):
    __tablename__ = "pacientes"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    documento = Column(String(20), unique=True, index=True)
    idade = Column(Integer)
    sexo = Column(String(1))
    diabetes_tipo = Column(String(50))
    historico_medico = Column(Text)
    medicamentos = Column(Text)
    alergias = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Use strings para lazy loading
    chats = relationship("Chat", back_populates="paciente", lazy="select")
    reports = relationship("ReportPDF", back_populates="paciente", lazy="select")

class Chat(Base):
    __tablename__ = "chats"
    
    id = Column(Integer, primary_key=True, index=True)
    paciente_id = Column(Integer, ForeignKey("pacientes.id"))
    titulo = Column(String(200), default="Chat sobre lesões")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    paciente = relationship("Paciente", back_populates="chats", lazy="select")
    messages = relationship("ChatMessage", back_populates="chat", lazy="select")
    images = relationship("Image", back_populates="chat", lazy="select")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"))
    content = Column(Text, nullable=False)
    is_user = Column(Boolean, default=True)
    message_type = Column(String(20), default="text")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    chat = relationship("Chat", back_populates="messages", lazy="select")

class Image(Base):
    __tablename__ = "images"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"))
    image_path = Column(String(500), nullable=False)
    filename = Column(String(200))
    description = Column(Text)
    classification = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    chat = relationship("Chat", back_populates="images", lazy="select")

class ReportPDF(Base):
    __tablename__ = "report_pdfs"
    
    id = Column(Integer, primary_key=True, index=True)
    paciente_id = Column(Integer, ForeignKey("pacientes.id"))
    file_path = Column(String(500), nullable=False)
    report_content = Column(Text)
    generated_at = Column(DateTime, default=datetime.utcnow)
    
    paciente = relationship("Paciente", back_populates="reports", lazy="select")