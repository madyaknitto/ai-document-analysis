from flask import Flask, jsonify, request
from flask_cors import CORS

from utils.document_processor import DocumentProcessor
from utils.vector_database import VectorDatabaseManager
from database.connection import db_manager
from database.models import Document, QAHistory

app = Flask(__name__)
CORS(app)

# Initialize processors
vector_db = VectorDatabaseManager()
document_processor = DocumentProcessor()

@app.route('/api/vector/list', methods=['GET'])
def list_vector_data():
    """API endpoint untuk list semua data di Vector Database"""
    try:
        # Check if vector database is healthy
        if not vector_db.is_healthy():
            return jsonify({
                "success": False, 
                "error": "Vector database tidak sehat. Silakan restart aplikasi."
            }), 500

        # Get collection stats
        stats = vector_db.get_collection_stats()
        if stats and "error" in stats:
            return jsonify({"success": False, "error": stats["error"]}), 500

                # Get collection data with embeddings and documents
        results = vector_db.get_collection_data(include=["documents", "metadatas", "embeddings"])
        if results is None:
            return jsonify({"success": False, "error": "Gagal mengambil data dari vector database"}), 500

        # Process results
        documents_data = {}
        doc_ids_to_fetch = set()
        embeddings_data = []
        
        if results.get('metadatas') and results['metadatas']:
            metadatas = results['metadatas']
            documents = results.get('documents', [])
            embeddings = results.get('embeddings', [])
            
            # Process metadata
            if isinstance(metadatas, list):
                for i, metadata_item in enumerate(metadatas):
                    if isinstance(metadata_item, dict):
                        # Process metadata item
                        doc_id = metadata_item.get('document_id')
                        if doc_id:
                            doc_ids_to_fetch.add(doc_id)
                            if doc_id not in documents_data:
                                documents_data[doc_id] = {
                                    'document_id': doc_id,
                                    'embeddings_count': 0,
                                    'pages': {}
                                }
                            documents_data[doc_id]['embeddings_count'] += 1
                            
                            # Group by page
                            page_num = metadata_item.get('page_number')
                            if page_num:
                                if page_num not in documents_data[doc_id]['pages']:
                                    documents_data[doc_id]['pages'][page_num] = {
                                        'page_number': page_num,
                                        'elements': []
                                    }
                                
                                element_type = metadata_item.get('element_type', 'UNKNOWN')
                                element_id = metadata_item.get('element_id', 'N/A')
                                
                                # Get document content and embedding
                                document_content = documents[i] if i < len(documents) else ""
                                embedding_vector = embeddings[i] if i < len(embeddings) else None
                                
                                # Process embedding vector
                                embedding_info = None
                                if embedding_vector is not None:
                                    if hasattr(embedding_vector, 'tolist'):
                                        embedding_list = embedding_vector.tolist()
                                    else:
                                        embedding_list = list(embedding_vector)
                                    
                                    embedding_info = {
                                        'length': len(embedding_list),
                                        'preview': embedding_list[:10],  # First 10 dimensions
                                    }
                                
                                element_info = {
                                    'element_type': element_type,
                                    'element_id': element_id,
                                    'document_content': document_content[:500] + "..." if len(document_content) > 500 else document_content,  # Truncate long content
                                    'document_length': len(document_content),
                                    'embedding': embedding_info
                                }
                                
                                documents_data[doc_id]['pages'][page_num]['elements'].append(element_info)
                                
                                # Add to embeddings data for detailed view
                                embeddings_data.append({
                                    'id': metadata_item.get('element_id', 'N/A'),
                                    'document_id': doc_id,
                                    'page_number': page_num,
                                    'element_type': element_type,
                                    'metadata': metadata_item,
                                    'document_content': document_content,
                                    'embedding': embedding_info
                                })

        # Fetch document details from SQL database
        if doc_ids_to_fetch:
            with db_manager.get_session() as session:
                documents = session.query(Document).filter(
                    Document.document_id.in_(list(doc_ids_to_fetch))
                ).all()
                
                for doc in documents:
                    if doc.document_id in documents_data:
                        documents_data[doc.document_id]['filename'] = doc.filename
                        documents_data[doc.document_id]['uploaded_at'] = doc.uploaded_at.isoformat() if doc.uploaded_at else None

        return jsonify({
            "success": True,
            "data": list(documents_data.values()),
            "embeddings": embeddings_data,
            "stats": stats
        })

    except Exception as e:
        print(f"Error in list_vector_data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Terjadi kesalahan: {str(e)}"
        }), 500

@app.route('/api/sqlite/list', methods=['GET'])
def list_sqlite_data():
    """API endpoint untuk list semua data di SQLite Database"""
    try:
        with db_manager.get_session() as session:
            # Get all documents
            documents = session.query(Document).all()
            
            documents_data = []
            for doc in documents:
                # Get QA history count
                qa_count = session.query(QAHistory).filter(
                    QAHistory.document_id == doc.document_id
                ).count()
                
                doc_info = {
                    'document_id': doc.document_id,
                    'filename': doc.filename,
                    'filepath': doc.filepath,
                    'uploaded_at': doc.uploaded_at.isoformat() if doc.uploaded_at else None,
                    'qa_history_count': qa_count
                }
                documents_data.append(doc_info)
            
            # Get all QA history
            qa_records = session.query(QAHistory).order_by(QAHistory.created_at.desc()).all()
            
            qa_data = []
            for qa in qa_records:
                qa_info = {
                    'id': qa.id,
                    'document_id': qa.document_id,
                    'question': qa.question,
                    'answer': qa.answer,
                    'response_time': qa.response_time,
                    'similarity_score': qa.similarity_score,
                    'page_references': qa.page_references,
                    'created_at': qa.created_at.isoformat() if qa.created_at else None
                }
                qa_data.append(qa_info)
            
            return jsonify({
                "success": True,
                "documents": documents_data,
                "qa_history": qa_data,
                "stats": {
                    "total_documents": len(documents_data),
                    "total_qa_records": len(qa_data)
                }
            })
            
    except Exception as e:
        print(f"Error in list_sqlite_data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": f"Terjadi kesalahan: {str(e)}"
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        with db_manager.get_session() as session:
            from sqlalchemy import text
            session.execute(text("SELECT 1"))
        
        # Check vector database
        is_healthy = vector_db.is_healthy()
        
        return jsonify({
            "success": True,
            "status": "healthy",
            "database": "connected",
            "vector_database": "healthy" if is_healthy else "unhealthy",
            "timestamp": "2024-01-01T00:00:00Z"
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "status": "unhealthy",
            "error": str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000) 