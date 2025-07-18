import streamlit as st
import json
import os
from datetime import datetime
import pandas as pd
from PIL import Image
import pytz

# Import custom modules
from config import Config
from database.connection import db_manager
from database.models import FlowDiagram, QAHistory, VectorEmbedding
from utils.ai_processor import GeminiProcessor
from utils.vector_database import VectorDatabaseManager
from utils.file_handler import FileHandler

# Timezone configuration
JAKARTA_TZ = pytz.timezone('Asia/Jakarta')

def to_jakarta_time(dt):
    """Convert UTC datetime to Jakarta time."""
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(JAKARTA_TZ)

# Page configuration
st.set_page_config(
    page_title=Config.APP_TITLE,
    page_icon=Config.APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize components
@st.cache_resource
def initialize_components():
    """Initialize all components with caching"""
    try:
        # Validate configuration
        Config.validate_config()
        
        # Initialize components
        ai_processor = GeminiProcessor()
        vector_db = VectorDatabaseManager()
        file_handler = FileHandler()
        
        return ai_processor, vector_db, file_handler
    except Exception as e:
        st.error(f"Error initializing components: {e}")
        st.stop()

# Initialize components
ai_processor, vector_db, file_handler = initialize_components()

def create_sidebar():
    """Create sidebar navigation"""
    st.sidebar.title("🔄 Flow Diagram Q&A")
    
    # Navigation
    page = st.sidebar.radio(
        "Pilih Halaman",
        ["🏠 Home", "📤 Upload Diagram", "❓ Tanya AI", "📊 Riwayat", "⚙️ Settings"]
    )
    
    # Database stats
    try:
        session = db_manager.get_session()
        diagram_count = session.query(FlowDiagram).count()
        qa_count = session.query(QAHistory).count()
        session.close()
        
        vector_stats = vector_db.get_collection_stats()
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("📈 **Statistik Database**")
        st.sidebar.write(f"• Total Diagram: {diagram_count}")
        st.sidebar.write(f"• Total Q&A: {qa_count}")
        if vector_stats:
            st.sidebar.write(f"• Total Embeddings: {vector_stats['total_embeddings']}")
        
    except Exception as e:
        st.sidebar.error(f"Error loading stats: {e}")
    
    return page

def home_page():
    """Home page content"""
    st.title("🔄 Flow Diagram Q&A Assistant")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        ### 🎯 Fitur Utama
        
        - **Upload Flow Diagram**: Upload gambar diagram alur Anda
        - **Analisis AI**: Sistem akan menganalisis diagram menggunakan Gemini AI
        - **Tanya Jawab**: Tanyakan apa saja tentang diagram Anda
        - **Vector Search**: Pencarian cepat berdasarkan similarity
        - **Riwayat Q&A**: Simpan dan akses riwayat pertanyaan
        """)
    
    with col2:
        st.markdown("""
        ### 🚀 Cara Menggunakan
        
        1. **Upload Diagram** di halaman Upload
        2. **Tunggu** proses analisis AI selesai
        3. **Tanyakan** pertanyaan tentang diagram
        4. **Dapatkan** jawaban yang akurat dari AI
        5. **Lihat** riwayat di halaman Riwayat
        """)
    
    # Recent activity
    st.markdown("---")
    st.subheader("📋 Aktivitas Terbaru")
    
    try:
        session = db_manager.get_session()
        recent_diagrams = session.query(FlowDiagram).order_by(FlowDiagram.created_at.desc()).limit(5).all()
        recent_qa = session.query(QAHistory).order_by(QAHistory.created_at.desc()).limit(5).all()
        session.close()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Diagram Terbaru**")
            if recent_diagrams:
                for diagram in recent_diagrams:
                    st.write(f"• {diagram.title} ({to_jakarta_time(diagram.created_at).strftime('%d/%m/%Y %H:%M')})")
            else:
                st.write("Belum ada diagram yang diupload")
        
        with col2:
            st.markdown("**Q&A Terbaru**")
            if recent_qa:
                for qa in recent_qa:
                    st.write(f"• {qa.question[:50]}... ({to_jakarta_time(qa.created_at).strftime('%d/%m/%Y %H:%M')})")
            else:
                st.write("Belum ada pertanyaan")
    
    except Exception as e:
        st.error(f"Error loading recent activity: {e}")

def upload_diagram_page():
    """Upload diagram page"""
    st.title("📤 Upload Flow Diagram")
    st.markdown("---")
    
    # File upload
    uploaded_file = st.file_uploader(
        "Pilih file diagram",
        type=['png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff'],
        help="Upload gambar flow diagram Anda"
    )
    
    if uploaded_file is not None:
        # Display uploaded image
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.image(uploaded_file, caption="Diagram yang diupload", use_container_width=True)
        
        with col2:
            # Diagram information form
            st.subheader("Informasi Diagram")

            upload_type = st.radio(
                "Pilih tipe unggah:",
                ("New", "Update"),
                horizontal=True
            )

            # Fetch existing titles once
            session = db_manager.get_session()
            existing_titles_query = session.query(FlowDiagram.title).distinct().order_by(FlowDiagram.title).all()
            session.close()
            title_list = [title[0] for title in existing_titles_query]

            title = ""
            button_label = ""

            if upload_type == "New":
                title = st.text_input("Judul Diagram Baru", value=uploaded_file.name.split('.')[0])
                button_label = "Analisis Diagram Baru"
            
            elif upload_type == "Update":
                if not title_list:
                    st.warning("Belum ada diagram untuk di-update. Silakan buat diagram baru.")
                    return
                title = st.selectbox("Pilih Judul Diagram untuk Di-update", title_list)
                button_label = "Update Diagram"

            description = st.text_area("Deskripsi", placeholder="Jelaskan tujuan diagram ini...")
            
            if st.button(f"🔍 {button_label}", type="primary"):
                # General validation
                if not title or not title.strip():
                    st.error("Harap isi atau pilih judul diagram")
                    return

                # Specific validation for "New"
                if upload_type == "New":
                    # Case-insensitive check for duplicates
                    if title.strip().lower() in [t.lower() for t in title_list]:
                        st.error(f"Judul diagram '{title}' sudah ada. Silakan gunakan judul lain atau pilih 'Update'.")
                        return
                
                # Proceed with analysis
                analyze_and_save_diagram(uploaded_file, title.strip(), description)

def analyze_and_save_diagram(uploaded_file, title, description):
    """Analyze and save diagram to database"""
    with st.spinner("Menganalisis diagram..."):
        try:
            # Save file
            file_info, error = file_handler.save_uploaded_file(uploaded_file)
            if error or file_info is None:
                st.error(error or "Gagal menyimpan file")
                return
            
            # Analyze diagram
            analysis = ai_processor.analyze_flow_diagram(file_info['file_path'])
            if not analysis:
                st.error("Gagal menganalisis diagram")
                return
            
            # Generate embeddings
            analysis_text = vector_db._convert_analysis_to_text(analysis)
            embeddings = ai_processor.generate_embeddings(analysis_text)
            
            # Save to database
            session = db_manager.get_session()
            try:
                # Create diagram record
                diagram = FlowDiagram(
                    title=title,
                    description=description,
                    file_path=file_info['file_path'],
                    file_name=file_info['original_name'],
                    file_size=file_info['file_size'],
                    processed=True
                )
                
                session.add(diagram)
                session.commit()
                
                # Add to vector database
                if embeddings:
                    vector_db.add_diagram_embedding(diagram.id, analysis, embeddings)
                
                # Save analysis to vector embeddings table
                vector_embedding = VectorEmbedding(
                    flow_diagram_id=diagram.id,
                    content=analysis_text,
                    embedding_type="diagram_analysis"
                )
                session.add(vector_embedding)
                session.commit()
                
                st.success("✅ Diagram berhasil dianalisis dan disimpan!")
                
                # Display analysis results
                st.subheader("🔍 Hasil Analisis")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Judul:** {analysis.get('title', 'N/A')}")
                    st.markdown(f"**Deskripsi:** {analysis.get('description', 'N/A')}")
                    st.markdown(f"**Tujuan Utama:** {analysis.get('main_purpose', 'N/A')}")
                
                with col2:
                    if analysis.get('decision_points'):
                        st.markdown("**Decision Points:**")
                        for point in analysis['decision_points']:
                            st.write(f"• {point}")
                
                if analysis.get('process_flow'):
                    st.markdown("**Alur Proses:**")
                    st.write(analysis['process_flow'])
                
            except Exception as e:
                session.rollback()
                st.error(f"Error saving to database: {e}")
            finally:
                session.close()
                
        except Exception as e:
            st.error(f"Error analyzing diagram: {e}")

def qa_page():
    """Q&A page"""
    st.title("❓ Tanya AI tentang Flow Diagram")
    st.markdown("---")
    
    # Get available diagrams
    try:
        session = db_manager.get_session()
        # Order by title and then by creation date for consistent ordering
        diagrams = session.query(FlowDiagram).filter(FlowDiagram.processed == True).order_by(FlowDiagram.title, FlowDiagram.created_at.desc()).all()
        session.close()
        
        if not diagrams:
            st.warning("Belum ada diagram yang tersedia. Silakan upload diagram terlebih dahulu.")
            return

        # Group diagrams by title
        diagrams_by_title = {}
        for d in diagrams:
            if d.title not in diagrams_by_title:
                diagrams_by_title[d.title] = []
            diagrams_by_title[d.title].append(d)
        
        diagram_titles = list(diagrams_by_title.keys())
        
        col1, col2 = st.columns(2)
        
        with col1:
            selected_title = st.selectbox("Pilih Nama Diagram", diagram_titles)
        
        selected_diagram = None
        if selected_title:
            title_diagrams = diagrams_by_title[selected_title]
            timestamp_options = {f"{to_jakarta_time(d.created_at).strftime('%d/%m/%Y %H:%M:%S')}": d for d in title_diagrams}
            
            with col2:
                selected_timestamp_key = st.selectbox("Pilih Waktu Upload", list(timestamp_options.keys()))
            
            if selected_timestamp_key:
                selected_diagram = timestamp_options[selected_timestamp_key]

        # The rest of the page only renders if a diagram is fully selected.
        if selected_diagram:
            st.markdown("---")
            # Display selected diagram
            disp_col1, disp_col2 = st.columns([1, 2])
            
            with disp_col1:
                file_path = str(selected_diagram.file_path)
                if os.path.exists(file_path):
                    st.image(file_path, caption=str(selected_diagram.title), use_container_width=True)
                else:
                    st.error("File diagram tidak ditemukan")
            
            with disp_col2:
                st.markdown(f"**Judul:** {selected_diagram.title}")
                st.markdown(f"**Deskripsi:** {selected_diagram.description or 'Tidak ada deskripsi'}")
                st.markdown(f"**Upload:** {to_jakarta_time(selected_diagram.created_at).strftime('%d/%m/%Y %H:%M')}")
            
            # Question input
            st.markdown("---")
            question = st.text_area("Tanyakan sesuatu tentang diagram ini:", 
                                   placeholder="Contoh: Bagaimana alur proses dimulai? Apa yang terjadi jika kondisi X terpenuhi?")
            
            if st.button("🤖 Tanya AI", type="primary"):
                if question.strip():
                    answer_question(selected_diagram, question)
                else:
                    st.error("Harap masukkan pertanyaan")
            
            # Previous Q&A for this diagram
            display_qa_history(selected_diagram.id)
        
    except Exception as e:
        st.error(f"Error loading diagrams: {e}")

def answer_question(diagram, question):
    """Answer question about diagram"""
    with st.spinner("Mencari jawaban..."):
        try:
            # Get diagram analysis from vector database
            diagram_embeddings = vector_db.get_diagram_embeddings(diagram.id)
            
            if not diagram_embeddings or not diagram_embeddings['documents']:
                st.error("Data analisis diagram tidak ditemukan")
                return
            
            # Get analysis data
            analysis_text = diagram_embeddings['documents'][0]
            
            # Convert back to analysis format (simplified)
            analysis_data = {
                "title": diagram.title,
                "description": diagram.description,
                "process_flow": analysis_text,
                "decision_points": [],
                "main_purpose": "Analisis diagram"
            }
            
            # Check for similar questions
            question_embedding = ai_processor.generate_embeddings(question)
            similar_questions = vector_db.search_similar_questions(question_embedding, diagram.id)
            
            if similar_questions and similar_questions['documents']:
                st.info("💡 Pertanyaan serupa ditemukan dalam riwayat")
                for i, doc in enumerate(similar_questions['documents'][0][:1]):  # Show top 1
                    distances = similar_questions.get('distances')
                    if distances and len(distances) > 0 and len(distances[0]) > i and distances[0][i] < 0.3:  # High similarity
                        st.write(f"**Pertanyaan serupa:** {doc.split('Answer:')[0].replace('Question:', '').strip()}")
            
            # Get answer from AI
            result = ai_processor.answer_question(question, analysis_data)
            
            if result:
                # Display answer
                st.subheader("💬 Jawaban AI")
                st.write(result['answer'])
                
                col1, col2 = st.columns(2)
                with col1:
                    st.caption(f"⏱️ Response time: {result['response_time']}")
                
                # Save to database
                session = db_manager.get_session()
                try:
                    qa_record = QAHistory(
                        flow_diagram_id=diagram.id,
                        question=question,
                        answer=result['answer'],
                        response_time=result['response_time']
                    )
                    session.add(qa_record)
                    session.commit()
                    
                    # Add to vector database
                    if question_embedding:
                        vector_db.add_qa_embedding(diagram.id, question, result['answer'], question_embedding)
                    
                except Exception as e:
                    session.rollback()
                    st.error(f"Error saving Q&A: {e}")
                finally:
                    session.close()
            
        except Exception as e:
            st.error(f"Error answering question: {e}")

def display_qa_history(diagram_id):
    """Display Q&A history for diagram"""
    st.markdown("---")
    st.subheader("📚 Riwayat Q&A")
    
    try:
        session = db_manager.get_session()
        qa_history = session.query(QAHistory).filter(
            QAHistory.flow_diagram_id == diagram_id
        ).order_by(QAHistory.created_at.desc()).limit(10).all()
        session.close()
        
        if qa_history:
            for qa in qa_history:
                with st.expander(f"Q: {qa.question[:100]}... ({to_jakarta_time(qa.created_at).strftime('%d/%m %H:%M')})"):
                    st.write(f"**Pertanyaan:** {qa.question}")
                    st.write(f"**Jawaban:** {qa.answer}")
                    st.caption(f"⏱️ {qa.response_time}")
        else:
            st.info("Belum ada riwayat Q&A untuk diagram ini")
    
    except Exception as e:
        st.error(f"Error loading Q&A history: {e}")

def history_page():
    """History page"""
    st.title("📊 Riwayat Diagram dan Q&A")
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["📋 Diagram", "💬 Q&A"])
    
    with tab1:
        display_diagram_history()
    
    with tab2:
        display_all_qa_history()

def display_diagram_history():
    """Display all diagram history"""
    try:
        session = db_manager.get_session()
        diagrams = session.query(FlowDiagram).order_by(FlowDiagram.created_at.desc()).all()
        session.close()
        
        if diagrams:
            for diagram in diagrams:
                with st.expander(f"📄 {diagram.title} ({to_jakarta_time(diagram.created_at).strftime('%d/%m/%Y %H:%M')})"):
                    col1, col2 = st.columns([1, 2])
                    
                    with col1:
                        file_path = str(diagram.file_path)
                        if os.path.exists(file_path):
                            st.image(file_path, use_container_width=True)
                        else:
                            st.error("File tidak ditemukan")
                    
                    with col2:
                        st.write(f"**Judul:** {diagram.title}")
                        st.write(f"**Deskripsi:** {diagram.description or 'Tidak ada deskripsi'}")
                        st.write(f"**File:** {diagram.file_name}")
                        st.write(f"**Ukuran:** {diagram.file_size/1024:.1f} KB")
                        st.write(f"**Status:** {'✅ Diproses' if bool(diagram.processed) else '⏳ Belum diproses'}")
                        
                        if st.button(f"🗑️ Hapus", key=f"delete_{diagram.id}"):
                            delete_diagram(diagram.id)
                            st.rerun()
        else:
            st.info("Belum ada diagram yang diupload")
    
    except Exception as e:
        st.error(f"Error loading diagram history: {e}")

def display_all_qa_history():
    """Display all Q&A history"""
    try:
        session = db_manager.get_session()
        qa_history = session.query(QAHistory).order_by(QAHistory.created_at.desc()).limit(50).all()
        session.close()
        
        if qa_history:
            for qa in qa_history:
                with st.expander(f"❓ {qa.question[:100]}... ({to_jakarta_time(qa.created_at).strftime('%d/%m/%Y %H:%M')})"):
                    st.write(f"**Pertanyaan:** {qa.question}")
                    st.write(f"**Jawaban:** {qa.answer}")
                    st.caption(f"⏱️ {qa.response_time}")
        else:
            st.info("Belum ada riwayat Q&A")
    
    except Exception as e:
        st.error(f"Error loading Q&A history: {e}")

def delete_diagram(diagram_id):
    """Delete diagram and related data"""
    try:
        session = db_manager.get_session()
        diagram = session.query(FlowDiagram).filter(FlowDiagram.id == diagram_id).first()
        
        if diagram:
            # Delete file
            file_handler.delete_file(diagram.file_path)
            
            # Delete from vector database
            vector_db.delete_diagram_embeddings(diagram_id)
            
            # Delete from database
            session.delete(diagram)
            session.commit()
            
            st.success("Diagram berhasil dihapus")
        
        session.close()
    
    except Exception as e:
        st.error(f"Error deleting diagram: {e}")

def settings_page():
    """Settings page"""
    st.title("⚙️ Pengaturan")
    st.markdown("---")
    
    # API Configuration
    st.subheader("🔑 Konfigurasi API")
    st.info("Untuk menggunakan aplikasi ini, Anda perlu membuat file .env dengan konfigurasi berikut:")
    
    st.code("""
GEMINI_API_KEY=your_gemini_api_key_here
DATABASE_URL=sqlite:///flow_diagram_qa.db
VECTOR_DB_PATH=./vector_db
""", language="bash")
    
    # Database Statistics
    st.subheader("📊 Statistik Database")
    try:
        session = db_manager.get_session()
        diagram_count = session.query(FlowDiagram).count()
        qa_count = session.query(QAHistory).count()
        vector_count = session.query(VectorEmbedding).count()
        session.close()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Diagram", diagram_count)
        with col2:
            st.metric("Total Q&A", qa_count)
        with col3:
            st.metric("Vector Embeddings", vector_count)
    
    except Exception as e:
        st.error(f"Error loading statistics: {e}")
    
    # Maintenance
    st.subheader("🔧 Maintenance")
    if st.button("🧹 Bersihkan File Lama"):
        cleaned_files = file_handler.cleanup_old_files()
        st.info(f"Berhasil membersihkan {len(cleaned_files)} file lama")

def main():
    """Main application"""
    try:
        # Create sidebar and get selected page
        page = create_sidebar()
        
        # Route to appropriate page
        if page == "🏠 Home":
            home_page()
        elif page == "📤 Upload Diagram":
            upload_diagram_page()
        elif page == "❓ Tanya AI":
            qa_page()
        elif page == "📊 Riwayat":
            history_page()
        elif page == "⚙️ Settings":
            settings_page()
        
    except Exception as e:
        st.error(f"Application error: {e}")
        st.stop()

if __name__ == "__main__":
    main() 