"""Simplified API routes for invoice data extraction"""

from fastapi import APIRouter, HTTPException, Depends, Path, Query
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
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
    file_identifier: str = Query(None, description="File path (local) or blob name (Azure)"),
    file_name: str = Query(None, description="Original file name"),
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

        if result["status"] == "upstream_error":
            raise HTTPException(
                status_code=503,
                detail={
                    "message": "Upstream service unavailable",
                    "errors": result.get("errors", [])
                }
            )

        if result["status"] == "conflict":
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Invoice is already processing",
                    "errors": result.get("errors", [])
                }
            )
        
        # Ensure all fields are JSON serializable
        invoice_payload = jsonable_encoder(result.get("invoice"))
        extraction_ts = result.get("extraction_timestamp")
        if extraction_ts and not isinstance(extraction_ts, str):
            extraction_ts = extraction_ts.isoformat()

        content = {
            "message": "Extraction completed successfully",
            "invoice_id": result.get("invoice_id"),
            "status": result.get("status"),
            "invoice": invoice_payload,
            "confidence": result.get("confidence"),
            "field_confidence": result.get("field_confidence"),
            "low_confidence_fields": result.get("low_confidence_fields", []),
            "low_confidence_triggered": result.get("low_confidence_triggered", False),
            "extraction_timestamp": extraction_ts
        }

        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(content)
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


@router.post("/extraction/ai-extract/{invoice_id}")
async def run_ai_extraction(
    invoice_id: str = Path(..., description="Invoice ID to improve"),
    confidence_threshold: float = 0.7,
    extraction_service: ExtractionService = Depends(get_extraction_service)
):
    """
    Manually trigger AI extraction to improve low-confidence fields
    
    This endpoint runs LLM-based extraction on fields that scored below
    the confidence threshold during the initial Document Intelligence extraction.
    
    Args:
        invoice_id: Invoice ID to improve
        confidence_threshold: Minimum confidence threshold (0.0-1.0)
        
    Returns:
        AI extraction result with improved fields
    """
    try:
        if not 0.0 <= confidence_threshold <= 1.0:
            raise HTTPException(
                status_code=400,
                detail="confidence_threshold must be between 0.0 and 1.0"
            )
        
        result = await extraction_service.run_ai_extraction(
            invoice_id=invoice_id,
            confidence_threshold=confidence_threshold
        )
        
        if result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "AI extraction error",
                    "errors": result.get("errors", [])
                }
            )
        
        return JSONResponse(
            status_code=200,
            content=jsonable_encoder(result)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in AI extraction: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
