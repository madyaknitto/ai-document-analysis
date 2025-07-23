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
    pages = relationship("DocumentPage", back_populates="document", cascade="all, delete-orphan")
    qa_history = relationship("QAHistory", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Document(document_id='{self.document_id}', filename='{self.filename}')>"

class DocumentPage(Base):
    __tablename__ = 'document_pages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(100), ForeignKey('documents.document_id', ondelete='CASCADE'), nullable=False)
    page_number = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="pages")
    elements = relationship("PageElement", back_populates="page", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<DocumentPage(id={self.id}, document_id='{self.document_id}', page={self.page_number})>"

class PageElement(Base):
    """
    Model untuk menyimpan elemen-elemen yang diekstrak dari halaman dokumen.
    
    Element Types:
    - ALL_TEXT: Seluruh teks yang diekstrak dari halaman, dapat mencakup penjelasan konten yang dihasilkan AI.
    - FLOWCHART: Diagram alur yang diekstrak.
    """
    __tablename__ = 'page_elements'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    page_id = Column(Integer, ForeignKey('document_pages.id', ondelete='CASCADE'), nullable=False)
    element_type = Column(String(50), nullable=False)  # 'ALL_TEXT', 'FLOWCHART'
    content_json = Column(Text)  # JSON string untuk konten (teks gabungan, atau flowchart)
    plain_text = Column(Text)  # Teks yang bisa di-embedding untuk vector search
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    page = relationship("DocumentPage", back_populates="elements")
    
    def __repr__(self):
        return f"<PageElement(id={self.id}, type='{self.element_type}')>"

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