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
        # If identifier is a URL, optionally force SDK first (for private blobs), else HTTP then SDK fallback
        if isinstance(file_identifier, str) and file_identifier.lower().startswith(("http://", "https://")):
            def download_via_sdk() -> bytes:
                from urllib.parse import urlsplit
                from azure.storage.blob import BlobServiceClient
                split = urlsplit(file_identifier)
                parts = split.path.lstrip("/").split("/", 1)
                if len(parts) == 2:
                    container, blob_name = parts
                    if settings.AZURE_STORAGE_CONNECTION_STRING:
                        svc = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
                        blob_client = svc.get_blob_client(container=container, blob=blob_name)
                        return blob_client.download_blob().readall()
                    elif settings.AZURE_STORAGE_ACCOUNT_NAME and settings.AZURE_STORAGE_ACCOUNT_KEY:
                        from azure.core.credentials import AzureNamedKeyCredential
                        credential = AzureNamedKeyCredential(settings.AZURE_STORAGE_ACCOUNT_NAME, settings.AZURE_STORAGE_ACCOUNT_KEY)
                        account_url = f"https://{settings.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
                        svc = BlobServiceClient(account_url=account_url, credential=credential)
                        blob_client = svc.get_blob_client(container=container, blob=blob_name)
                        return blob_client.download_blob().readall()
                raise ValueError("Could not parse container/blob from URL")

            if getattr(settings, "USE_BLOB_SDK_FOR_URLS", False):
                try:
                    return download_via_sdk()
                except Exception as e:
                    logger.warning(f"SDK download failed for URL, falling back to HTTP: {e}")

            try:
                import requests
                resp = requests.get(file_identifier, timeout=30)
                resp.raise_for_status()
                return resp.content
            except Exception as e:
                logger.warning(f"HTTP download failed, trying blob SDK: {e}")
                try:
                    return download_via_sdk()
                except Exception as e2:
                    logger.error(f"Failed to download file via Azure SDK: {e2}")
                # If both fail, re-raise original
                raise

        if self.use_azure:
            blob_client = self.container_client.get_blob_client(file_identifier)
            return blob_client.download_blob().readall()
        else:
            file_path = Path(file_identifier)
            if file_path.is_absolute():
                return file_path.read_bytes()
            
            # Handle paths that already include storage/raw/ prefix
            if file_identifier.startswith("storage/raw/") or file_identifier.startswith("storage\\raw\\"):
                # Remove the prefix and use just the filename
                file_identifier = file_identifier.replace("storage/raw/", "").replace("storage\\raw\\", "")
            
            file_path = self.raw_path / file_identifier
            return file_path.read_bytes()
    
    def get_file_path(self, file_identifier: str) -> str:
        """Get full file path/URL"""
        if isinstance(file_identifier, str) and file_identifier.lower().startswith(("http://", "https://")):
            return file_identifier
        if self.use_azure:
            blob_client = self.container_client.get_blob_client(file_identifier)
            return blob_client.url
        else:
            file_path = Path(file_identifier)
            if file_path.is_absolute():
                return str(file_path)
            
            # Handle paths that already include storage/raw/ prefix
            if file_identifier.startswith("storage/raw/") or file_identifier.startswith("storage\\raw\\"):
                # Remove the prefix and use just the filename
                file_identifier = file_identifier.replace("storage/raw/", "").replace("storage\\raw\\", "")
            
            file_path = self.raw_path / file_identifier
            # Return a consistent posix-style path so tests behave the same across platforms
            return file_path.as_posix()

