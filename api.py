from flask import Flask, jsonify, request
from flask_cors import CORS
from sqlalchemy.orm import joinedload, subqueryload

from utils.document_processor import DocumentProcessor
from utils.vector_database import VectorDatabaseManager
from database.connection import db_manager
from database.models import Document, DocumentPage, QAHistory, PageElement # Pastikan PageElement di-import

app = Flask(__name__)
CORS(app)

# Initialize processors
vector_db = VectorDatabaseManager()
document_processor = DocumentProcessor()

@app.route('/api/chroma/list', methods=['GET'])
def list_chroma_data():
    """API endpoint untuk list semua data di Chroma DB - Diperbaiki dengan error recovery"""
    try:
        # Check if vector database is healthy
        if not vector_db.is_healthy():
            print("Vector database unhealthy, attempting recovery...")
            if not vector_db.force_reset():
                return jsonify({
                    "success": False, 
                    "error": "Vector database tidak dapat dipulihkan. Silakan restart aplikasi."
                }), 500

        # Get collection stats
        stats = vector_db.get_collection_stats()
        if stats and "error" in stats:
            return jsonify({"success": False, "error": stats["error"]}), 500

        # Get collection data with error handling
        results = vector_db.get_collection_data(include=["documents", "metadatas", "embeddings"])
        if results is None:
            return jsonify({"success": False, "error": "Gagal mengambil data dari vector database"}), 500

        # Process results
        documents_data = {}
        doc_ids_to_fetch = set()

        if results and 'ids' in results and len(results['ids']) > 0:
            for i in range(len(results['ids'])):
                meta = results['metadatas'][i] if results['metadatas'] else {}
                doc_id = meta.get('document_id')
                if not doc_id: 
                    continue

                doc_ids_to_fetch.add(doc_id)
                
                if doc_id not in documents_data:
                    documents_data[doc_id] = {"document_id": doc_id, "pages": [], "total_pages": 0}
                
                documents_data[doc_id]["pages"].append({
                    "page_number": meta.get('page_number'),
                    "element_type": meta.get('element_type'),
                    "content_preview": (results['documents'][i] or "") if results['documents'] else "",
                })
                documents_data[doc_id]["total_pages"] += 1
        
        # Get SQL document info
        sql_docs_map = {}
        if doc_ids_to_fetch:
            try:
                with db_manager.get_session() as session:
                    sql_docs = session.query(Document).filter(Document.document_id.in_(list(doc_ids_to_fetch))).all()
                    sql_docs_map = {doc.document_id: doc for doc in sql_docs}
            except Exception as sql_error:
                print(f"SQL error: {sql_error}")
                # Continue without SQL data
        
        # Combine data
        for doc_id, data in documents_data.items():
            sql_doc = sql_docs_map.get(doc_id)
            if sql_doc:
                data["filename"] = sql_doc.filename
                data["uploaded_at"] = sql_doc.uploaded_at.isoformat() if sql_doc.uploaded_at else None
            else:
                data["filename"] = "Unknown"
                data["uploaded_at"] = None

        return jsonify({
            "success": True,
            "stats": stats,
            "data": list(documents_data.values()),
            "total_documents": len(documents_data),
            "vector_db_healthy": vector_db.is_healthy()
        })
        
    except Exception as e:
        print(f"Error in list_chroma_data: {e}")
        return jsonify({
            "success": False, 
            "error": f"Terjadi kesalahan: {str(e)}",
            "vector_db_healthy": vector_db.is_healthy()
        }), 500

@app.route('/api/chroma/reset', methods=['POST'])
def reset_chroma_database():
    """API endpoint untuk reset vector database"""
    try:
        success = vector_db.force_reset()
        if success:
            return jsonify({
                "success": True,
                "message": "Vector database berhasil direset"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Gagal reset vector database"
            }), 500
            
    except Exception as e:
        print(f"Error resetting vector database: {e}")
        return jsonify({
            "success": False,
            "error": f"Terjadi kesalahan: {str(e)}"
        }), 500

@app.route('/api/chroma/health', methods=['GET'])
def check_chroma_health():
    """API endpoint untuk cek kesehatan vector database"""
    try:
        is_healthy = vector_db.is_healthy()
        stats = vector_db.get_collection_stats() if is_healthy else None
        
        return jsonify({
            "success": True,
            "healthy": is_healthy,
            "stats": stats
        })
        
    except Exception as e:
        print(f"Error checking vector database health: {e}")
        return jsonify({
            "success": False,
            "healthy": False,
            "error": f"Terjadi kesalahan: {str(e)}"
        }), 500

@app.route('/api/embeddings/stats/<document_id>', methods=['GET'])
def get_embedding_stats(document_id):
    """API endpoint untuk mendapatkan statistik embedding dokumen"""
    try:
        stats = document_processor.get_embedding_statistics(document_id)
        return jsonify({
            "success": True,
            "stats": stats
        })
        
    except Exception as e:
        print(f"Error getting embedding stats: {e}")
        return jsonify({
            "success": False,
            "error": f"Terjadi kesalahan: {str(e)}"
        }), 500

@app.route('/api/embeddings/regenerate/<document_id>', methods=['POST'])
def regenerate_embeddings(document_id):
    """API endpoint untuk regenerate embeddings dokumen"""
    try:
        result = document_processor.regenerate_embeddings(document_id)
        
        if 'error' in result:
            return jsonify({
                "success": False,
                "error": result['error']
            }), 500
        
        return jsonify({
            "success": True,
            "message": f"Berhasil regenerate {result['regenerated_count']} embeddings",
            "result": result
        })
        
    except Exception as e:
        print(f"Error regenerating embeddings: {e}")
        return jsonify({
            "success": False,
            "error": f"Terjadi kesalahan: {str(e)}"
        }), 500

