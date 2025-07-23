import os
import time

if not os.path.exists("storage"):
    os.makedirs("storage")

import streamlit as st
import math
import pytz
from config import Config
from database.connection import db_manager
from database.models import Document, DocumentPage, PageElement, QAHistory
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
        st.info("➡️ Silakan atur API Key Anda di sidebar bagian 'Pengaturan API Key'.")
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

              if st.session_state.get('selected_document_id'):
                  if st.button("🗑️ Hapus Dokumen Terpilih", use_container_width=True, help="Hapus dokumen yang aktif saat ini", key="delete_selected_doc"):
                      with db_manager.get_session() as session:
                          doc_to_delete_obj = session.query(Document).filter(Document.document_id == st.session_state.selected_document_id).first()
                      if doc_to_delete_obj:
                          st.session_state.doc_to_delete = doc_to_delete_obj
                          st.rerun()
          
          if st.session_state.doc_to_delete:
              doc = st.session_state.doc_to_delete
              st.warning(f"Yakin hapus **{doc.filename}**?")
              col1, col2 = st.columns(2)
              if col1.button("✅ Ya", use_container_width=True, type="primary"):
                  if delete_document(doc.document_id):
                      st.toast("✅ Dokumen dihapus!")
                      if st.session_state.selected_document_id == doc.document_id:
                          st.session_state.selected_document_id = None
                          st.session_state.page = "upload"
                      st.session_state.doc_to_delete = None
                      st.rerun()
              if col2.button("❌ Batal", use_container_width=True):
                  st.session_state.doc_to_delete = None
                  st.rerun()

        except Exception as e:
          st.error(f"Gagal memuat dokumen: {e}")

