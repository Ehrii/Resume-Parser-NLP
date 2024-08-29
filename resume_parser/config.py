# config.py
import os

class Config:
    SECRET_KEY = os.urandom(24)
    UPLOAD_FOLDER = 'uploads/'
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx'}

    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = ''
    MYSQL_DB = 'finalproj'
