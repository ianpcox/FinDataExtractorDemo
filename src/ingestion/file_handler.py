"""Simplified file handler - supports local storage and optional Azure Blob Storage"""

import os
from datetime import datetime
from typing import Optional
from uuid import uuid4
from pathlib import Path
import logging

from src.config import settings

logger = logging.getLogger(__name__)


class FileHandler:
    """Simplified file handler - supports local storage with optional Azure Blob Storage"""
    
    def __init__(
        self,
        storage_path: Optional[str] = None,
        use_azure: bool = False
    ):
        """
        Initialize file handler
        
        Args:
            storage_path: Local storage path (defaults to settings.LOCAL_STORAGE_PATH)
            use_azure: Whether to use Azure Blob Storage (requires Azure credentials)
        """
        self.use_azure = use_azure
        self.storage_path = Path(storage_path or settings.LOCAL_STORAGE_PATH)
        
        if not self.use_azure:
            # Setup local storage
            self.storage_path.mkdir(parents=True, exist_ok=True)
            self.raw_path = self.storage_path / "raw"
            self.processed_path = self.storage_path / "processed"
            self.raw_path.mkdir(exist_ok=True)
            self.processed_path.mkdir(exist_ok=True)
            logger.info(f"Using local storage at: {self.storage_path}")
        else:
            # Setup Azure Blob Storage
            try:
                from azure.storage.blob import BlobServiceClient
                from azure.identity import DefaultAzureCredential
                
                connection_string = settings.AZURE_STORAGE_CONNECTION_STRING
                if connection_string:
                    self.blob_service_client = BlobServiceClient.from_connection_string(
                        connection_string
                    )
                elif settings.AZURE_STORAGE_ACCOUNT_NAME:
                    account_url = f"https://{settings.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
                    credential = DefaultAzureCredential()
                    self.blob_service_client = BlobServiceClient(
                        account_url=account_url,
                        credential=credential
                    )
                else:
                    raise ValueError("Azure storage credentials not configured")
                
                self.container_client = self.blob_service_client.get_container_client(
                    settings.AZURE_STORAGE_CONTAINER_RAW
                )
                self._ensure_container_exists()
                logger.info("Using Azure Blob Storage")
            except ImportError:
                logger.warning("Azure storage libraries not available, falling back to local storage")
                self.use_azure = False
                self.storage_path.mkdir(parents=True, exist_ok=True)
                self.raw_path = self.storage_path / "raw"
                self.processed_path = self.storage_path / "processed"
                self.raw_path.mkdir(exist_ok=True)
                self.processed_path.mkdir(exist_ok=True)
    
    def _ensure_container_exists(self):
        """Ensure Azure container exists"""
        if not self.use_azure:
            return
        try:
            self.container_client.get_container_properties()
        except Exception:
            self.container_client.create_container()
            logger.info(f"Created container '{settings.AZURE_STORAGE_CONTAINER_RAW}'")
    
    def upload_file(
        self,
        file_content: bytes,
        file_name: str,
        metadata: Optional[dict] = None
    ) -> dict:
        """
        Upload a file to storage
        
        Args:
            file_content: File content as bytes
            file_name: Original file name
            metadata: Optional metadata dictionary
            
        Returns:
            Dictionary with file information
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        file_id = str(uuid4())[:8]
        file_extension = os.path.splitext(file_name)[1]
        stored_name = f"{timestamp}_{file_id}{file_extension}"
        
        if self.use_azure:
            return self._upload_to_azure(file_content, stored_name, file_name, metadata)
        else:
            return self._upload_to_local(file_content, stored_name, file_name, metadata)
    
    def _upload_to_local(
        self,
        file_content: bytes,
        stored_name: str,
        original_name: str,
        metadata: Optional[dict]
    ) -> dict:
        """Upload file to local storage"""
        file_path = self.raw_path / stored_name
        file_path.write_bytes(file_content)
        
        result = {
            "file_path": str(file_path),
            "stored_name": stored_name,
            "original_filename": original_name,
            "size": len(file_content),
            "upload_date": datetime.utcnow(),
            "storage_type": "local"
        }
        
        logger.info(f"Uploaded file '{original_name}' to local storage: {file_path}")
        return result
    
    def _upload_to_azure(
        self,
        file_content: bytes,
        stored_name: str,
        original_name: str,
        metadata: Optional[dict]
    ) -> dict:
        """Upload file to Azure Blob Storage"""
        blob_client = self.container_client.get_blob_client(stored_name)
        
        blob_metadata = {
            "original_filename": original_name,
            "upload_timestamp": datetime.utcnow().isoformat(),
        }
        if metadata:
            blob_metadata.update(metadata)
        
        blob_client.upload_blob(
            data=file_content,
            metadata=blob_metadata,
            overwrite=False
        )
        
        result = {
            "blob_name": stored_name,
            "blob_url": blob_client.url,
            "container": settings.AZURE_STORAGE_CONTAINER_RAW,
            "size": len(file_content),
            "upload_date": datetime.utcnow(),
            "original_filename": original_name,
            "storage_type": "azure"
        }
        
        logger.info(f"Uploaded file '{original_name}' to Azure Blob Storage: {stored_name}")
        return result
    
    def download_file(self, file_identifier: str) -> bytes:
        """
        Download a file from storage
        
        Args:
            file_identifier: File path (local) or blob name (Azure)
            
        Returns:
            File content as bytes
        """
        if self.use_azure:
            blob_client = self.container_client.get_blob_client(file_identifier)
            return blob_client.download_blob().readall()
        else:
            file_path = Path(file_identifier)
            if not file_path.is_absolute():
                file_path = self.raw_path / file_identifier
            return file_path.read_bytes()
    
    def get_file_path(self, file_identifier: str) -> str:
        """Get full file path/URL"""
        if self.use_azure:
            blob_client = self.container_client.get_blob_client(file_identifier)
            return blob_client.url
        else:
            file_path = Path(file_identifier)
            if not file_path.is_absolute():
                file_path = self.raw_path / file_identifier
            return str(file_path)

