import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Gemini API Configuration
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    
    # Database Configuration
    DATABASE_NAME = os.getenv('DATABASE_NAME', 'document_analysis_qa.db')
    
    # Vector Database Configuration
    VECTOR_DB_PATH = os.getenv('VECTOR_DB_PATH', './vector_db')
    
    # Streamlit Configuration
    APP_TITLE = "Flow Document Q&A Assistant"
    APP_ICON = "🔄"
    
    # AI Configuration
    MODEL_NAME = "gemini-2.0-flash"  # Supports multimodal (text + image)
    EMBEDDING_MODEL = "text-embedding-004"
    
    # Maximum file size for uploads (in MB)
    MAX_FILE_SIZE = 10
    
    @classmethod
    def validate_config(cls):
        """Validate that all required configuration is present"""
        if not cls.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY tidak ditemukan. Silakan tambahkan ke file .env")
        
        return True 