"""Simplified API routes for document matching"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/matching/match")
async def match_invoice_to_po(
    invoice_id: str,
    po_number: str = None
):
    """
    Match invoice to purchase order (simplified placeholder)
    
    Args:
        invoice_id: Invoice ID
        po_number: Optional PO number to match against
        
    Returns:
        Matching result
    """
    # TODO: Implement simplified matching logic
    return JSONResponse(
        status_code=200,
        content={
            "message": "Matching functionality - to be implemented",
            "invoice_id": invoice_id,
            "po_number": po_number,
            "matched": False,
            "confidence": 0.0
        }
    )

