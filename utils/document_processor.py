import os
import uuid
from pathlib import Path
from PIL import Image
import fitz  # PyMuPDF
from sqlalchemy.orm import sessionmaker
from database.connection import db_manager
from database.models import Document
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

    def generate_document_id(self, filename):
        """Generate document ID in format: [nama]_[unique_rand]"""
        # Remove file extension
        name_without_ext = os.path.splitext(filename)[0]
        
        # Clean filename (remove special characters, replace spaces with underscore)
        import re
        clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', name_without_ext)
        clean_name = re.sub(r'\s+', '_', clean_name).strip('_')
        
        # If clean_name is empty, use 'document'
        if not clean_name:
            clean_name = 'document'
        
        # Generate unique random string (8 characters)
        unique_rand = uuid.uuid4().hex[:8].upper()
        
        # Create document ID
        document_id = f"{clean_name}_{unique_rand}"
        
        return document_id

    def process_pdf_document(self, pdf_path, document_id=None):
        """
        Process a PDF document: convert to PNG pages, extract data, store in database
        Returns the document_id
        """
        try:
            # Get filename from path
            filename = os.path.basename(pdf_path)
            
            if not document_id:
                # Generate document ID using filename
                document_id = self.generate_document_id(filename)
            
            # Get file info
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
                try:
                    for page_num, png_filename, png_filepath in png_filepaths:
                        try:
                            # Process page with AI extraction (no need for DocumentPage)
                            extracted_elements = self.ai_processor.process_png_page(png_filepath)
                            
                            # Store elements in vector database only
                            for element_data in extracted_elements:
                                if element_data['plain_text']:
                                    embedding = self.ai_processor.generate_embeddings(element_data['plain_text'])
                                    if embedding:
                                        self.vector_db.add_element_embedding(
                                            element_id=f"{document_id}_page_{page_num}_{element_data['element_type']}",
                                            plain_text=element_data['plain_text'],
                                            embedding_vector=embedding,
                                            metadata={
                                                "document_id": str(document_id),
                                                "page_number": page_num,
                                                "element_type": element_data['element_type']
                                            }
                                        )
                            
                            self.session.commit()
                            print(f"Page {page_num} processed successfully with {len(extracted_elements)} elements")
                            
                        except Exception as e:
                            print(f"Error processing PNG page {page_num}: {e}")
                            if self.session:
                                self.session.rollback()
                            raise e
                    
                    print(f"Batch processed {len(png_filepaths)} pages successfully")
                    
                except Exception as e:
                    print(f"Error processing PNG pages batch: {e}")
                    if self.session:
                        self.session.rollback()
                    raise e
            
            print(f"Document {document_id} processed successfully with {page_count} pages")
            return document_id
            
        except Exception as e:
            print(f"Error processing PDF document: {e}")
            if self.session:
                self.session.rollback()
            raise e

    def get_document_pages_for_qa(self, document_id):
        """Get all pages for QA processing from vector database"""
        try:
            # Get pages from vector database metadata
            results = self.vector_db.collection.get(
                where={"document_id": document_id},
                include=["metadatas"]
            )
            
            pages_data = []
            if results['metadatas']:
                # Get unique page numbers
                page_numbers = set()
                for metadata in results['metadatas']:
                    page_num = metadata.get('page_number')
                    if page_num:
                        page_numbers.add(page_num)
                
                # Convert to list and sort
                for page_num in sorted(page_numbers):
                    # Get elements for this page
                    elements = []
                    for metadata in results['metadatas']:
                        if metadata.get('page_number') == page_num:
                            elements.append({
                                'element_type': metadata.get('element_type', 'UNKNOWN'),
                                'plain_text': metadata.get('plain_text', ''),
                                'similarity_score': 1 - metadata.get('distance', 1)
                            })
                    
                    # Add page data with elements
                    pages_data.append({
                        'page_number': page_num,
                        'page_id': page_num,
                        'elements': elements
                    })
            
            return pages_data
            
        except Exception as e:
            print(f"Error getting document pages for QA: {e}")
            return []

    def search_similar_content(self, document_id, query, top_k=5):
        """
        Search for similar content using vector database only.
        """
        try:
            query_embedding = self.ai_processor.generate_embeddings(query, task_type="RETRIEVAL_QUERY")
            if not query_embedding:
                return []
            
            # Search in vector database
            initial_results = self.vector_db.search_similar_elements(
                query_embedding=query_embedding,
                document_id=document_id,
                top_k=top_k
            )
            
            if not initial_results or not initial_results.get('metadatas') or not initial_results['metadatas'][0]:
                return []
            
            all_similar_elements = []
            for i, metadata in enumerate(initial_results['metadatas'][0]):
                similarity_score = 1 - initial_results['distances'][0][i]
                
                # Boost flowchart elements
                element_type = metadata.get('element_type', 'UNKNOWN')
                if element_type == 'FLOWCHART':
                    similarity_score *= 1.05
                    similarity_score = min(similarity_score, 1.0)

                if similarity_score > 0.5:
                    # Get plain_text from vector database
                    plain_text = initial_results['documents'][0][i] if initial_results.get('documents') and initial_results['documents'][0] else ""
                    
                    all_similar_elements.append({
                        'element_type': element_type,
                        'plain_text': plain_text,
                        'similarity_score': round(similarity_score, 3),
                        'page_number': metadata.get('page_number'),
                        'element_id': metadata.get('element_id')
                    })
            
            # Sort by similarity score
            all_similar_elements.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            # Get top element per page
            top_elements_per_page = {}
            for element in all_similar_elements:
                page_num = element['page_number']
                if page_num not in top_elements_per_page:
                    top_elements_per_page[page_num] = element
            
            # Return filtered results
            final_results = list(top_elements_per_page.values())
            final_results.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            return final_results[:2]
            
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
            
            # Get page count from file system
            page_dir = os.path.join("storage/documents", document_id)
            page_count = len([f for f in os.listdir(page_dir) if f.endswith('.png')])
            
            return {
                'document_id': document.document_id,
                'filename': document.filename,
                'uploaded_at': document.uploaded_at.isoformat() if document.uploaded_at else None,
                'page_count': page_count
            }
            
        except Exception as e:
            print(f"Error getting document info: {e}")
            return None
    
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