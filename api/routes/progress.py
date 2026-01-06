"""API routes for progress tracking"""

from fastapi import APIRouter, HTTPException, Path
from fastapi.responses import JSONResponse
from typing import Optional
import logging

from src.services.progress_tracker import progress_tracker

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/progress/{invoice_id}")
async def get_progress(invoice_id: str = Path(..., description="Invoice ID to get progress for")):
    """
    Get processing progress for an invoice
    
    Args:
        invoice_id: Invoice ID
        
    Returns:
        Progress information including:
        - current_step: Current processing step
        - progress_percentage: Progress percentage (0-100)
        - status: running, complete, or error
        - message: Current status message
        - steps: Individual step progress
    """
    try:
        progress = await progress_tracker.get(invoice_id)
        
        if not progress:
            raise HTTPException(
                status_code=404,
                detail=f"Progress not found for invoice_id: {invoice_id}"
            )
        
        return JSONResponse(
            status_code=200,
            content=progress
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting progress for invoice {invoice_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

