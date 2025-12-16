"""Simplified ingestion service with database integration"""

from typing import Dict, Any, Optional
from datetime import datetime
from uuid import uuid4
import logging

from .file_handler import FileHandler
from .pdf_processor import PDFProcessor
from src.models.invoice import Invoice
from src.services.db_service import DatabaseService

logger = logging.getLogger(__name__)


class IngestionService:
    """Service for ingesting invoice PDFs"""
    
    def __init__(
        self,
        file_handler: Optional[FileHandler] = None,
        pdf_processor: Optional[PDFProcessor] = None
    ):
        """
        Initialize ingestion service
        
        Args:
            file_handler: FileHandler instance
            pdf_processor: PDFProcessor instance
        """
        self.file_handler = file_handler or FileHandler()
        self.pdf_processor = pdf_processor or PDFProcessor()
    
    async def ingest_invoice(
        self,
        file_content: bytes,
        file_name: str
    ) -> Dict[str, Any]:
        """
        Ingest an invoice PDF
        
        Args:
            file_content: PDF file content as bytes
            file_name: Original file name
            
        Returns:
            Dictionary with ingestion result
        """
        errors = []
        
        try:
            # Step 1: Validate PDF
            is_valid, error_message = self.pdf_processor.validate_file(
                file_content,
                file_name
            )
            
            if not is_valid:
                errors.append(error_message)
                return {
                    "status": "validation_failed",
                    "errors": errors
                }
            
            # Step 2: Get PDF info
            pdf_info = self.pdf_processor.get_pdf_info(file_content)
            
            # Step 3: Upload file
            upload_result = self.file_handler.upload_file(
                file_content=file_content,
                file_name=file_name
            )
            
            # Generate invoice ID
            invoice_id = str(uuid4())
            upload_date = upload_result["upload_date"]
            
            # Step 4: Create initial invoice record in database
            file_path = upload_result.get("file_path") or upload_result.get("blob_name") or upload_result.get("stored_name")
            
            invoice = Invoice(
                id=invoice_id,
                file_path=file_path,
                file_name=file_name,
                upload_date=upload_date,
                status="processing"
            )
            
            # Save to database
            # Note: DatabaseService.save_invoice will get its own session if db is None
            await DatabaseService.save_invoice(invoice)
            
            result = {
                "invoice_id": invoice_id,
                "status": "uploaded",
                "file_name": file_name,
                "file_path": file_path,
                "file_size": upload_result["size"],
                "page_count": pdf_info.get("page_count", 0),
                "upload_date": upload_date,
                "errors": []
            }
            
            logger.info(f"Invoice ingested successfully: {invoice_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error ingesting invoice: {e}", exc_info=True)
            errors.append(str(e))
            return {
                "status": "error",
                "errors": errors
            }

