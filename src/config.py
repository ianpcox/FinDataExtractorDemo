"""Simplified application configuration"""

import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings - simplified version"""
    
    # Application
    APP_NAME: str = "FinDataExtractorDEMO"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Demo Mode (bypasses Azure dependencies)
    DEMO_MODE: bool = os.getenv("DEMO_MODE", "False").lower() == "true"
    
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
    # Force SDK for blob URLs (avoid public HTTP fetch); if true, blob URLs will be fetched via SDK first
    USE_BLOB_SDK_FOR_URLS: bool = os.getenv("USE_BLOB_SDK_FOR_URLS", "False").lower() == "true"
    
    # Database
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./findataextractor.db")

    # LLM Fallback (optional)
    USE_LLM_FALLBACK: bool = os.getenv("USE_LLM_FALLBACK", "False").lower() == "true"
    AOAI_ENDPOINT: Optional[str] = os.getenv("AOAI_ENDPOINT")
    AOAI_API_KEY: Optional[str] = os.getenv("AOAI_API_KEY")
    AOAI_DEPLOYMENT_NAME: Optional[str] = os.getenv("AOAI_DEPLOYMENT_NAME")
    AOAI_API_VERSION: str = os.getenv("AOAI_API_VERSION", "2024-02-15-preview")
    
    # File Processing
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
    SUPPORTED_FILE_TYPES: str = os.getenv("SUPPORTED_FILE_TYPES", "pdf")
    EXTRACTION_CONFIDENCE_THRESHOLD: float = float(os.getenv("EXTRACTION_CONFIDENCE_THRESHOLD", "0.85"))
    
    # PDF Preprocessing (optional - reduces costs and improves extraction accuracy)
    ENABLE_PDF_PREPROCESSING: bool = os.getenv("ENABLE_PDF_PREPROCESSING", "False").lower() == "true"
    ENABLE_PDF_IMAGE_OPTIMIZATION: bool = os.getenv("ENABLE_PDF_IMAGE_OPTIMIZATION", "False").lower() == "true"
    ENABLE_PDF_ROTATION_CORRECTION: bool = os.getenv("ENABLE_PDF_ROTATION_CORRECTION", "False").lower() == "true"
    PDF_PREPROCESS_TARGET_DPI: int = int(os.getenv("PDF_PREPROCESS_TARGET_DPI", "300"))  # Target DPI for image optimization
    PDF_PREPROCESS_MAX_DPI: int = int(os.getenv("PDF_PREPROCESS_MAX_DPI", "600"))  # Maximum DPI before downscaling
    PDF_PREPROCESS_TIMEOUT_SEC: float = float(os.getenv("PDF_PREPROCESS_TIMEOUT_SEC", "30"))  # Timeout in seconds for preprocessing (SLO)
    
    # Storage (local file storage path if not using Azure)
    LOCAL_STORAGE_PATH: str = os.getenv("LOCAL_STORAGE_PATH", "./storage")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Optional[str] = os.getenv("LOG_FILE")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from .env that aren't in this model


# Global settings instance
settings = Settings()

