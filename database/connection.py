import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize database connection"""
        try:
            # Ensure storage directory exists
            os.makedirs("storage", exist_ok=True)
            
            # Create SQLite database
            db_path = os.path.join("storage", "document_analysis.db")
            self.engine = create_engine(
                f"sqlite:///{db_path}",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=False
            )
            
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            
            # Create tables
            self.create_tables()
            
            print("Database initialized successfully")
            
        except Exception as e:
            print(f"Error initializing database: {e}")
            raise e
    
    def create_tables(self):
        """Create database tables with new schema"""
        try:
            # Create tables using raw SQL for better control
            with self.engine.connect() as conn:
                # Create documents table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS documents (
                        document_id VARCHAR(100) PRIMARY KEY,
                        filename VARCHAR(255) NOT NULL,
                        filepath TEXT NOT NULL,
                        uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Create document_pages table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS document_pages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        document_id INTEGER,
                        page_number INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Create page_elements table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS page_elements (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        page_id INTEGER,
                        element_type TEXT,
                        change_status TEXT,
                        content_json TEXT,
                        plain_text TEXT,
                        embedding_id TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                # Create qa_history table
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS qa_history (
                        id VARCHAR PRIMARY KEY,
                        document_id VARCHAR(100),
                        question TEXT NOT NULL,
                        answer TEXT NOT NULL,
                        response_time VARCHAR(50),
                        similarity_score FLOAT,
                        page_references TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                
                conn.commit()
                print("Database tables created successfully")
                
        except Exception as e:
            print(f"Error creating tables: {e}")
            raise e
    
    def get_session(self):
        """Get database session"""
        if not self.SessionLocal:
            raise Exception("Database not initialized")
        return self.SessionLocal()
    
    def close(self):
        """Close database connection"""
        if self.engine:
            self.engine.dispose()

# Global database manager instance
db_manager = DatabaseManager()

 