"""Simplified application configuration"""

import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings - simplified version"""
    
    # Application
    APP_NAME: str = "FinDataExtractorVanilla"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # API
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    
    # Azure Document Intelligence (Required)
    AZURE_FORM_RECOGNIZER_ENDPOINT: Optional[str] = os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT")
    AZURE_FORM_RECOGNIZER_KEY: Optional[str] = os.getenv("AZURE_FORM_RECOGNIZER_KEY")
    AZURE_FORM_RECOGNIZER_MODEL: str = os.getenv("AZURE_FORM_RECOGNIZER_MODEL", "prebuilt-invoice")
    
    # Azure Storage (Optional - can use local storage)
    AZURE_STORAGE_ACCOUNT_NAME: Optional[str] = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
    AZURE_STORAGE_CONNECTION_STRING: Optional[str] = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    AZURE_STORAGE_CONTAINER_RAW: str = os.getenv("AZURE_STORAGE_CONTAINER_RAW", "invoices-raw")
    AZURE_STORAGE_CONTAINER_PROCESSED: str = os.getenv("AZURE_STORAGE_CONTAINER_PROCESSED", "invoices-processed")
    
    # Database
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./findataextractor.db")
    
    # File Processing
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    SUPPORTED_FILE_TYPES: str = os.getenv("SUPPORTED_FILE_TYPES", "pdf")
    EXTRACTION_CONFIDENCE_THRESHOLD: float = float(os.getenv("EXTRACTION_CONFIDENCE_THRESHOLD", "0.85"))
    
    # Storage (local file storage path if not using Azure)
    LOCAL_STORAGE_PATH: str = os.getenv("LOCAL_STORAGE_PATH", "./storage")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Optional[str] = os.getenv("LOG_FILE")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()

