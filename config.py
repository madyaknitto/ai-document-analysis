import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    # Gemini API Configuration
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    
    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///flow_diagram_qa.db')
    
    # Vector Database Configuration
    VECTOR_DB_PATH = os.getenv('VECTOR_DB_PATH', './vector_db')
    
    # Streamlit Configuration
    APP_TITLE = "Flow Diagram Q&A Assistant"
    APP_ICON = "🔄"
    
    # AI Configuration
    MODEL_NAME = "gemini-2.0-flash"  # Supports multimodal (text + image)
    EMBEDDING_MODEL = "models/embedding-001"
    
    # Maximum file size for uploads (in MB)
    MAX_FILE_SIZE = 10
    
    # Supported file types
    SUPPORTED_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff']
    
    @classmethod
    def validate_config(cls):
        """Validate that all required configuration is present"""
        if not cls.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY tidak ditemukan. Silakan tambahkan ke file .env")
        
        return True 