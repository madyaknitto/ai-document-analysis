import os
import time
import math
import pytz
import streamlit as st
from config import Config
from database.connection import db_manager
from database.models import Document, QAHistory
from utils.document_processor import DocumentProcessor
from utils.vector_database import VectorDatabaseManager

JAKARTA_TZ = pytz.timezone('Asia/Jakarta')

st.set_page_config(
    page_title=Config.APP_TITLE,
    page_icon=Config.APP_ICON,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inisialisasi session state di awal
if 'page' not in st.session_state:
    st.session_state.page = "upload"
if 'selected_document_id' not in st.session_state:
    st.session_state.selected_document_id = None
if 'last_sources' not in st.session_state:
    st.session_state.last_sources = {}
if 'doc_to_delete' not in st.session_state:
    st.session_state.doc_to_delete = None
if 'qa_to_delete' not in st.session_state:
    st.session_state.qa_to_delete = None
if 'init_error' not in st.session_state:
    st.session_state.init_error = None
if 'document_processed' not in st.session_state:
    st.session_state.document_processed = False
if 'preview_page' not in st.session_state:
    st.session_state.preview_page = 1

def to_jakarta_time(dt):
    if dt and dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    return dt.astimezone(JAKARTA_TZ) if dt else None

def truncate_text(text, max_length=20):
    if len(text) > max_length:
        return text[:max_length-3] + "..."
    return text

@st.cache_resource
def initialize_processor():
    try:
        Config.validate_config()
        processor = DocumentProcessor()
        vector_db = VectorDatabaseManager()
        return processor, vector_db
    except Exception as e:
        error_message = f"❌ Gagal menginisialisasi komponen: {e}"
        st.session_state.init_error = error_message
        st.error(error_message)
        st.info("➡️ Silakan atur API Key Anda di file .env")
        st.stop()

processor, vector_db = initialize_processor()

def create_sidebar():
    with st.sidebar:
        st.title("🔄 AI Document")
        button_type_new_doc = "primary" if st.session_state.get('page') == 'upload' else "secondary"

        if st.button("📤 + Dokumen Baru", use_container_width=True, type=button_type_new_doc, key="upload_new_doc"):
            # Hanya jalankan jika belum di halaman upload untuk efisiensi
            if st.session_state.get('page') != 'upload':
                st.session_state.page = "upload"
                st.session_state.selected_document_id = None
                st.session_state.doc_to_delete = None
                st.rerun()
        
        st.markdown("---")

        try:
          with db_manager.get_session() as session:
              documents = session.query(Document).order_by(Document.uploaded_at.desc()).all()
          
          if not documents:
              st.info("Belum ada dokumen.")
          else:
              st.markdown("##### 📚 Riwayat Dokumen")
              
              for doc in documents:
                  button_type = "primary" if doc.document_id == st.session_state.get('selected_document_id') else "secondary"
                  if st.button(f"📄 {truncate_text(doc.filename)}", key=f"doc_{doc.document_id}", use_container_width=True, type=button_type):
                      st.session_state.page = "chat"
                      st.session_state.selected_document_id = doc.document_id
                      st.session_state.doc_to_delete = None # Reset konfirmasi hapus jika ada
                      st.rerun()

              st.markdown("---") 

              # Handle delete confirmation in sidebar
              if st.session_state.get('selected_document_id'):
                  if st.button("🗑️ Hapus Dokumen Terpilih", use_container_width=True, help="Hapus dokumen yang aktif saat ini", key="delete_selected_doc"):
                      with db_manager.get_session() as session:
                          doc_to_delete_obj = session.query(Document).filter(Document.document_id == st.session_state.selected_document_id).first()
                      if doc_to_delete_obj:
                          st.session_state.doc_to_delete = doc_to_delete_obj
                          st.rerun()
                  
                  # Show delete confirmation dialog in sidebar
                  if st.session_state.doc_to_delete:
                      doc = st.session_state.doc_to_delete
                      st.warning(f"⚠️ Hapus **{doc.filename}**?")
                      col1, col2 = st.columns(2)
                      with col1:
                          if st.button("✅ Ya", type="primary", use_container_width=True, key="confirm_delete_doc"):
                              delete_document(doc.document_id)
                      with col2:
                          if st.button("❌ Batal", use_container_width=True, key="cancel_delete_doc"):
                              st.session_state.doc_to_delete = None
                              st.rerun()
                  
                  # Show QA history delete confirmation in sidebar
                  if st.session_state.qa_to_delete:
                      qa = st.session_state.qa_to_delete
                      st.warning(f"⚠️ Hapus riwayat tanya jawab?")
                      st.markdown(f"**Pertanyaan:** {qa.question[:50]}...")
                      col1, col2 = st.columns(2)
                      with col1:
                          if st.button("✅ Ya", type="primary", use_container_width=True, key="confirm_delete_qa"):
                              delete_qa_history(qa.id)
                      with col2:
                          if st.button("❌ Batal", use_container_width=True, key="cancel_delete_qa"):
                              st.session_state.qa_to_delete = None
                              st.rerun()

        except Exception as e:
            st.error(f"Error loading documents: {e}")

def render_upload_page():
    st.header("📤 Upload Dokumen")
    
    uploaded_file = st.file_uploader("Pilih file PDF", type=['pdf'], help="Upload file PDF yang ingin dianalisis")
    
    if uploaded_file is not None:
        # Check file size (10MB limit)
        file_size = len(uploaded_file.getvalue()) / (1024 * 1024)  # Convert to MB
        if file_size > Config.MAX_FILE_SIZE:
            st.error(f"❌ File terlalu besar! Maksimal {Config.MAX_FILE_SIZE}MB. Ukuran file Anda: {file_size:.2f}MB")
            return
        
        st.info(f"📄 File: {uploaded_file.name} ({file_size:.2f}MB)")
        
        if st.button("🚀 Upload & Analisis", type="primary", use_container_width=True):
            with st.spinner("🔄 Memproses dokumen..."):
                try:
                    # Generate document ID from filename
                    document_id = processor.generate_document_id(uploaded_file.name)
                    
                    # Create storage directory for this document
                    storage_dir = os.path.join("storage", "documents", document_id)
                    os.makedirs(storage_dir, exist_ok=True)
                    
                    # Save uploaded file with original name + unique ID
                    original_filename = uploaded_file.name
                    file_extension = os.path.splitext(original_filename)[1]
                    saved_filename = f"{document_id}{file_extension}"
                    saved_filepath = os.path.join(storage_dir, saved_filename)
                    
                    # Save the file
                    with open(saved_filepath, 'wb') as f:
                        f.write(uploaded_file.getvalue())
                    
                    # Process document using the saved file
                    document_id = processor.process_pdf_document(saved_filepath, document_id)
                    
                    st.success(f"✅ Dokumen berhasil diproses!")
                    st.info(f"📋 ID Dokumen: `{document_id}`")
                    st.session_state.document_processed = True
                    st.session_state.selected_document_id = document_id
                    st.session_state.page = "chat"
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error memproses dokumen: {str(e)}")
                    # Clean up saved file if exists
                    if 'saved_filepath' in locals() and os.path.exists(saved_filepath):
                        os.unlink(saved_filepath)

def render_chat_page(doc_id):
    st.header("💬 Chat dengan Dokumen")
    
    # Get document info
    doc_info = processor.get_document_info(doc_id)
    if not doc_info:
        st.error("❌ Dokumen tidak ditemukan")
        return
    
    st.info(f"📄 **{doc_info['filename']}** | 📊 {doc_info['page_count']} halaman | 📅 {doc_info['uploaded_at']}")
    st.caption(f"🆔 Document ID: `{doc_info['document_id']}`")
    
    # Create 2-column layout: Chat on left, Info tabs on right
    col_chat, col_info = st.columns([3, 2])
    
    with col_chat:
        render_chat_interface(doc_id)
    
    with col_info:
        # Create tabs for info
        tab_preview, tab_history, tab_stats = st.tabs(["👁️ Preview", "📚 Riwayat", "📊 Statistik"])
        
        with tab_preview:
            render_document_preview(doc_id, doc_info)
        
        with tab_history:
            render_qa_history(doc_id)
        
        with tab_stats:
            render_document_stats(doc_id, doc_info)

def render_qa_history(document_id):
    st.subheader("📚 Riwayat Tanya Jawab")
    
    try:
        with db_manager.get_session() as session:
            qa_records = session.query(QAHistory).filter(
                QAHistory.document_id == document_id
            ).order_by(QAHistory.created_at.desc()).limit(5).all()  # Limit to 5 most recent
            
            if not qa_records:
                st.info("Belum ada riwayat tanya jawab.")
                return
            
            for record in qa_records:
                with st.expander(f"❓ {record.question[:30]}..."):
                    st.write(f"**Pertanyaan:** {record.question}")
                    st.write(f"**Jawaban:** {record.answer}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.caption(f"⏱️ {record.response_time}")
                    with col2:
                        st.caption(f"📊 Score: {record.similarity_score:.3f}")
                    
                    # Delete button - now triggers sidebar confirmation
                    if st.button("🗑️ Hapus", key=f"delete_qa_{record.id}", use_container_width=True):
                        st.session_state.qa_to_delete = record
                        st.rerun()
                    
                    st.divider()
                    
    except Exception as e:
        st.error(f"Error loading QA history: {e}")

def render_document_preview(doc_id, doc_info):
    st.subheader("👁️ Preview Dokumen")
    
    # Get pages from vector database instead of SQL
    pages_data = processor.get_document_pages_for_qa(doc_id)
    
    if not pages_data:
        st.warning("Pratinjau tidak tersedia.")
        return
    
    # Pagination
    total_pages = len(pages_data)
    items_per_page = 10  # Show 10 pages at a time
    
    # Calculate pagination
    total_pages_pagination = math.ceil(total_pages / items_per_page)    
    
    # Calculate which pages to show
    start_idx = (st.session_state.preview_page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, total_pages)
    
    # Show current pages with expanders
    for i in range(start_idx, end_idx):
        page_data = pages_data[i]
        # Construct PNG file path
        png_filename = f"{doc_id}_page_{page_data['page_number']}.png"
        png_filepath = os.path.join("storage/documents", doc_id, png_filename)
        
        with st.expander(f"📄 Halaman {page_data['page_number']} ({len(page_data['elements'])} element)"):
            # Show PNG image if exists
            if os.path.exists(png_filepath):
                element_types = [element['element_type'] for element in page_data['elements']]
                st.write(f"**Element Type:** {', '.join(element_types)}")

                st.image(png_filepath, use_container_width=True, caption=f"Halaman {page_data['page_number']}")
            else:
                st.warning(f"Gambar tidak tersedia untuk halaman {page_data['page_number']}")

    col1, col2, col3 = st.columns([2, 4, 1])
    
    with col1:
        if st.button("⬅️", disabled=st.session_state.preview_page <= 1):
            st.session_state.preview_page = max(1, st.session_state.preview_page - 1)
            st.rerun()

    with col2:
        st.markdown(f"**Halaman {st.session_state.preview_page} dari {total_pages_pagination}**")
    
    with col3:
        if st.button("➡️", disabled=st.session_state.preview_page >= total_pages_pagination):
            st.session_state.preview_page = min(total_pages_pagination, st.session_state.preview_page + 1)
            st.rerun()

def render_document_stats(doc_id, doc_info):
    st.subheader("📊 Statistik Dokumen")
    
    # Get vector database stats
    try:
        stats = vector_db.get_collection_stats()
        if stats and "error" not in stats:
            st.metric("Total Embeddings", stats.get('total_embeddings', 0))
        else:
            st.warning("Vector database tidak tersedia")
    except Exception as e:
        st.error(f"Error getting stats: {e}")
    
    # Document info
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Halaman", doc_info['page_count'])
    with col2:
        st.metric("Tanggal Upload", doc_info['uploaded_at'][:10] if doc_info['uploaded_at'] else 'N/A')
    
    # Document ID info
    st.markdown("---")
    st.caption("**Document ID:**")
    st.code(doc_info['document_id'], language=None)

def render_chat_interface(doc_id):
    # Inisialisasi session state yang diperlukan
    for key in [f"last_q_{doc_id}", f"last_a_{doc_id}"]:
        if key not in st.session_state:
            st.session_state[key] = ""
    for key in [f"last_r_{doc_id}", f"last_s_{doc_id}"]: # r = response_time, s = score
        if key not in st.session_state:
            st.session_state[key] = None

    st.subheader("❓ Ajukan Pertanyaan")
    prompt = st.text_area("Tanya apapun tentang isi dokumen ini:", height=100, placeholder="Contoh: Apa yang dilakukan sistem jika tidak ada data di database.", label_visibility="collapsed", key=f"question_input_{doc_id}")
    if st.button("Kirim Pertanyaan", type="primary", use_container_width=True, key=f"send_question_{doc_id}"):
        if prompt:
            with st.spinner("🧠 AI sedang menganalisis dan mencari jawaban..."):
                # Initialize variables
                avg_score = 0
                
                try:
                    start_time = time.time()
                    
                    # Get answer using embedding-based search
                    result = processor.answer_question(doc_id, prompt)
                    response_time = time.time() - start_time # in seconds
                    
                    if not isinstance(result, dict):
                        result = {"answer": str(result), "similar_elements": []}
                    
                    response = result.get('answer', "Maaf, saya tidak dapat menemukan jawaban.")
                    similar_elements = result.get('similar_elements', [])

                    # Calculate average similarity score
                    if similar_elements:
                        scores = [s.get('similarity_score', 0) for s in similar_elements]
                        if scores:
                            avg_score = sum(scores) / len(scores)
                    
                    st.session_state[f"last_q_{doc_id}"] = prompt
                    st.session_state[f"last_a_{doc_id}"] = response
                    st.session_state[f"last_r_{doc_id}"] = f"{response_time:.2f}s"
                    st.session_state[f"last_s_{doc_id}"] = avg_score # Simpan skor rata-rata

                    if 'last_sources' not in st.session_state:
                        st.session_state.last_sources = {}
                    st.session_state.last_sources[doc_id] = similar_elements

                    # Simpan ke database (skor tidak disimpan di DB saat ini, bisa ditambahkan jika perlu)
                    with db_manager.get_session() as session:
                        qa_record = QAHistory(
                            document_id=doc_id, question=prompt, answer=response,
                            response_time=f"{response_time:.2f}s",
                            similarity_score=avg_score
                        )
                        session.add(qa_record)
                        session.commit()

                    st.rerun()
                    
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        else:
            st.warning("Silakan masukkan pertanyaan")

    # Display last Q&A if exists
    if st.session_state[f"last_q_{doc_id}"] and st.session_state[f"last_a_{doc_id}"]:
        st.markdown("---")
        st.subheader("💬 Hasil Terakhir")
        
        # Question
        st.markdown(f"**❓ Pertanyaan:** {st.session_state[f'last_q_{doc_id}']}")
        
        # Answer
        st.markdown(f"**🤖 Jawaban:** {st.session_state[f'last_a_{doc_id}']}")
        
        # Metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("⏱️ Response Time", st.session_state[f"last_r_{doc_id}"])
        with col2:
            st.metric("📊 Similarity Score", f"{st.session_state[f'last_s_{doc_id}']:.3f}")
        with col3:
            if doc_id in st.session_state.last_sources:
                st.metric("📄 Sources", len(st.session_state.last_sources[doc_id]))
        
        # Show sources with page images if available
        if doc_id in st.session_state.last_sources and st.session_state.last_sources[doc_id]:
            st.markdown("---")
            st.subheader("🔍 Lihat Sumber:")
            for source in st.session_state.last_sources[doc_id]:
                    page_number = source.get('page_number', 'N/A')
                    element_type = source.get('element_type', 'UNKNOWN')
                    similarity_score = source.get('similarity_score', 0)
                    plain_text = source.get('plain_text', '')
                    
                    with st.expander(f"**Halaman {page_number}** ({element_type})"):
                        st.markdown(f"**Score:** {similarity_score:.3f}")
                        st.markdown(f"**Content:** {plain_text[:200]}...")
                        
                        # Show page image if available
                        if page_number != 'N/A':
                            png_filename = f"{doc_id}_page_{page_number}.png"
                            png_filepath = os.path.join("storage/documents", doc_id, png_filename)
                            
                            if os.path.exists(png_filepath):
                                st.image(png_filepath, use_container_width=True, caption=f"Halaman {page_number}")
                            else:
                                st.warning(f"Gambar tidak tersedia untuk halaman {page_number}")
                    
def delete_document(document_id):
    """Delete a document and all its associated data"""
    try:
        success = processor.delete_document(document_id)
        if success:
            st.success("✅ Dokumen berhasil dihapus!")
            # Reset session state
            if st.session_state.get('selected_document_id') == document_id:
                st.session_state.selected_document_id = None
                st.session_state.page = "upload"
            st.session_state.doc_to_delete = None
            st.rerun()
        else:
            st.error("❌ Gagal menghapus dokumen")
    except Exception as e:
        st.error(f"❌ Error menghapus dokumen: {str(e)}")

def delete_qa_history(qa_id):
    """Delete a QA history record"""
    try:
        with db_manager.get_session() as session:
            qa_record = session.query(QAHistory).filter(QAHistory.id == qa_id).first()
            if qa_record:
                session.delete(qa_record)
                session.commit()
                st.success("✅ Riwayat tanya jawab berhasil dihapus!")
                st.session_state.qa_to_delete = None
                st.rerun()
            else:
                st.error("❌ Riwayat tanya jawab tidak ditemukan")
    except Exception as e:
        st.error(f"❌ Error menghapus riwayat: {str(e)}")

def main():
    # Show error if initialization failed
    if st.session_state.init_error:
        st.error(st.session_state.init_error)
        st.info("➡️ Silakan atur API Key Anda di file .env")
        return
    
    # Create sidebar
    create_sidebar()
    
    # Main content based on page
    if st.session_state.page == "upload":
        render_upload_page()
    elif st.session_state.page == "chat" and st.session_state.selected_document_id:
        render_chat_page(st.session_state.selected_document_id)
    else:
        st.info("👈 Pilih dokumen di sidebar untuk memulai chat")

if __name__ == "__main__":
    main()