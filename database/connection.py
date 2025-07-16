from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base
from config import Config
import os

class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self.initialize_database()
    
    def initialize_database(self):
        """Initialize database connection and create tables"""
        try:
            self.engine = create_engine(Config.DATABASE_URL, echo=False)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            
            # Create tables
            Base.metadata.create_all(bind=self.engine)
            print("Database initialized successfully")
            
        except Exception as e:
            print(f"Error initializing database: {e}")
            raise e
    
    def get_session(self):
        """Get database session"""
        if self.SessionLocal is None:
            raise Exception("Database not initialized")
        return self.SessionLocal()
    
    def close_session(self, session):
        """Close database session"""
        if session:
            session.close()

# Global database manager instance
db_manager = DatabaseManager()

def get_db():
    """Dependency to get database session"""
    session = db_manager.get_session()
    try:
        yield session
    finally:
        db_manager.close_session(session) 