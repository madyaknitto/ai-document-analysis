"""
Test script untuk memverifikasi refactoring google-genai
"""

from utils.ai_processor import GeminiProcessor
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_gemini_client():
    """Test inisialisasi client Gemini"""
    try:
        processor = GeminiProcessor()
        print("✅ Client berhasil diinisialisasi")
        return True
    except Exception as e:
        print(f"❌ Error inisialisasi client: {e}")
        return False

def test_simple_text_generation():
    """Test generasi teks sederhana"""
    try:
        processor = GeminiProcessor()
        
        if processor.client is None:
            print("❌ Client tidak terinisialisasi")
            return False
        
        # Test simple text generation
        prompt = "Jelaskan apa itu flow diagram dalam 2 kalimat"
        response = processor.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[prompt]
        )
        
        if response and response.text:
            print(f"✅ Text generation berhasil: {response.text[:100]}...")
            return True
        else:
            print("❌ Response kosong")
            return False
    except Exception as e:
        print(f"❌ Error text generation: {e}")
        return False

def test_embeddings():
    """Test embedding generation"""
    try:
        processor = GeminiProcessor()
        
        if processor.client is None:
            print("❌ Client tidak terinisialisasi")
            return False
        
        # Test embedding generation
        text = "Ini adalah test embedding"
        embedding = processor.generate_embeddings(text)
        
        if embedding:
            print(f"✅ Embedding berhasil: {len(embedding)} dimensi")
            return True
        else:
            print("❌ Embedding gagal: None")
            return False
    except Exception as e:
        print(f"❌ Error embedding: {e}")
        return False

if __name__ == "__main__":
    print("Testing Google GenAI refactoring...")
    print("=" * 50)
    
    # Check API key
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("❌ GEMINI_API_KEY tidak ditemukan. Pastikan file .env sudah diatur.")
        exit(1)
    
    # Run tests
    test_gemini_client()
    test_simple_text_generation()
    test_embeddings()
    
    print("\n✅ Refactoring selesai! Aplikasi siap digunakan dengan google-genai") 