@app.route('/api/embeddings/test', methods=['GET'])
def test_embedding_functionality():
    """API endpoint untuk test embedding functionality"""
    try:
        result = document_processor.test_embedding_functionality()
        return jsonify(result)
        
    except Exception as e:
        print(f"Error testing embedding functionality: {e}")
        return jsonify({
            "success": False,
            "error": f"Terjadi kesalahan: {str(e)}"
        }), 500

@app.route('/api/qa/test/<document_id>', methods=['GET'])
def test_question_answering(document_id):
    """API endpoint untuk test question answering functionality"""
    try:
        test_question = request.args.get('question', 'Apa isi dokumen ini?')
        result = document_processor.test_question_answering(document_id, test_question)
        return jsonify(result)
        
    except Exception as e:
        print(f"Error testing question answering: {e}")
        return jsonify({
            "success": False,
            "error": f"Terjadi kesalahan: {str(e)}"
        }), 500

@app.route('/api/sqlite/documents', methods=['GET'])
def list_sqlite_documents():
    """API endpoint untuk list semua documents dari SQLite - Diperbaiki"""
    try:
        with db_manager.get_session() as session:
            # PERBAIKAN: Gunakan subqueryload untuk efisiensi
            # Ini akan menjalankan total 3 query, bukan 1 + 2*N queries
            documents = session.query(Document).options(
                subqueryload(Document.pages),
                subqueryload(Document.qa_history)
            ).order_by(Document.uploaded_at.desc()).all()
            
            documents_data = []
            for doc in documents:
                # PERBAIKAN: Hitung dari relasi yang sudah di-load, bukan query baru
                page_count = len(doc.pages)
                qa_count = len(doc.qa_history)
                
                documents_data.append({
                    "document_id": doc.document_id,
                    "filename": doc.filename,
                    "filepath": doc.filepath,
                    "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                    "page_count": page_count,
                    "qa_history_count": qa_count
                })
            
            return jsonify({
                "success": True,
                "data": documents_data,
                "total_documents": len(documents_data)
            })
            
    except Exception as e:
        return jsonify({"success": False, "error": f"Terjadi kesalahan: {str(e)}"}), 500

@app.route('/api/sqlite/pages/<string:document_id>', methods=['GET'])
def list_document_pages(document_id):
    """API endpoint untuk list semua pages dari sebuah dokumen - Diperbaiki"""
    try:
        with db_manager.get_session() as session:
            # PERBAIKAN: Gunakan joinedload untuk mengambil elemen terkait dalam satu query
            query = session.query(DocumentPage).options(
                subqueryload(DocumentPage.elements)  # Ambil semua elemen untuk setiap halaman
            ).filter(DocumentPage.document_id == document_id)
            
            pages = query.order_by(DocumentPage.page_number).all()
            
            if not pages:
                 return jsonify({"success": False, "error": "Dokumen atau halaman tidak ditemukan"}), 404

            pages_data = []
            for page in pages:
                elements_data = [{
                    "id": el.id,
                    "element_type": el.element_type,
                    "plain_text": el.plain_text,
                    "content_json": el.content_json
                } for el in page.elements]

                pages_data.append({
                    "id": page.id,
                    "page_number": page.page_number,
                    "created_at": page.created_at.isoformat() if page.created_at else None,
                    "elements": elements_data, # Data elemen yang sudah di-load
                    "element_count": len(page.elements)
                })
            
            # Ambil informasi dokumen induk sekali saja
            document = session.query(Document).filter(Document.document_id == document_id).first()

            return jsonify({
                "success": True,
                "document_id": document_id,
                "document_filename": document.filename if document else "Unknown",
                "data": pages_data,
                "total_pages": len(pages_data),
            })
            
    except Exception as e:
        return jsonify({"success": False, "error": f"Terjadi kesalahan: {str(e)}"}), 500


@app.route('/api/sqlite/qa-history', methods=['GET'])
def list_sqlite_qa_history():
    """API endpoint untuk list semua QA history dari SQLite - Diperbaiki"""
    try:
        with db_manager.get_session() as session:
            document_id = request.args.get('document_id')
            
            # PERBAIKAN: Gunakan joinedload untuk mengambil info dokumen induk dalam satu query
            query = session.query(QAHistory).options(joinedload(QAHistory.document))
            
            if document_id:
                query = query.filter(QAHistory.document_id == document_id)
            
            qa_history = query.order_by(QAHistory.created_at.desc()).all()
            
            qa_data = []
            for qa in qa_history:
                # PERBAIKAN: Akses langsung dari relasi, bukan query baru
                doc_filename = qa.document.filename if qa.document else "Unknown"

                qa_data.append({
                    "id": qa.id,
                    "document_id": qa.document_id,
                    "document_filename": doc_filename,
                    "question": qa.question,
                    "answer": qa.answer,
                    "response_time": qa.response_time,
                    "similarity_score": qa.similarity_score,
                    "page_references": qa.page_references,
                    "created_at": qa.created_at.isoformat() if qa.created_at else None
                })
            
            return jsonify({
                "success": True,
                "data": qa_data,
                "total_qa_history": len(qa_data),
                "filters": {"document_id": document_id}
            })
            
    except Exception as e:
        return jsonify({"success": False, "error": f"Terjadi kesalahan: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)