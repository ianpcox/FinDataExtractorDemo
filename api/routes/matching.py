"""Simplified API routes for document matching"""

from fastapi import APIRouter, HTTPException, Depends, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

from src.matching.matching_service import MatchingService
from src.services.db_service import DatabaseService
from src.models.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter()


class MatchInvoicePORequest(BaseModel):
    """Request model for invoice to PO matching"""
    invoice_id: str
    po_number: Optional[str] = None
    po_data: Optional[Dict[str, Any]] = None  # PO data from separate storage


class MatchResponse(BaseModel):
    """Response model for matching operations"""
    success: bool
    invoice_id: str
    matches: List[Dict[str, Any]]
    message: Optional[str] = None


@router.post("/matching/match", response_model=MatchResponse)
async def match_invoice_to_po(
    request: MatchInvoicePORequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Match invoice to purchase order
    
    Args:
        request: MatchInvoicePORequest with invoice_id and optional po_number/po_data
        
    Returns:
        MatchResponse with matching results
    """
    try:
        # Verify invoice exists
        invoice = await DatabaseService.get_invoice(request.invoice_id, db=db)
        if not invoice:
            raise HTTPException(
                status_code=404,
                detail=f"Invoice {request.invoice_id} not found"
            )
        
        # Create matching service
        matching_service = MatchingService(db=db)
        
        # Perform matching
        matches = await matching_service.match_invoice_to_po(
            invoice_id=request.invoice_id,
            po_number=request.po_number,
            po_data=request.po_data
        )
        
        # Convert matches to dict format
        matches_data = [
            {
                "source_document_id": m.source_document_id,
                "source_document_type": m.source_document_type,
                "matched_document_id": m.matched_document_id,
                "matched_document_type": m.matched_document_type,
                "matched_document_number": m.matched_document_number,
                "confidence": m.confidence,
                "match_strategy": m.match_strategy.value,
                "match_details": m.match_details,
                "created_at": m.created_at.isoformat()
            }
            for m in matches
        ]
        
        return MatchResponse(
            success=True,
            invoice_id=request.invoice_id,
            matches=matches_data,
            message=f"Found {len(matches)} match(es)" if matches else "No matches found"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error matching invoice to PO: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/matching/{invoice_id}")
async def get_invoice_matches(
    invoice_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all matches for an invoice
    
    Args:
        invoice_id: Invoice ID
        
    Returns:
        List of matches (placeholder - would query DocumentMatch table)
    """
    # TODO: Query DocumentMatch table when implemented
    return JSONResponse(
        status_code=200,
        content={
            "message": "Match retrieval - to be implemented",
            "invoice_id": invoice_id,
            "matches": []
        }
    )

