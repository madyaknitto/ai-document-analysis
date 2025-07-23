import os
import uuid
from pathlib import Path
from PIL import Image
import fitz  # PyMuPDF
from sqlalchemy.orm import sessionmaker
from database.connection import db_manager
from database.models import Document, DocumentPage, PageElement
from utils.ai_processor import AIProcessor
from utils.vector_database import VectorDatabaseManager
import json

class DocumentProcessor:
    def __init__(self):
        self.ai_processor = AIProcessor()
        self.vector_db = VectorDatabaseManager()
        self.db_manager = db_manager
        self.session = None
        self._init_database_session()

    def _init_database_session(self):
        """Initialize database session"""
        try:
            self.session = db_manager.get_session()
        except Exception as e:
            print(f"Error initializing database session: {e}")
            raise e
    
    def process_pdf_document(self, pdf_path, document_id=None):
        """
        Process a PDF document: convert to PNG pages, extract data, store in database
        Returns the document_id
        """
        try:
            if not document_id:
                document_id = f"DOC_{uuid.uuid4().hex[:8].upper()}"
            
            # Get file info
            filename = os.path.basename(pdf_path)
            filepath = os.path.abspath(pdf_path)

            # Create document record
            document = Document(
                document_id=document_id,
                filename=filename,
                filepath=filepath
            )
            
            self.session.add(document)
            self.session.commit()
            
            # Convert PDF to PNG pages and process each page
            png_dir = self._create_png_directory(document_id)
            page_count = self._convert_pdf_to_png(pdf_path, png_dir, document_id)
            
            # Collect all PNG filepaths for batch processing
            png_filepaths = []
            for page_num in range(1, page_count + 1):
                png_filename = f"{document_id}_page_{page_num}.png"
                png_filepath = os.path.join(png_dir, png_filename)
                
                if os.path.exists(png_filepath):
                    png_filepaths.append((page_num, png_filename, png_filepath))
            
            # Process all pages in batch for better performance
            if png_filepaths:
                self._process_png_pages_batch(document_id, png_filepaths)
            
            print(f"Document {document_id} processed successfully with {page_count} pages")
            return document_id
            
        except Exception as e:
            print(f"Error processing PDF document: {e}")
            if self.session:
                self.session.rollback()
            raise e
    
    def _create_png_directory(self, document_id):
        """Create directory for PNG files"""
        png_dir = os.path.join("storage/documents", document_id)
        os.makedirs(png_dir, exist_ok=True)
        return png_dir
    
    def _convert_pdf_to_png(self, pdf_path, png_dir, document_id):
        """Convert PDF pages to PNG files"""
        try:
            pdf_document = fitz.open(pdf_path)
            page_count = len(pdf_document)
            
            for page_num in range(page_count):
                page = pdf_document.load_page(page_num)
                
                # Render page to image
                mat = fitz.Matrix(3.0, 3.0)  # 2x zoom for better quality
                pix = page.get_pixmap(matrix=mat)
                
                # Save as PNG
                png_filename = f"{document_id}_page_{page_num + 1}.png"
                png_filepath = os.path.join(png_dir, png_filename)
                pix.save(png_filepath)
            
            pdf_document.close()
            return page_count
            
        except Exception as e:
            print(f"Error converting PDF to PNG: {e}")
            raise e
    
    def _process_png_pages_batch(self, document_id, png_filepaths):
        """Process multiple PNG pages in batch with AI extraction"""
        try:
            for page_num, png_filename, png_filepath in png_filepaths:
                self._process_png_page(document_id, page_num, png_filename, png_filepath)
            
            print(f"Batch processed {len(png_filepaths)} pages successfully")
            
        except Exception as e:
            print(f"Error processing PNG pages batch: {e}")
            if self.session:
                self.session.rollback()
            raise e
    
    def _process_png_page(self, document_id, page_number, png_filename, png_filepath):
        """Process a single PNG page with AI extraction"""
        try:
            extracted_elements = self.ai_processor.process_png_page(png_filepath)
            
            page = DocumentPage(document_id=document_id, page_number=page_number)
            self.session.add(page)
            self.session.flush()
            
            for element_data in extracted_elements:
                element_type = element_data['element_type']
                if not self._validate_element_type(element_type):
                    print(f"⚠️  Warning: Invalid element type '{element_type}', skipping")
                    continue
                
                element = PageElement(
                    page_id=page.id,
                    element_type=element_type,
                    content_json=element_data['content_json'],
                    plain_text=element_data['plain_text']
                )
                self.session.add(element)
                self.session.flush()
                
                if element_data['plain_text']:
                    embedding = self.ai_processor.generate_embeddings(element_data['plain_text'])
                    if embedding:
                        self.vector_db.add_element_embedding(
                            element_id=element.id,
                            plain_text=element_data['plain_text'],
                            embedding_vector=embedding,
                            metadata={
                                "document_id": str(document_id),
                                "page_number": page_number,
                                "element_type": element_data['element_type']
                            }
                        )
            
            self.session.commit()
            print(f"Page {page_number} processed successfully with {len(extracted_elements)} elements")
            
        except Exception as e:
            print(f"Error processing PNG page {page_number}: {e}")
            if self.session:
                self.session.rollback()
            raise e

    def get_document_pages_for_qa(self, document_id):
        """Get all pages and their elements for QA processing"""
        try:
            pages = self.session.query(DocumentPage).filter(
                DocumentPage.document_id == document_id
            ).order_by(DocumentPage.page_number).all()
            
            pages_data = []
            for page in pages:
                elements_data = []
                for element in page.elements:
                    elements_data.append({
                        'element_type': element.element_type,
                        'content_json': element.content_json,
                        'plain_text': element.plain_text
                    })
                
                pages_data.append({
                    'page_number': page.page_number,
                    'elements': elements_data
                })
            
            return pages_data
            
        except Exception as e:
            print(f"Error getting document pages for QA: {e}")
            return []

    def get_page_details_by_number(self, document_id, page_number):
        """Get detailed information about a specific page"""
        try:
            page = self.session.query(DocumentPage).filter(
                DocumentPage.document_id == document_id,
                DocumentPage.page_number == page_number
            ).first()
            
            if not page:
                return None
            
            elements_data = []
            for element in page.elements:
                elements_data.append({
                    'element_type': element.element_type,
                    'content_json': element.content_json,
                    'plain_text': element.plain_text
                })
            
            return {
                'page_number': page.page_number,
                'elements': elements_data
            }
            
        except Exception as e:
            print(f"Error getting page details: {e}")
            return None

    def search_similar_content(self, document_id, query, top_k=5):
        """
        Search for similar content, boost flowcharts, and return only the top-scoring element per page.
        """
        try:
            query_embedding = self.ai_processor.generate_embeddings(query, task_type="RETRIEVAL_QUERY")
            if not query_embedding:
                return []
            
            # Ambil lebih banyak hasil awal untuk memastikan ada cukup kandidat setelah penyaringan
            initial_results = self.vector_db.search_similar_elements(
                query_embedding=query_embedding,
                document_id=document_id,
                top_k=top_k
            )
            
            if not initial_results or not initial_results.get('metadatas') or not initial_results['metadatas'][0]:
                return []
            
            all_similar_elements = []
            with self.db_manager.get_session() as session:
                for i, metadata in enumerate(initial_results['metadatas'][0]):
                    element_id = metadata.get('element_id')
                    if not element_id:
                        continue
                    
                    element_with_page = session.query(PageElement, DocumentPage.page_number).join(
                        DocumentPage, PageElement.page_id == DocumentPage.id
                    ).filter(PageElement.id == int(element_id)).first()
                    
                    if element_with_page:
                        element, page_number = element_with_page
                        similarity_score = 1 - initial_results['distances'][0][i]
                        
                        if element.element_type == 'FLOWCHART':
                            similarity_score *= 1.1
                            similarity_score = min(similarity_score, 1.0)

                        if similarity_score > 0.5:
                            all_similar_elements.append({
                                'element_type': element.element_type,
                                'plain_text': element.plain_text,
                                'content_json': element.content_json,
                                'similarity_score': round(similarity_score, 3),
                                'page_number': page_number,
                                'element_id': element_id
                            })
            
            # Urutkan semua elemen yang ditemukan berdasarkan skor
            all_similar_elements.sort(key=lambda x: (x['similarity_score']), reverse=True)
            
            # Saring untuk mendapatkan hanya skor tertinggi per halaman
            top_elements_per_page = {}
            for element in all_similar_elements:
                page_num = element['page_number']
                if page_num not in top_elements_per_page:
                    top_elements_per_page[page_num] = element
            
            # Kembalikan daftar yang sudah disaring, diurutkan kembali, dan dibatasi oleh top_k
            final_results = list(top_elements_per_page.values())
            final_results.sort(key=lambda x: (x['similarity_score']), reverse=True)
            
            return final_results[:1]
            
        except Exception as e:
            print(f"Error searching similar content: {e}")
            return []

    def answer_question(self, document_id, question, top_k=5):
        """Answer a question based on document content"""
        try:
            similar_elements = self.search_similar_content(document_id, question, top_k)
            if not similar_elements:
                return {"answer": "Maaf, tidak ada informasi relevan yang ditemukan.", "similar_elements": []}

            answer = self.ai_processor.answer_question(question, similar_elements)
            return {"answer": answer, "similar_elements": similar_elements}
            
        except Exception as e:
            print(f"Error answering question: {e}")
            return {"answer": f"Terjadi kesalahan: {e}", "similar_elements": []}

    def get_document_info(self, document_id):
        """Get basic information about a document"""
        try:
            document = self.session.query(Document).filter(
                Document.document_id == document_id
            ).first()
            
            if not document:
                return None
            
            # Get page count
            page_count = self.session.query(DocumentPage).filter(
                DocumentPage.document_id == document_id
            ).count()
            
            # Get element count
            element_count = self.session.query(PageElement).join(DocumentPage).filter(
                DocumentPage.document_id == document_id
            ).count()
            
            return {
                'document_id': document.document_id,
                'filename': document.filename,
                'uploaded_at': document.uploaded_at.isoformat() if document.uploaded_at else None,
                'page_count': page_count,
                'element_count': element_count
            }
            
        except Exception as e:
            print(f"Error getting document info: {e}")
            return None

    def list_all_documents(self):
        """List all documents with basic information"""
        try:
            documents = self.session.query(Document).all()
            
            documents_info = []
            for doc in documents:
                # Get page count for each document
                page_count = self.session.query(DocumentPage).filter(
                    DocumentPage.document_id == doc.document_id
                ).count()
                
                documents_info.append({
                    'document_id': doc.document_id,
                    'filename': doc.filename,
                    'uploaded_at': doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                    'page_count': page_count
                })
            
            return documents_info
            
        except Exception as e:
            print(f"Error listing documents: {e}")
            return []

    def delete_document(self, document_id):
        """Delete a document and all its associated data"""
        try:
            # Delete from vector database first
            self.vector_db.delete_document_embeddings(document_id)
            
            # Delete from SQL database (cascade will handle related records)
            document = self.session.query(Document).filter(
                Document.document_id == document_id
            ).first()
            
            if document:
                self.session.delete(document)
                self.session.commit()
                
                # Delete PNG files
                png_dir = os.path.join("storage/documents", document_id)
                if os.path.exists(png_dir):
                    import shutil
                    shutil.rmtree(png_dir)
                
                print(f"Document {document_id} deleted successfully")
                return True
            else:
                print(f"Document {document_id} not found")
                return False
                
        except Exception as e:
            print(f"Error deleting document: {e}")
            if self.session:
                self.session.rollback()
            return False

    def __del__(self):
        """Cleanup when object is destroyed"""
        if self.session:
            self.session.close()

    def _validate_element_type(self, element_type):
        """Validate element type against supported types"""
        supported_types = ['ALL_TEXT', 'FLOWCHART']
        return element_type in supported_types