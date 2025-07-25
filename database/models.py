from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

Base = declarative_base()

class Document(Base):
    __tablename__ = 'documents'
    
    document_id = Column(String(100), primary_key=True)
    filename = Column(String(255), nullable=False)
    filepath = Column(Text, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    qa_history = relationship("QAHistory", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Document(document_id='{self.document_id}', filename='{self.filename}')>"

class QAHistory(Base):
    __tablename__ = 'qa_history'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(100), ForeignKey('documents.document_id', ondelete='CASCADE'), nullable=False, index=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    response_time = Column(String(50))
    similarity_score = Column(Float)
    page_references = Column(Text) # Store page numbers as comma-separated string or JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship with document
    document = relationship("Document", back_populates="qa_history")
    
    def __repr__(self):
        return f"<QAHistory(id='{self.id}', question='{self.question[:50]}...')>" 