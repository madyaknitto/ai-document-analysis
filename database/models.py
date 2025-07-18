from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import uuid

Base = declarative_base()

class FlowDiagram(Base):
    __tablename__ = 'flow_diagrams'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(200), nullable=False)
    description = Column(Text)
    file_path = Column(String(500), nullable=False)
    file_name = Column(String(200), nullable=False)
    file_size = Column(Integer)
    upload_date = Column(DateTime, default=datetime.utcnow)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship dengan Q&A history
    qa_history = relationship("QAHistory", back_populates="flow_diagram")
    
    def __repr__(self):
        return f"<FlowDiagram(id='{self.id}', title='{self.title}')>"

class QAHistory(Base):
    __tablename__ = 'qa_history'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    flow_diagram_id = Column(String, ForeignKey('flow_diagrams.id'), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    response_time = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship dengan flow diagram
    flow_diagram = relationship("FlowDiagram", back_populates="qa_history")
    
    def __repr__(self):
        return f"<QAHistory(id='{self.id}', question='{self.question[:50]}...')>"

class VectorEmbedding(Base):
    __tablename__ = 'vector_embeddings'
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    flow_diagram_id = Column(String, ForeignKey('flow_diagrams.id'), nullable=False)
    content = Column(Text, nullable=False)
    embedding_type = Column(String(50), default='diagram_analysis')
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<VectorEmbedding(id='{self.id}', type='{self.embedding_type}')>" 