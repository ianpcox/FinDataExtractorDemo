"""Azure Blob Storage utilities for browsing and downloading files"""

from typing import List, Optional, Dict, Any
from azure.storage.blob import BlobServiceClient, ContainerClient
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import AzureError
import logging

from src.config import settings

logger = logging.getLogger(__name__)


class AzureBlobBrowser:
    """Utility class for browsing Azure Blob Storage"""
    
    def __init__(self):
        """Initialize Azure Blob Storage client"""
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
    
    def list_blobs(
        self,
        container_name: str,
        prefix: Optional[str] = None,
        name_starts_with: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List blobs in a container, optionally filtered by prefix/path
        
        Args:
            container_name: Name of the container
            prefix: Path prefix to filter (e.g., "RAW Basic/" or "Raw_Basic/")
            name_starts_with: Alternative to prefix (for compatibility)
            
        Returns:
            List of blob information dictionaries
        """
        try:
            container_client = self.blob_service_client.get_container_client(container_name)
            
            # Use prefix if provided, otherwise name_starts_with
            filter_prefix = prefix or name_starts_with
            
            blobs = []
            for blob in container_client.list_blobs(name_starts_with=filter_prefix):
                blobs.append({
                    "name": blob.name,
                    "size": blob.size,
                    "content_type": blob.content_settings.content_type if blob.content_settings else None,
                    "last_modified": blob.last_modified.isoformat() if blob.last_modified else None,
                    "metadata": blob.metadata or {}
                })
            
            logger.info(f"Found {len(blobs)} blobs in container '{container_name}' with prefix '{filter_prefix}'")
            return blobs
            
        except AzureError as e:
            logger.error(f"Error listing blobs: {e}")
            raise
    
    def download_blob(
        self,
        container_name: str,
        blob_name: str
    ) -> bytes:
        """
        Download a blob from Azure Storage
        
        Args:
            container_name: Name of the container
            blob_name: Name/path of the blob
            
        Returns:
            Blob content as bytes
        """
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            return blob_client.download_blob().readall()
            
        except AzureError as e:
            logger.error(f"Error downloading blob '{blob_name}': {e}")
            raise
    
    def list_containers(self) -> List[str]:
        """List all containers in the storage account"""
        try:
            containers = []
            for container in self.blob_service_client.list_containers():
                containers.append(container.name)
            return containers
        except AzureError as e:
            logger.error(f"Error listing containers: {e}")
            raise
    
    def get_blob_info(
        self,
        container_name: str,
        blob_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get information about a specific blob"""
        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            properties = blob_client.get_blob_properties()
            
            return {
                "name": blob_name,
                "size": properties.size,
                "content_type": properties.content_settings.content_type if properties.content_settings else None,
                "last_modified": properties.last_modified.isoformat() if properties.last_modified else None,
                "metadata": properties.metadata or {},
                "url": blob_client.url
            }
        except AzureError as e:
            logger.error(f"Error getting blob info: {e}")
            return None

