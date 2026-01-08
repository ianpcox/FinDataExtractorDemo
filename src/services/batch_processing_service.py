"""Batch processing service for multiple invoices"""

import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.extraction.extraction_service import ExtractionService
from src.services.db_service import DatabaseService

logger = logging.getLogger(__name__)


class BatchProcessingService:
    """Service for batch processing multiple invoices"""
    
    def __init__(
        self,
        extraction_service: Optional[ExtractionService] = None,
        max_concurrent: int = 5
    ):
        """
        Initialize batch processing service
        
        Args:
            extraction_service: ExtractionService instance
            max_concurrent: Maximum number of concurrent extractions
        """
        self.extraction_service = extraction_service or ExtractionService()
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_batch(
        self,
        invoice_ids: List[str],
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Process a batch of invoices concurrently
        
        Args:
            invoice_ids: List of invoice IDs to process
            db: Optional database session
            
        Returns:
            {
                "total": int,
                "succeeded": int,
                "failed": int,
                "results": [{"invoice_id": str, "status": str, "result": dict}]
            }
        """
        logger.info(f"Starting batch processing for {len(invoice_ids)} invoices")
        start_time = datetime.utcnow()
        
        # Create tasks for all invoices
        tasks = [
            self._process_single(invoice_id, db)
            for invoice_id in invoice_ids
        ]
        
        # Execute with concurrency limit
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        succeeded = 0
        failed = 0
        processed_results = []
        
        for invoice_id, result in zip(invoice_ids, results):
            if isinstance(result, Exception):
                logger.error(f"Batch processing error for {invoice_id}: {result}")
                processed_results.append({
                    "invoice_id": invoice_id,
                    "status": "error",
                    "error": str(result)
                })
                failed += 1
            elif result.get("status") == "extracted":
                processed_results.append({
                    "invoice_id": invoice_id,
                    "status": "success",
                    "result": result
                })
                succeeded += 1
            else:
                processed_results.append({
                    "invoice_id": invoice_id,
                    "status": "failed",
                    "result": result
                })
                failed += 1
        
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        
        summary = {
            "total": len(invoice_ids),
            "succeeded": succeeded,
            "failed": failed,
            "elapsed_seconds": elapsed,
            "results": processed_results
        }
        
        logger.info(
            f"Batch processing complete: {succeeded}/{len(invoice_ids)} succeeded in {elapsed:.2f}s"
        )
        
        return summary
    
    async def _process_single(
        self,
        invoice_id: str,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """Process a single invoice with semaphore control"""
        async with self.semaphore:
            logger.info(f"Processing invoice {invoice_id} in batch")
            
            # Get invoice metadata from database
            invoice_db = await DatabaseService.get_invoice(invoice_id, db=db)
            if not invoice_db:
                return {
                    "invoice_id": invoice_id,
                    "status": "error",
                    "errors": ["Invoice not found in database"]
                }
            
            # Extract invoice
            result = await self.extraction_service.extract_invoice(
                invoice_id=invoice_id,
                file_identifier=invoice_db.file_path,
                file_name=invoice_db.file_name,
                upload_date=invoice_db.upload_date,
                db=db
            )
            
            return result
    
    async def process_pending_invoices(
        self,
        limit: Optional[int] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Process all invoices with status 'uploaded' or 'processing'
        
        Args:
            limit: Maximum number of invoices to process (None for all)
            db: Optional database session
            
        Returns:
            Batch processing summary
        """
        logger.info("Finding pending invoices for batch processing")
        
        # Get pending invoices
        pending = await DatabaseService.list_invoices(
            status_filter="uploaded",
            limit=limit,
            db=db
        )
        
        if not pending:
            logger.info("No pending invoices found")
            return {
                "total": 0,
                "succeeded": 0,
                "failed": 0,
                "results": []
            }
        
        invoice_ids = [inv["invoice_id"] for inv in pending]
        logger.info(f"Found {len(invoice_ids)} pending invoices")
        
        return await self.process_batch(invoice_ids, db=db)
    
    async def reprocess_failed_invoices(
        self,
        limit: Optional[int] = None,
        db: Optional[AsyncSession] = None
    ) -> Dict[str, Any]:
        """
        Reprocess invoices that previously failed extraction
        
        Args:
            limit: Maximum number of invoices to reprocess
            db: Optional database session
            
        Returns:
            Batch processing summary
        """
        logger.info("Finding failed invoices for reprocessing")
        
        # Get failed invoices
        failed = await DatabaseService.list_invoices(
            status_filter="error",
            limit=limit,
            db=db
        )
        
        if not failed:
            logger.info("No failed invoices found")
            return {
                "total": 0,
                "succeeded": 0,
                "failed": 0,
                "results": []
            }
        
        invoice_ids = [inv["invoice_id"] for inv in failed]
        logger.info(f"Found {len(invoice_ids)} failed invoices for reprocessing")
        
        return await self.process_batch(invoice_ids, db=db)