def render_upload_page():
    st.title("📤 Upload & Analisis Dokumen PDF")
    st.markdown("Upload file PDF untuk dianalisis oleh AI. AI akan mengekstrak teks, tabel, dan struktur untuk memungkinkan Anda melakukan tanya jawab.")
    uploaded_file = st.file_uploader("Pilih file PDF", type=['pdf'], label_visibility="collapsed")
    if uploaded_file:
        with st.spinner("⏳ Memproses dokumen dengan AI... Ini mungkin memakan waktu beberapa saat."):
            try:
                pdf_path = os.path.join("storage", uploaded_file.name)
                with open(pdf_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                document_id = processor.process_pdf_document(pdf_path)
                os.remove(pdf_path)
                st.session_state.document_processed = True
                st.session_state.selected_document_id = document_id
                st.session_state.page = "chat"
                st.success(f"✅ Dokumen '{uploaded_file.name}' berhasil diproses!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Gagal memproses dokumen: {e}")
                if 'pdf_path' in locals() and os.path.exists(pdf_path):
                    os.remove(pdf_path)

def render_chat_page(doc_id):
    doc_info = processor.get_document_info(doc_id)
    if not doc_info:
        st.error("Dokumen tidak ditemukan. Silakan pilih dari sidebar.")
        return
    st.header(f"💬 Chat dengan: {doc_info['filename']}")
    col_chat, col_viewer = st.columns([6, 4])
    with col_viewer:
        render_document_viewer(doc_id, doc_info)
    with col_chat:
        render_chat_interface(doc_id)

def render_qa_history(document_id):
    st.caption("Riwayat percakapan untuk dokumen ini.")
    ITEMS_PER_PAGE = 5
    page_key = f"history_page_{document_id}"

    if page_key not in st.session_state:
        st.session_state[page_key] = 1
    if 'qa_to_delete_id' not in st.session_state:
        st.session_state.qa_to_delete_id = None

    try:
        with db_manager.get_session() as session:
            query = session.query(QAHistory).filter(QAHistory.document_id == document_id)
            total_items = query.count()

            if total_items == 0:
                st.info("Belum ada riwayat percakapan yang tersimpan.")
                return

            total_pages = math.ceil(total_items / ITEMS_PER_PAGE)
            if st.session_state[page_key] > total_pages:
                st.session_state[page_key] = total_pages
            
            current_page = st.session_state[page_key]
            offset = (current_page - 1) * ITEMS_PER_PAGE
            qa_history_page = query.order_by(QAHistory.created_at.desc()).limit(ITEMS_PER_PAGE).offset(offset).all()

            for qa in qa_history_page:
                timestamp = to_jakarta_time(qa.created_at).strftime('%d/%m/%y %H:%M')
                with st.expander(f"💬 Q: {truncate_text(qa.question, 60)}... ({timestamp})"):
                    col_content, col_delete = st.columns([6, 1])
                    with col_content:
                        st.markdown(f"**Anda:**\n\n>{qa.question}")
                        st.markdown(f"**AI:**\n\n{qa.answer}")
                        if qa.response_time:
                            st.caption(f"⏱️ Waktu respons: {qa.response_time}")
                        if qa.similarity_score:
                            st.caption(f"🎯 Skor Relevansi: {qa.similarity_score:.1%}")
                    with col_delete:
                        if st.button("🗑️", key=f"delete_qa_{qa.id}", help="Hapus riwayat ini"):
                            st.session_state.qa_to_delete_id = qa.id
                            st.rerun()

                if st.session_state.qa_to_delete_id == qa.id:
                    st.warning("Anda yakin ingin menghapus riwayat ini?")
                    col_confirm1, col_confirm2 = st.columns([1,1])
                    if col_confirm1.button("✅ Ya, Hapus", key=f"confirm_delete_qa_{qa.id}", type="primary", use_container_width=True):
                        if delete_qa_history(qa.id):
                            st.toast("✅ Riwayat berhasil dihapus!")
                            st.session_state.qa_to_delete_id = None
                            st.rerun()
                    if col_confirm2.button("❌ Batal", key=f"cancel_delete_qa_{qa.id}", use_container_width=True):
                        st.session_state.qa_to_delete_id = None
                        st.rerun()
            
            if total_pages > 1:
                st.markdown("---")
                col1, col2, col3 = st.columns([3, 2, 3])
                
                with col1:
                    if st.button("⬅️", use_container_width=True, disabled=(current_page <= 1), key=f"prev_hist_{document_id}"):
                        st.session_state[page_key] -= 1
                        st.rerun()
                
                with col2:
                    st.markdown(f"<p style='text-align: center; margin-top: 8px;'>Hal {current_page}/{total_pages}</p>", unsafe_allow_html=True)

                with col3:
                    if st.button("➡️", use_container_width=True, disabled=(current_page >= total_pages), key=f"next_hist_{document_id}"):
                        st.session_state[page_key] += 1
                        st.rerun()

    except Exception as e:
        st.error(f"Gagal menampilkan riwayat: {e}")

def render_document_viewer(doc_id, doc_info):
    st.subheader("📄 Konteks Dokumen")
    
    tab_sources, tab_preview, tab_history = st.tabs(["📄 **Sumber**", "🖼️ **Pratinjau**","📜 **Riwayat**"])

    with tab_history:
        render_qa_history(doc_id)

    with tab_sources:
        st.caption("Halaman dalam dokumen yang digunakan untuk jawaban.")
        sources = st.session_state.get('last_sources', {}).get(doc_id, [])
        
        if not sources:
            st.info("Belum ada jawaban. Ajukan pertanyaan untuk melihat sumber yang digunakan.")
        else:
            for i, source in enumerate(sources):                
                if isinstance(source, dict):
                    score_percent = f"{source.get('similarity_score', 0):.1%}"
                    element_type = source.get('element_type', 'Unknown')
                    page_number = source.get('page_number', 'Unknown')
                    expander_title = f"Halaman {page_number} - {element_type} - Skor: {score_percent}"
                    
                    with st.expander(expander_title):
                        # Show PNG image if exists
                        png_filename = f"{doc_id}_page_{page_number}.png"
                        png_filepath = os.path.join("storage/documents", doc_id, png_filename)
                        
                        if os.path.exists(png_filepath):
                            st.image(png_filepath, use_container_width=True, caption=f"Sumber Halaman {page_number}")
                        else:
                            st.warning(f"Gambar tidak tersedia untuk halaman {page_number}")
                        
                        # Show element details
                        st.write(f"**Tipe Elemen:** {element_type}")
                        st.write(f"**Konten:**")
                        st.text_area(
                            label="Konten Elemen",
                            value=source.get('plain_text', ''),
                            height=150,
                            disabled=True,
                            label_visibility="collapsed",
                            key=f"source_text_{doc_id}_{i}"  # Unique key based on document and source index
                        )

    with tab_preview:
        with db_manager.get_session() as session:
            # Use joinedload to eagerly load elements
            from sqlalchemy.orm import joinedload
            pages = session.query(DocumentPage).options(joinedload(DocumentPage.elements)).filter(
                DocumentPage.document_id == doc_id
            ).order_by(DocumentPage.page_number).all()

        st.caption("Semua halaman pada dokumen.")
        if not pages:
            st.warning("Pratinjau tidak tersedia.")
        else:
            PAGES_PER_GROUP = 5
            page_groups = [pages[i:i + PAGES_PER_GROUP] for i in range(0, len(pages), PAGES_PER_GROUP)]
            total_pagination_pages = len(page_groups)
            
            preview_page_key = f"preview_group_page_{doc_id}"
            if preview_page_key not in st.session_state:
                st.session_state[preview_page_key] = 1
            current_pagination_page = st.session_state[preview_page_key]

            group_to_display = page_groups[current_pagination_page - 1]
            for page in group_to_display:
                # Construct PNG file path
                png_filename = f"{doc_id}_page_{page.page_number}.png"
                png_filepath = os.path.join("storage/documents", doc_id, png_filename)
                
                with st.expander(f"Halaman {page.page_number} ({len(page.elements)} elemen)"):
                    # Show PNG image if exists
                    if os.path.exists(png_filepath):
                        st.image(png_filepath, use_container_width=True, caption=f"Halaman {page.page_number}")
                    else:
                        st.warning(f"Gambar tidak tersedia untuk halaman {page.page_number}")
            
            st.markdown("---")
            col1, col2, col3 = st.columns([3, 2, 3])
            with col1:
                if st.button("⬅️", use_container_width=True, disabled=(current_pagination_page <= 1), key=f"prev_exp_group_{doc_id}"):
                    st.session_state[preview_page_key] -= 1
                    st.rerun()
            with col2:
                start_page = group_to_display[0].page_number
                end_page = group_to_display[-1].page_number
                st.markdown(f"<p style='text-align: center; margin-top: 8px;'>Hal {start_page}-{end_page} dari {doc_info['page_count']}</p>", unsafe_allow_html=True)
            with col3:
                if st.button("➡️", use_container_width=True, disabled=(current_pagination_page >= total_pagination_pages), key=f"next_exp_group_{doc_id}"):
                    st.session_state[preview_page_key] += 1
                    st.rerun()

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
                    st.error(f"Terjadi kesalahan: {e}")
        else:
            st.warning("Mohon masukkan pertanyaan Anda terlebih dahulu.")
    
    st.markdown("---")

    if st.session_state[f"last_q_{doc_id}"]:
        st.markdown("##### Pertanyaan Anda:")
        st.markdown(f"<div style='text-align: justify;'>{st.session_state[f'last_q_{doc_id}']}</div>", unsafe_allow_html=True)
        st.markdown("##### Jawaban AI:")
        st.markdown(f"<div style='text-align: justify;'>{st.session_state[f'last_a_{doc_id}']}</div>", unsafe_allow_html=True)
        
        response_time = st.session_state.get(f'last_r_{doc_id}', '0s')
        avg_score = st.session_state.get(f'last_s_{doc_id}', 0)

        col1, col2 = st.columns(2)
        with col1:
            st.caption(f"⏱️ Waktu respons: **{response_time}**")
        with col2:
            if avg_score is not None:
                st.caption(f"🎯 Skor Relevansi: **{avg_score:.1%}**")
        
        # Show embedding information - use session state to avoid UnboundLocalError
        last_sources = st.session_state.get('last_sources', {}).get(doc_id, [])
        if last_sources and len(last_sources) > 0:
            st.caption(f"📊 Ditemukan {len(last_sources)} elemen relevan menggunakan embedding search")


def delete_document(document_id):
    try:
        # Use processor to delete document (handles both SQL and vector DB)
        success = processor.delete_document(document_id)
        
        if success:
            # Also remove original PDF file if exists
            with db_manager.get_session() as session:
                document = session.query(Document).filter(Document.document_id == document_id).first()
                if document and document.filepath and os.path.exists(document.filepath):
                    os.remove(document.filepath)
        
        return success
    except Exception as e:
        st.error(f"Gagal menghapus dokumen: {e}")
        return False

def delete_qa_history(qa_id):
    try:
        with db_manager.get_session() as session:
            qa_record = session.query(QAHistory).filter(QAHistory.id == qa_id).first()
            if qa_record:
                session.delete(qa_record)
                session.commit()
                return True
        return False
    except Exception as e:
        st.error(f"Gagal menghapus riwayat QA: {e}")
        return False

def handle_delete_dialogs():
    """Mengelola semua dialog konfirmasi penghapusan."""
    
    # Dialog untuk menghapus Dokumen
    if st.session_state.doc_to_delete:
        doc_to_delete = st.session_state.doc_to_delete
        
        st.dialog("⚠️ Konfirmasi Penghapusan Dokumen")
        st.warning(f"Anda yakin ingin menghapus **{doc_to_delete.filename}** secara permanen? Semua riwayat chat terkait juga akan dihapus.")
        
        col1, col2 = st.columns(2)
        if col1.button("✅ Ya, Hapus", use_container_width=True, type="primary"):
            if delete_document(doc_to_delete.document_id):
                st.toast("✅ Dokumen berhasil dihapus!")
                if st.session_state.selected_document_id == doc_to_delete.document_id:
                    st.session_state.selected_document_id = None
                    st.session_state.page = "upload"
                st.session_state.doc_to_delete = None
                st.rerun()
        if col2.button("❌ Batal", use_container_width=True):
            st.session_state.doc_to_delete = None
            st.rerun()

    # Dialog untuk menghapus Riwayat QA
    if st.session_state.qa_to_delete:
        qa_to_delete = st.session_state.qa_to_delete
        
        st.dialog("⚠️ Konfirmasi Penghapusan Riwayat")
        st.warning("Anda yakin ingin menghapus riwayat percakapan ini?")
        st.caption(f"Pertanyaan: *{truncate_text(qa_to_delete.question, 100)}*")
        
        col1, col2 = st.columns(2)
        if col1.button("✅ Ya, Hapus", use_container_width=True, type="primary"):
            if delete_qa_history(qa_to_delete.id):
                st.toast("✅ Riwayat berhasil dihapus!")
                st.session_state.qa_to_delete = None
                st.rerun()
        if col2.button("❌ Batal", use_container_width=True):
            st.session_state.qa_to_delete = None
            st.rerun()

def main():
    """Titik masuk utama aplikasi."""
    create_sidebar()

    page = st.session_state.get('page', 'upload') 
    selected_id = st.session_state.get('selected_document_id')

    if selected_id and page == "chat":
        render_chat_page(selected_id)
    else:
        with db_manager.get_session() as session:
            documents_exist = session.query(Document).first() is not None
        
        if not selected_id and documents_exist and page != 'upload':
            with db_manager.get_session() as session:
                first_doc_id = session.query(Document).order_by(Document.uploaded_at.desc()).first().document_id
            st.session_state.selected_document_id = first_doc_id
            st.session_state.page = 'chat'
            st.rerun()
        else:
            st.session_state.page = "upload" 
            render_upload_page()

if __name__ == "__main__":
    main()