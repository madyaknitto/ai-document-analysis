# 🔄 AI Document Analysis & Q&A

Aplikasi web untuk menganalisis dokumen PDF dan menjawab pertanyaan berdasarkan konten dokumen menggunakan AI.

## ✨ Fitur Utama

- **Upload & Analisis PDF**: Konversi PDF ke gambar dan ekstraksi elemen (teks, flowchart, ringkasan)
- **AI-Powered Q&A**: Tanya jawab berdasarkan konten dokumen menggunakan Google Gemini AI
- **Vector Search**: Pencarian semantik untuk menemukan informasi relevan
- **Multi-page Support**: Analisis dokumen multi-halaman
- **Flowchart Detection**: Deteksi dan analisis flowchart secara otomatis
- **Riwayat Q&A**: Simpan dan lihat riwayat tanya jawab

## 🚀 Cara Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Setup Environment Variables
Buat file `.env` dengan konfigurasi berikut:
```env
GEMINI_API_KEY=your_gemini_api_key_here
DATABASE_NAME=document_analysis_qa.db
VECTOR_DB_PATH=./vector_db
```

### 3. Jalankan Aplikasi
```bash
streamlit run app.py
```

## 📁 Struktur Project

```
├── app.py                 # Aplikasi Streamlit utama
├── api.py                 # API endpoints (Flask)
├── config.py              # Konfigurasi aplikasi
├── requirements.txt       # Dependencies Python
├── database/              # Database models & connection
│   ├── models.py         # SQLAlchemy models
│   └── connection.py     # Database connection
└── utils/                 # Utility modules
    ├── document_processor.py  # PDF processing & analysis
    ├── ai_processor.py        # AI integration (Gemini)
    ├── vector_database.py     # Vector search (ChromaDB)
    └── function_call.py       # AI function calling
```

## 🎯 Cara Penggunaan

1. **Upload Dokumen**: Pilih file PDF untuk dianalisis
2. **Tunggu Proses**: Sistem akan mengkonversi PDF dan mengekstrak elemen
3. **Tanya Jawab**: Ajukan pertanyaan tentang konten dokumen
4. **Lihat Riwayat**: Akses riwayat tanya jawab sebelumnya

## 🔧 Teknologi

- **Frontend**: Streamlit
- **Backend**: Python, Flask
- **AI**: Google Gemini 2.0 Flash
- **Database**: SQLite + ChromaDB (Vector Database)
- **PDF Processing**: PyMuPDF, Pillow

## 📝 Catatan

- Maksimal ukuran file: 10MB
- Format yang didukung: PDF
- Elemen yang dapat dianalisis: Teks, Flowchart, Ringkasan 