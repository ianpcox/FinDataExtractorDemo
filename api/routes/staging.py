"""API routes for ERP staging"""

from fastapi import APIRouter, HTTPException, Depends, Query, Body
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, List
import logging

from src.erp.staging_service import ERPStagingService, ERPPayloadFormat
from src.services.db_service import DatabaseService
from src.models.database import get_db
from src.ingestion.file_handler import FileHandler
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/staging", tags=["staging"])


class StageInvoiceRequest(BaseModel):
    """Request model for staging an invoice"""
    invoice_id: str
    generate_overlay: bool = False
    require_approval: bool = True
    format: Optional[str] = "dynamics_gp"  # json, csv, xml, dynamics_gp


class BatchStageRequest(BaseModel):
    """Request model for batch staging"""
    invoice_ids: Optional[List[str]] = None
    limit: int = 100
    require_approval: bool = True
    format: Optional[str] = "dynamics_gp"


@router.post("/stage")
async def stage_invoice(
    request: StageInvoiceRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Stage an invoice for ERP export
    
    Args:
        request: StageInvoiceRequest with invoice_id and options
        
    Returns:
        Staging result with payload location
    """
    try:
        # Verify invoice exists
        invoice = await DatabaseService.get_invoice(request.invoice_id, db=db)
        if not invoice:
            raise HTTPException(
                status_code=404,
                detail=f"Invoice {request.invoice_id} not found"
            )
        
        # Determine format
        try:
            erp_format = ERPPayloadFormat(request.format.lower()) if request.format else ERPPayloadFormat.DYNAMICS_GP
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid format: {request.format}. Must be one of: json, csv, xml, dynamics_gp"
            )
        
        # Create staging service
        staging_service = ERPStagingService(
            erp_format=erp_format,
            file_handler=FileHandler()
        )
        
        # Stage invoice
        result = await staging_service.stage_invoice(
            invoice_id=request.invoice_id,
            generate_overlay=request.generate_overlay,
            require_approval=request.require_approval
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("message", "Staging failed")
            )
        
        return {
            "success": True,
            "invoice_id": result["invoice_id"],
            "payload_location": result["payload_location"],
            "overlay_location": result.get("overlay_location"),
            "format": result["format"],
            "export_timestamp": result["export_timestamp"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error staging invoice: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/batch-stage")
async def batch_stage_invoices(
    request: BatchStageRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Batch stage multiple invoices for ERP export
    
    Args:
        request: BatchStageRequest with invoice_ids and options
        
    Returns:
        Batch staging results
    """
    try:
        # Determine format
        try:
            erp_format = ERPPayloadFormat(request.format.lower()) if request.format else ERPPayloadFormat.DYNAMICS_GP
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid format: {request.format}. Must be one of: json, csv, xml, dynamics_gp"
            )
        
        # Create staging service
        staging_service = ERPStagingService(
            erp_format=erp_format,
            file_handler=FileHandler()
        )
        
        # Batch stage
        result = await staging_service.batch_stage(
            invoice_ids=request.invoice_ids,
            limit=request.limit,
            require_approval=request.require_approval
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error batch staging invoices: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/invoice/{invoice_id}/payload")
async def get_staged_payload(
    invoice_id: str,
    format: Optional[str] = Query("dynamics_gp", description="Format: json, csv, xml, dynamics_gp"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get staged payload for an invoice (for direct ERP integration)
    
    Args:
        invoice_id: Invoice ID
        format: Optional format override
        
    Returns:
        Payload in requested format
    """
    try:
        # Verify invoice exists
        invoice = await DatabaseService.get_invoice(invoice_id, db=db)
        if not invoice:
            raise HTTPException(
                status_code=404,
                detail=f"Invoice {invoice_id} not found"
            )
        
        # Determine format
        try:
            erp_format = ERPPayloadFormat(format.lower()) if format else ERPPayloadFormat.DYNAMICS_GP
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid format: {format}"
            )
        
        # Get payload
        staging_service = ERPStagingService(erp_format=erp_format)
        payload = await staging_service.get_payload(invoice_id, format=erp_format)
        
        if not payload:
            raise HTTPException(
                status_code=404,
                detail=f"Payload not found for invoice {invoice_id}"
            )
        
        # Determine content type
        content_type_map = {
            "json": "application/json",
            "csv": "text/csv",
            "xml": "application/xml",
            "dynamics_gp": "application/xml"
        }
        content_type = content_type_map.get(erp_format.value, "text/plain")
        
        return Response(
            content=payload,
            media_type=content_type,
            headers={
                "Content-Disposition": f'inline; filename="invoice_{invoice_id}_payload.{erp_format.value}"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting staged payload: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/invoice/{invoice_id}/preview")
async def preview_staged_payload(
    invoice_id: str,
    format: Optional[str] = Query("json", description="Format: json, csv, xml, dynamics_gp"),
    db: AsyncSession = Depends(get_db)
):
    """
    Preview staged payload for an invoice (for human review before export)
    
    Args:
        invoice_id: Invoice ID
        format: Format for preview (default: json)
        
    Returns:
        Payload preview in requested format
    """
    try:
        # Verify invoice exists
        invoice = await DatabaseService.get_invoice(invoice_id, db=db)
        if not invoice:
            raise HTTPException(
                status_code=404,
                detail=f"Invoice {invoice_id} not found"
            )
        
        # Determine format
        try:
            erp_format = ERPPayloadFormat(format.lower()) if format else ERPPayloadFormat.JSON
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid format: {format}"
            )
        
        # Generate preview payload
        from src.erp.staging_service import ERPPayloadGenerator
        generator = ERPPayloadGenerator(erp_format=erp_format)
        payload_result = generator.generate_payload(invoice)
        
        return {
            "invoice_id": invoice_id,
            "format": erp_format.value,
            "payload": payload_result["payload"],
            "preview": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error previewing staged payload: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

