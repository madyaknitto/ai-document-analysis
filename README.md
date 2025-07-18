# 🔄 Flow Diagram Q&A Assistant

Aplikasi web full-stack yang memungkinkan pengguna untuk bertanya kepada AI tentang flow diagram menggunakan Streamlit, dengan integrasi Gemini AI dan vector database.

## 🎯 Fitur Utama

- **Upload Flow Diagram**: Upload gambar diagram alur dalam berbagai format
- **Analisis AI**: Analisis otomatis diagram menggunakan Gemini AI
- **Q&A System**: Tanya jawab interaktif tentang diagram
- **Vector Database**: Penyimpanan embedding untuk pencarian yang cepat
- **Similarity Search**: Pencarian pertanyaan serupa untuk respons yang efisien
- **Riwayat Q&A**: Penyimpanan dan akses riwayat pertanyaan
- **Database Management**: Manajemen data diagram dan Q&A

## 🛠️ Teknologi yang Digunakan

- **Frontend**: Streamlit
- **AI Processing**: Google Gemini AI
- **Vector Database**: ChromaDB
- **Database**: SQLite dengan SQLAlchemy
- **Image Processing**: PIL (Pillow)
- **Embedding**: Gemini Embedding API

## 📋 Prerequisites

- Python 3.8 atau lebih baru
- Google Gemini API Key
- Minimal 2GB RAM
- Koneksi internet untuk API calls

## 🚀 Instalasi

1. **Clone repository atau download files**
```bash
cd flow-diagram-qa
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Setup environment variables**
Buat file `.env` di root directory:
```env
GEMINI_API_KEY=your_gemini_api_key_here
DATABASE_URL=sqlite:///flow_diagram_qa.db
VECTOR_DB_PATH=./vector_db
```

4. **Dapatkan Gemini API Key**
   - Kunjungi [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Buat API key baru
   - Masukkan ke file `.env`

## 🏃‍♂️ Menjalankan Aplikasi

```bash
streamlit run app.py
```

Aplikasi akan buka di browser pada `http://localhost:8501`