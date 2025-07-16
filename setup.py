#!/usr/bin/env python3
"""
Setup script untuk Flow Diagram Q&A Assistant
Menginisialisasi database dan folder yang diperlukan
"""

import os
import sys
from pathlib import Path

def create_directories():
    """Membuat direktori yang diperlukan"""
    directories = [
        'uploads',
        'vector_db',
        'database',
        'utils',
        'logs'
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✓ Direktori '{directory}' dibuat/sudah ada")

def create_env_file():
    """Membuat file .env template jika belum ada"""
    env_path = Path('.env')
    if not env_path.exists():
        env_content = """# Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Database Configuration
DATABASE_URL=sqlite:///flow_diagram_qa.db

# Vector Database Configuration
VECTOR_DB_PATH=./vector_db
"""
        with open(env_path, 'w') as f:
            f.write(env_content)
        print("✓ File .env template dibuat")
        print("⚠️  Harap isi GEMINI_API_KEY dengan API key yang valid")
    else:
        print("✓ File .env sudah ada")

def check_dependencies():
    """Memeriksa dependencies yang diperlukan"""
    required_packages = [
        ('streamlit', 'streamlit'),
        ('google-generativeai', 'google.generativeai'),
        ('chromadb', 'chromadb'),
        ('sqlalchemy', 'sqlalchemy'),
        ('pandas', 'pandas'),
        ('numpy', 'numpy'),
        ('pillow', 'PIL'),
        ('python-dotenv', 'dotenv')
    ]
    
    missing_packages = []
    
    for package_name, import_name in required_packages:
        try:
            __import__(import_name)
            print(f"✓ {package_name} terinstall")
        except ImportError:
            missing_packages.append(package_name)
            print(f"✗ {package_name} tidak terinstall")
    
    if missing_packages:
        print("\n⚠️  Packages yang hilang:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\nJalankan: pip install -r requirements.txt")
        return False
    
    return True

def initialize_database():
    """Inisialisasi database"""
    try:
        from database.connection import db_manager
        print("✓ Database berhasil diinisialisasi")
        return True
    except Exception as e:
        print(f"✗ Error inisialisasi database: {e}")
        return False

def main():
    """Main setup function"""
    print("🔄 Flow Diagram Q&A Assistant - Setup")
    print("=" * 50)
    
    # Buat direktori
    print("\n1. Membuat direktori...")
    create_directories()
    
    # Buat file .env
    print("\n2. Setup environment variables...")
    create_env_file()
    
    # Cek dependencies
    print("\n3. Memeriksa dependencies...")
    if not check_dependencies():
        print("\n❌ Setup gagal. Harap install dependencies terlebih dahulu.")
        sys.exit(1)
    
    # Inisialisasi database
    print("\n4. Inisialisasi database...")
    if not initialize_database():
        print("\n❌ Setup gagal. Error inisialisasi database.")
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("✅ Setup selesai!")
    print("\n📝 Langkah selanjutnya:")
    print("1. Isi GEMINI_API_KEY di file .env")
    print("2. Jalankan: streamlit run app.py")
    print("3. Buka browser di http://localhost:8501")
    print("\n🚀 Selamat menggunakan Flow Diagram Q&A Assistant!")

if __name__ == "__main__":
    main() 