"""Simplified ingestion service with database integration"""

from typing import Dict, Any, Optional
from datetime import datetime
from uuid import uuid4
import logging
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from .file_handler import FileHandler
from .pdf_processor import PDFProcessor
from .pdf_preprocessor import PDFPreprocessor
from src.models.invoice import Invoice
from src.services.db_service import DatabaseService
from src.services.progress_tracker import progress_tracker, ProcessingStep
from src.config import settings

logger = logging.getLogger(__name__)


class IngestionService:
    """Service for ingesting invoice PDFs"""
    
    def __init__(
        self,
        file_handler: Optional[FileHandler] = None,
        pdf_processor: Optional[PDFProcessor] = None,
        pdf_preprocessor: Optional[PDFPreprocessor] = None
    ):
        """
        Initialize ingestion service
        
        Args:
            file_handler: FileHandler instance
            pdf_processor: PDFProcessor instance
            pdf_preprocessor: PDFPreprocessor instance (optional, for PDF optimization)
        """
        self.file_handler = file_handler or FileHandler()
        self.pdf_processor = pdf_processor or PDFProcessor()
        self.pdf_preprocessor = pdf_preprocessor or PDFPreprocessor()
    
    async def ingest_invoice(
        self,
        file_content: bytes,
        file_name: str,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        Ingest an invoice PDF
        
        Args:
            file_content: PDF file content as bytes
            file_name: Original file name
            db: Optional async DB session (uses default if not provided)
            
        Returns:
            Dictionary with ingestion result
        """
        errors = []
        
        # Generate invoice ID early for progress tracking
        invoice_id = str(uuid4())
        
        try:
            # Start progress tracking
            await progress_tracker.start(invoice_id, ProcessingStep.PREPROCESSING, "Validating PDF file...")
            await progress_tracker.update(invoice_id, 5, "Validating PDF file...")
            
            # Step 1: Validate PDF
            is_valid, error_message = self.pdf_processor.validate_file(
                file_content,
                file_name
            )
            
            if not is_valid:
                errors.append(error_message)
                await progress_tracker.error(invoice_id, error_message, ProcessingStep.PREPROCESSING)
                return {
                    "status": "validation_failed",
                    "errors": errors
                }
            
            await progress_tracker.update(invoice_id, 10, "PDF validated, starting preprocessing...")
            
            # Step 2: Preprocess PDF (optional - optimizes for extraction)
            # Run with timeout (30 second SLO)
            preprocessing_timeout = getattr(settings, "PDF_PREPROCESS_TIMEOUT_SEC", 30.0)
            try:
                await progress_tracker.update(invoice_id, 15, "Preprocessing PDF...")
                processed_content, preprocessing_stats = await asyncio.wait_for(
                    run_in_threadpool(
                        self.pdf_preprocessor.preprocess,
                        file_content,
                        file_name
                    ),
                    timeout=preprocessing_timeout
                )
                await progress_tracker.update(invoice_id, 25, "Preprocessing complete")
                await progress_tracker.complete_step(invoice_id, ProcessingStep.PREPROCESSING, "Preprocessing complete")
            except asyncio.TimeoutError:
                # Preprocessing exceeded SLO - use original file and notify user
                logger.warning(
                    f"PDF preprocessing exceeded {preprocessing_timeout}s SLO for {file_name}, "
                    "using original file"
                )
                processed_content = file_content
                preprocessing_stats = {
                    "original_size": len(file_content),
                    "processed_size": len(file_content),
                    "size_reduction": 0.0,
                    "preprocessing_applied": [],
                    "timeout": True,
                    "timeout_seconds": preprocessing_timeout,
                    "message": (
                        "Due to the size of the file and the processing work required, "
                        "preprocessing is taking longer than usual. The original file will be used."
                    )
                }
                await progress_tracker.update(invoice_id, 25, preprocessing_stats["message"])
                await progress_tracker.complete_step(invoice_id, ProcessingStep.PREPROCESSING, preprocessing_stats["message"])
            
            # Step 3: Start ingestion step
            await progress_tracker.start(invoice_id, ProcessingStep.INGESTION, "Processing PDF info...")
            await progress_tracker.update(invoice_id, 30, "Processing PDF info...")
            
            # Get PDF info (use processed content if preprocessing was applied)
            pdf_info = self.pdf_processor.get_pdf_info(processed_content)
            
            await progress_tracker.update(invoice_id, 35, "Uploading file...")
            
            # Step 4: Upload file (use processed content)
            upload_result = self.file_handler.upload_file(
                file_content=processed_content,
                file_name=file_name
            )
            
            upload_date = upload_result["upload_date"]
            await progress_tracker.update(invoice_id, 40, "File uploaded, saving to database...")
            
            # Step 5: Create initial invoice record in database
            file_path = upload_result.get("file_path") or upload_result.get("blob_name") or upload_result.get("stored_name")
            
            invoice = Invoice(
                id=invoice_id,
                file_path=file_path,
                file_name=file_name,
                upload_date=upload_date,
                status="processing"
            )
            
            # Save to database
            await DatabaseService.save_invoice(invoice, db=db)
            await progress_tracker.update(invoice_id, 50, "Ingestion complete")
            await progress_tracker.complete_step(invoice_id, ProcessingStep.INGESTION, "Invoice ingested successfully")
            
            result = {
                "invoice_id": invoice_id,
                "status": "uploaded",
                "file_name": file_name,
                "file_path": file_path,
                "file_size": upload_result["size"],
                "page_count": pdf_info.get("page_count", 0),
                "upload_date": upload_date,
                "preprocessing": preprocessing_stats if (preprocessing_stats.get("preprocessing_applied") or preprocessing_stats.get("timeout")) else None,
                "errors": []
            }
            
            logger.info(f"Invoice ingested successfully: {invoice_id}")
            # Don't mark as complete yet - extraction will continue
            return result
            
        except Exception as e:
            logger.error(f"Error ingesting invoice: {e}", exc_info=True)
            errors.append(str(e))
            await progress_tracker.error(invoice_id, str(e), ProcessingStep.INGESTION)
            return {
                "status": "error",
                "errors": errors
            }

