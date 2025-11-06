from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Paciente(Base):
    __tablename__ = "pacientes"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=False)
    idade = Column(Integer)
    sexo = Column(String(1))
    diabetes_tipo = Column(String(50))
    historico_medico = Column(Text)
    documento = Column(String(100))
    medicamentos = Column(Text)
    alergias = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    chats = relationship("Chat", back_populates="paciente")
    reports = relationship("ReportPDF", back_populates="paciente")

class Chat(Base):
    __tablename__ = "chats"
    
    id = Column(Integer, primary_key=True, index=True)
    paciente_id = Column(Integer, ForeignKey("pacientes.id"))
    titulo = Column(String(200), default="Chat sobre lesões")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    paciente = relationship("Paciente", back_populates="chats")
    messages = relationship("ChatMessage", back_populates="chat")
    images = relationship("Image", back_populates="chat")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"))
    content = Column(Text, nullable=False)
    is_user = Column(Boolean, default=True)  # True for user, False for AI
    message_type = Column(String(20), default="text")  # text, image, system
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    chat = relationship("Chat", back_populates="messages")

class Image(Base):
    __tablename__ = "images"
    
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"))
    image_path = Column(String(500), nullable=False)
    filename = Column(String(200))
    description = Column(Text)  # Descrição gerada pelo Gemini
    classification = Column(String(100))  # Classificação do modelo de ML
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    chat = relationship("Chat", back_populates="images")

class ReportPDF(Base):
    __tablename__ = "report_pdfs"
    
    id = Column(Integer, primary_key=True, index=True)
    paciente_id = Column(Integer, ForeignKey("pacientes.id"))
    file_path = Column(String(500), nullable=False)
    report_content = Column(Text)
    generated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    paciente = relationship("Paciente", back_populates="reports")