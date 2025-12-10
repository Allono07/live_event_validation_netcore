"""Configuration module for the application."""
import os
from datetime import timedelta


class Config:
    """Base configuration."""
    
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'mysql+pymysql://val_user:strongpassword@127.0.0.1:3306/validation_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Upload configuration
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'csv'}
    
    # Socket.IO
    SOCKETIO_MESSAGE_QUEUE = os.environ.get('SOCKETIO_MESSAGE_QUEUE')
    
    # CORS
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*')
    
    # Email configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 465))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'False').lower() == 'true'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'True').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@validation.app')
    MAIL_MAX_EMAILS = None
    MAIL_SUPPRESS_SEND = False
    MAIL_ASCII_ATTACHMENTS = False
    # Delivery mode for emails/OTPs: 'send' or 'log'
    OTP_DELIVERY_MODE = os.environ.get('OTP_DELIVERY_MODE', 'log')
    
    # JWT configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    
    # Celery configuration (async tasks)
    CELERY_BROKER_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_RESULT_BACKEND = os.environ.get('REDIS_URL', 'redis://localhost:6379/1')
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TIMEZONE = 'UTC'
    CELERY_ENABLE_UTC = True
    CELERY_TASK_SOFT_TIME_LIMIT = 300
    CELERY_TASK_TIME_LIMIT = 600
    
    # App settings
    APP_URL = os.environ.get('APP_URL', 'http://localhost:5001')


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    FLASK_ENV = 'development'
    # In development, do not send real emails
    MAIL_SUPPRESS_SEND = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    FLASK_ENV = 'production'
    SESSION_COOKIE_SECURE = True  # Require HTTPS in production


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    MAIL_SUPPRESS_SEND = True


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}