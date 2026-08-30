from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.database import Base

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    document = Column(String(20), unique=True, index=True)
    age = Column(Integer)
    sex = Column(String(1))
    diabetes_type = Column(String(50))
    medical_history = Column(Text)
    medications = Column(Text)
    allergies = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    chats = relationship("Chat", back_populates="patient", lazy="select")
    reports = relationship("ReportPDF", back_populates="patient", lazy="select")

class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    title = Column(String(200), default="Chat about wounds")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = relationship("Patient", back_populates="chats", lazy="select")
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
    model_version = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)

    chat = relationship("Chat", back_populates="images", lazy="select")

class ReportPDF(Base):
    __tablename__ = "report_pdfs"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    file_path = Column(String(500), nullable=False)
    report_content = Column(Text)
    generated_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="reports", lazy="select")
