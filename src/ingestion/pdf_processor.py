"""Simplified PDF validation and processing"""

import os
from typing import Tuple, Optional
from io import BytesIO
import PyPDF2
import logging

from src.config import settings

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Handles PDF validation and basic processing"""
    
    def __init__(self, max_file_size_mb: Optional[int] = None):
        """
        Initialize PDF processor
        
        Args:
            max_file_size_mb: Maximum file size in MB (defaults to settings)
        """
        self.max_file_size_mb = max_file_size_mb or settings.MAX_FILE_SIZE_MB
        self.max_file_size_bytes = self.max_file_size_mb * 1024 * 1024
    
    def validate_file(
        self,
        file_content: bytes,
        file_name: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate PDF file
        
        Args:
            file_content: File content as bytes
            file_name: Original file name
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file extension
        if not file_name.lower().endswith('.pdf'):
            return False, "File must be a PDF (.pdf extension required)"
        
        # Check file size
        file_size = len(file_content)
        if file_size == 0:
            return False, "File is empty"
        
        if file_size > self.max_file_size_bytes:
            return False, (
                f"File size ({file_size / 1024 / 1024:.2f} MB) exceeds "
                f"maximum allowed size ({self.max_file_size_mb} MB)"
            )
        
        # Validate PDF structure
        try:
            pdf_file = BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            if pdf_reader.is_encrypted:
                return False, "PDF is encrypted and cannot be processed"
            
            if len(pdf_reader.pages) == 0:
                return False, "PDF has no pages"
            
            # Try to access first page
            first_page = pdf_reader.pages[0]
            _ = first_page.extract_text()
            
            logger.info(
                f"PDF validation successful: {file_name} "
                f"({file_size} bytes, {len(pdf_reader.pages)} pages)"
            )
            
            return True, None
            
        except PyPDF2.errors.PdfReadError as e:
            return False, f"Invalid PDF format: {str(e)}"
        except Exception as e:
            return False, f"Error validating PDF: {str(e)}"
    
    def get_pdf_info(self, file_content: bytes) -> dict:
        """
        Extract basic information from PDF
        
        Args:
            file_content: File content as bytes
            
        Returns:
            Dictionary with PDF information
        """
        try:
            pdf_file = BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            return {
                "page_count": len(pdf_reader.pages),
                "is_encrypted": pdf_reader.is_encrypted,
                "metadata": pdf_reader.metadata or {}
            }
        except Exception as e:
            logger.error(f"Error getting PDF info: {e}")
            return {"error": str(e)}

