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

## 📖 Cara Menggunakan

### 1. Upload Diagram
- Pilih halaman "📤 Upload Diagram"
- Upload file gambar diagram (.png, .jpg, .jpeg, .gif, .bmp, .tiff)
- Isi judul dan deskripsi diagram
- Klik "🔍 Analisis Diagram"
- Tunggu proses analisis selesai

### 2. Tanya AI
- Pilih halaman "❓ Tanya AI"
- Pilih diagram yang ingin ditanyakan
- Masukkan pertanyaan dalam bahasa Indonesia
- Klik "🤖 Tanya AI"
- Dapatkan jawaban dari AI

### 3. Lihat Riwayat
- Pilih halaman "📊 Riwayat"
- Tab "📋 Diagram": Lihat semua diagram yang pernah diupload
- Tab "💬 Q&A": Lihat riwayat pertanyaan dan jawaban

### 4. Pengaturan
- Pilih halaman "⚙️ Settings"
- Lihat statistik database
- Lakukan maintenance file

## 🏗️ Struktur Proyek

```
flow-diagram-qa/
├── app.py                 # Aplikasi Streamlit utama
├── config.py              # Konfigurasi aplikasi
├── requirements.txt       # Dependencies
├── README.md             # Dokumentasi
├── database/
│   ├── models.py         # Model database
│   └── connection.py     # Koneksi database
├── utils/
│   ├── ai_processor.py   # Gemini AI integration
│   ├── vector_database.py # ChromaDB management
│   └── file_handler.py   # File operations
├── uploads/              # Folder upload file
└── vector_db/            # Vector database storage
```

## 🔧 Konfigurasi

### Environment Variables
- `GEMINI_API_KEY`: API key untuk Google Gemini
- `DATABASE_URL`: URL database SQLite
- `VECTOR_DB_PATH`: Path untuk ChromaDB

### Aplikasi Settings
- `MAX_FILE_SIZE`: Maksimal ukuran file upload (10MB)
- `SUPPORTED_EXTENSIONS`: Format file yang didukung
- `MODEL_NAME`: Model Gemini yang digunakan (gemini-pro)
- `EMBEDDING_MODEL`: Model embedding (models/embedding-001)

## 📊 Database Schema

### FlowDiagram
- `id`: Primary key
- `title`: Judul diagram
- `description`: Deskripsi diagram
- `file_path`: Path file yang diupload
- `file_name`: Nama file asli
- `file_size`: Ukuran file
- `processed`: Status pemrosesan
- `created_at`: Tanggal dibuat
- `updated_at`: Tanggal diupdate

### QAHistory
- `id`: Primary key
- `flow_diagram_id`: Foreign key ke FlowDiagram
- `question`: Pertanyaan user
- `answer`: Jawaban AI
- `confidence_score`: Skor kepercayaan
- `response_time`: Waktu respons
- `created_at`: Tanggal dibuat

### VectorEmbedding
- `id`: Primary key
- `flow_diagram_id`: Foreign key ke FlowDiagram
- `content`: Konten yang di-embed
- `embedding_type`: Jenis embedding
- `created_at`: Tanggal dibuat

## 🔍 Fitur AI

### Analisis Diagram
AI akan menganalisis diagram dan mengekstrak:
- Judul dan deskripsi
- Elemen-elemen diagram
- Alur proses
- Decision points
- Input dan output
- Tujuan utama

### Q&A System
- Pertanyaan dalam bahasa Indonesia
- Jawaban berdasarkan analisis diagram
- Pencarian pertanyaan serupa
- Confidence scoring
- Response time tracking

### Vector Search
- Embedding menggunakan Gemini
- Similarity search dengan ChromaDB
- Caching untuk performa optimal
- Pencarian pertanyaan serupa

## 🚨 Troubleshooting

### Error: "GEMINI_API_KEY tidak ditemukan"
- Pastikan file `.env` ada di root directory
- Pastikan API key valid dan aktif
- Restart aplikasi setelah menambah API key

### Error: "Database tidak dapat diakses"
- Pastikan folder memiliki permission write
- Restart aplikasi
- Hapus file database dan buat ulang

### Error: "File tidak dapat diupload"
- Periksa format file (harus gambar)
- Periksa ukuran file (maksimal 10MB)
- Pastikan folder uploads memiliki permission write

### Performance Issues
- Bersihkan file lama di Settings
- Restart aplikasi
- Periksa koneksi internet untuk API calls

## 🎨 Customization

### Menambah Format File
Edit `config.py`:
```python
SUPPORTED_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.svg']
```

### Mengubah Model AI
Edit `config.py`:
```python
MODEL_NAME = "gemini-pro-vision"  # Untuk vision tasks
```

### Mengubah Similarity Threshold
Edit `utils/ai_processor.py`:
```python
return len(intersection) / len(union) > 0.3  # Ubah threshold
```

## 🔐 Security

- API key disimpan dalam environment variables
- File upload dibatasi ukuran dan format
- Database lokal (tidak ada data sensitif di cloud)
- Validasi input untuk mencegah injection

## 📈 Monitoring

- Statistik database di sidebar
- Response time tracking
- Confidence scoring
- Error logging

## 🤝 Kontribusi

Untuk berkontribusi:
1. Fork repository
2. Buat branch fitur baru
3. Commit perubahan
4. Push ke branch
5. Buat Pull Request

## 📝 License

Aplikasi ini menggunakan lisensi MIT. Lihat file LICENSE untuk detail.

## 🙏 Acknowledgments

- Google Gemini AI untuk AI processing
- ChromaDB untuk vector database
- Streamlit untuk web framework
- SQLAlchemy untuk database ORM

## 📞 Support

Jika mengalami masalah:
1. Periksa bagian Troubleshooting
2. Lihat log error di console
3. Pastikan semua dependencies terinstall
4. Buat issue di repository

---

**Dibuat dengan ❤️ menggunakan Streamlit dan Gemini AI** 