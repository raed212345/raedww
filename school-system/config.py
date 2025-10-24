import os

class Config:
    SECRET_KEY = 'school_system_secret_key_2024_advanced'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///data/database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static/uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size