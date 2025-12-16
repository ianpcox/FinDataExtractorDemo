"""API routes for PDF overlay rendering"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from typing import Optional
import logging

from src.services.db_service import DatabaseService
from src.erp.pdf_overlay_renderer import PDFOverlayRenderer
from src.ingestion.file_handler import FileHandler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/overlay", tags=["overlay"])


@router.get("/{invoice_id}")
async def get_overlay_pdf(
    invoice_id: str,
    file_handler: FileHandler = Depends(lambda: FileHandler())
):
    """
    Generate PDF overlay for an invoice
    
    Args:
        invoice_id: Invoice ID
        
    Returns:
        PDF file with overlay
    """
    try:
        # Get invoice from database
        invoice = await DatabaseService.get_invoice(invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
        
        # Create overlay renderer
        renderer = PDFOverlayRenderer(file_handler=file_handler)
        
        # Generate overlay PDF
        overlay_pdf = renderer.render_overlay(invoice)
        
        # Return PDF response
        return Response(
            content=overlay_pdf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="invoice_{invoice_id}_overlay.pdf"'
            }
        )
        
    except ImportError as e:
        logger.error(f"PDF overlay dependencies not available: {e}")
        raise HTTPException(
            status_code=503,
            detail="PDF overlay rendering is not available. Please install reportlab and PyPDF2."
        )
    except Exception as e:
        logger.error(f"Error generating overlay PDF for invoice {invoice_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

