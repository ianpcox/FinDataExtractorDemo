"""Batch processing API routes"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel

from src.models.database import get_db
from src.services.batch_processing_service import BatchProcessingService

router = APIRouter(prefix="/api/batch", tags=["batch"])


class BatchProcessRequest(BaseModel):
    """Request to process a batch of invoices"""
    invoice_ids: List[str]


class BatchProcessPendingRequest(BaseModel):
    """Request to process pending invoices"""
    limit: Optional[int] = None


@router.post("/process")
async def process_batch(
    request: BatchProcessRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Process a batch of invoices by ID
    
    Returns summary of batch processing results
    """
    if not request.invoice_ids:
        raise HTTPException(status_code=400, detail="invoice_ids list cannot be empty")
    
    if len(request.invoice_ids) > 100:
        raise HTTPException(
            status_code=400,
            detail="Maximum 100 invoices per batch request"
        )
    
    batch_service = BatchProcessingService()
    result = await batch_service.process_batch(request.invoice_ids, db=db)
    
    return result


@router.post("/process-pending")
async def process_pending(
    request: BatchProcessPendingRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Process all pending invoices (status='uploaded')
    
    Optionally limit the number of invoices to process
    """
    batch_service = BatchProcessingService()
    result = await batch_service.process_pending_invoices(
        limit=request.limit,
        db=db
    )
    
    return result


@router.post("/reprocess-failed")
async def reprocess_failed(
    request: BatchProcessPendingRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Reprocess all failed invoices (status='error')
    
    Optionally limit the number of invoices to reprocess
    """
    batch_service = BatchProcessingService()
    result = await batch_service.reprocess_failed_invoices(
        limit=request.limit,
        db=db
    )
    
    return result
