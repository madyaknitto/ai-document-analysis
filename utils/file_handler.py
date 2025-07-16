import os
import uuid
import shutil
from datetime import datetime
from PIL import Image
from config import Config

class FileHandler:
    def __init__(self):
        self.upload_dir = "uploads"
        self.ensure_upload_directory()
    
    def ensure_upload_directory(self):
        """Ensure upload directory exists"""
        if not os.path.exists(self.upload_dir):
            os.makedirs(self.upload_dir)
    
    def save_uploaded_file(self, uploaded_file):
        """Save uploaded file and return file info"""
        try:
            # Generate unique filename
            file_extension = os.path.splitext(uploaded_file.name)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}{file_extension}"
            file_path = os.path.join(self.upload_dir, unique_filename)
            
            # Check file extension
            if file_extension not in Config.SUPPORTED_EXTENSIONS:
                return None, f"Format file tidak didukung. Gunakan: {', '.join(Config.SUPPORTED_EXTENSIONS)}"
            
            # Check file size (in MB)
            file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
            if file_size_mb > Config.MAX_FILE_SIZE:
                return None, f"File terlalu besar. Maksimal {Config.MAX_FILE_SIZE}MB"
            
            # Save file
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getvalue())
            
            # Validate image
            try:
                img = Image.open(file_path)
                img.verify()
            except Exception as e:
                os.remove(file_path)
                return None, "File gambar tidak valid"
            
            return {
                "file_path": file_path,
                "original_name": uploaded_file.name,
                "unique_name": unique_filename,
                "file_size": len(uploaded_file.getvalue()),
                "file_extension": file_extension,
                "upload_date": datetime.now()
            }, None
            
        except Exception as e:
            return None, f"Error menyimpan file: {str(e)}"
    
    def delete_file(self, file_path):
        """Delete file from filesystem"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")
            return False
    
    def get_file_info(self, file_path):
        """Get file information"""
        try:
            if not os.path.exists(file_path):
                return None
            
            stat = os.stat(file_path)
            return {
                "file_path": file_path,
                "file_size": stat.st_size,
                "created_date": datetime.fromtimestamp(stat.st_ctime),
                "modified_date": datetime.fromtimestamp(stat.st_mtime),
                "exists": True
            }
        except Exception as e:
            return None
    
    def validate_image(self, file_path):
        """Validate that file is a valid image"""
        try:
            img = Image.open(file_path)
            img.verify()
            return True
        except Exception:
            return False
    
    def get_image_dimensions(self, file_path):
        """Get image dimensions"""
        try:
            img = Image.open(file_path)
            return img.size  # (width, height)
        except Exception:
            return None
    
    def cleanup_old_files(self, days_old=30):
        """Clean up files older than specified days"""
        try:
            cutoff_date = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
            cleaned_files = []
            
            for filename in os.listdir(self.upload_dir):
                file_path = os.path.join(self.upload_dir, filename)
                if os.path.isfile(file_path):
                    file_stat = os.stat(file_path)
                    if file_stat.st_mtime < cutoff_date:
                        os.remove(file_path)
                        cleaned_files.append(filename)
            
            return cleaned_files
            
        except Exception as e:
            print(f"Error cleaning up files: {e}")
            return [] 