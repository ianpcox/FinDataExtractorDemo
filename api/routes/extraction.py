"""Simplified API routes for invoice data extraction"""

from fastapi import APIRouter, HTTPException, Depends, Path
from fastapi.responses import JSONResponse
import logging

from src.extraction.extraction_service import ExtractionService
from src.extraction.document_intelligence_client import DocumentIntelligenceClient
from src.ingestion.file_handler import FileHandler

logger = logging.getLogger(__name__)

router = APIRouter()


def get_extraction_service() -> ExtractionService:
    """Dependency to get extraction service instance"""
    doc_client = DocumentIntelligenceClient()
    file_handler = FileHandler()
    return ExtractionService(
        doc_intelligence_client=doc_client,
        file_handler=file_handler
    )


@router.post("/extraction/extract/{invoice_id}")
async def extract_invoice(
    invoice_id: str = Path(..., description="Invoice ID to extract"),
    file_identifier: str = None,
    file_name: str = None,
    extraction_service: ExtractionService = Depends(get_extraction_service)
):
    """
    Trigger extraction for an invoice
    
    Args:
        invoice_id: Invoice ID
        file_identifier: File path (local) or blob name (Azure)
        file_name: Original file name
        
    Returns:
        Extraction result
    """
    try:
        if not file_identifier:
            raise HTTPException(
                status_code=400,
                detail="file_identifier is required"
            )
        
        if not file_name:
            file_name = "invoice.pdf"
        
        from datetime import datetime
        result = await extraction_service.extract_invoice(
            invoice_id=invoice_id,
            file_identifier=file_identifier,
            file_name=file_name,
            upload_date=datetime.utcnow()
        )
        
        if result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "Extraction error",
                    "errors": result.get("errors", [])
                }
            )
        
        if result["status"] == "extraction_failed":
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Extraction failed",
                    "errors": result.get("errors", [])
                }
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Extraction completed successfully",
                "invoice_id": result["invoice_id"],
                "status": result["status"],
                "invoice": result["invoice"],
                "confidence": result["confidence"],
                "extraction_timestamp": result["extraction_timestamp"].isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extracting invoice: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/extraction/{invoice_id}")
async def get_extraction_result(
    invoice_id: str = Path(..., description="Invoice ID"),
    extraction_service: ExtractionService = Depends(get_extraction_service)
):
    """
    Get extraction result for an invoice
    
    Args:
        invoice_id: Invoice ID
        
    Returns:
        Extraction result (placeholder - would query database in full implementation)
    """
    # TODO: Query database for extraction result
    raise HTTPException(
        status_code=501,
        detail="Not implemented - would query database for extraction result"
    )

