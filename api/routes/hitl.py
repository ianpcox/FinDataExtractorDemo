"""HITL (Human-in-the-Loop) API routes for invoice validation"""

from fastapi import APIRouter, HTTPException, Depends, Body
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
import logging
import json
from pathlib import Path

from src.services.db_service import DatabaseService
from src.models.database import get_db
from src.models.invoice import Invoice, LineItem, Address
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/hitl", tags=["hitl"])


class FieldValidation(BaseModel):
    """Validation for a single field"""
    field_name: str
    value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    validated: bool = False
    corrected_value: Optional[Any] = None
    validation_notes: Optional[str] = None


class LineItemValidation(BaseModel):
    """Validation for a line item"""
    line_number: int
    validated: bool = False
    corrections: Optional[Dict[str, Any]] = None
    validation_notes: Optional[str] = None


class InvoiceValidationRequest(BaseModel):
    """Request to validate an invoice"""
    invoice_id: str
    field_validations: Optional[List[FieldValidation]] = None
    line_item_validations: Optional[List[LineItemValidation]] = None
    overall_validation_status: str = Field(default="pending")  # pending, validated, needs_review
    validation_notes: Optional[str] = None
    reviewer: Optional[str] = None


class InvoiceValidationResponse(BaseModel):
    """Response for invoice validation"""
    success: bool
    invoice_id: str
    validation_status: str
    message: str


@router.get("/invoice/{invoice_id}")
async def get_invoice_for_validation(
    invoice_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get invoice with field-level confidence for HITL validation
    
    Returns invoice data with confidence scores per field for human review.
    
    Args:
        invoice_id: Invoice ID
        
    Returns:
        Invoice data with confidence scores and validation status
    """
    try:
        # helper to safely convert numeric values
        def to_number(val, default=None):
            try:
                if val is None:
                    return default
                if isinstance(val, (int, float)):
                    return float(val)
                return float(str(val).replace(",", ""))
            except Exception:
                return default
        
        def to_date_str(val):
            try:
                return val.isoformat() if val else None
            except Exception:
                return None
        
        def to_str(val, default=None):
            return val if val is not None else default
        
        # Get invoice from database
        invoice = await DatabaseService.get_invoice(invoice_id, db=db)
        if not invoice:
            raise HTTPException(
                status_code=404,
                detail=f"Invoice {invoice_id} not found"
            )
        
        def get_conf(key: str, default: float = 0.0):
            if invoice.field_confidence:
                # exact match
                if key in invoice.field_confidence:
                    try:
                        return float(invoice.field_confidence.get(key) or 0.0)
                    except Exception:
                        return default
                # address fallback bill_to -> customer_address
                if key == "bill_to_address" and "customer_address" in invoice.field_confidence:
                    try:
                        return float(invoice.field_confidence.get("customer_address") or 0.0)
                    except Exception:
                        return default
            return default

        # Build response with field-level confidence
        # derive low confidence fields for UI hints
        low_conf_threshold = 0.75
        low_conf_fields = []
        if invoice.field_confidence:
            low_conf_fields = [
                name for name, conf in invoice.field_confidence.items()
                if conf is not None and conf < low_conf_threshold
            ]

        response = {
            "invoice_id": invoice.id,
            "status": to_str(invoice.status, "processing"),
            "file_name": to_str(invoice.file_name, "Not extracted"),
            "file_path": to_str(invoice.file_path, None),
            "upload_date": to_date_str(invoice.upload_date),
            "extraction_confidence": to_number(invoice.extraction_confidence, 0.0),
            "extraction_timestamp": to_date_str(invoice.extraction_timestamp),
            "low_confidence_fields": low_conf_fields,
            "low_confidence_triggered": bool(low_conf_fields),
            "review_status": to_str(invoice.review_status, "pending_review"),
            "reviewer": to_str(invoice.reviewer, None),
            "review_timestamp": to_date_str(invoice.review_timestamp),
            "fields": {
                "invoice_number": {
                    "value": to_str(invoice.invoice_number, "Not extracted"),
                    "confidence": get_conf("invoice_number"),
                    "validated": False
                },
                "invoice_date": {
                    "value": to_date_str(invoice.invoice_date),
                    "confidence": get_conf("invoice_date"),
                    "validated": False
                },
                "due_date": {
                    "value": to_date_str(invoice.due_date),
                    "confidence": get_conf("due_date"),
                    "validated": False
                },
                "vendor_name": {
                    "value": to_str(invoice.vendor_name, "Not extracted"),
                    "confidence": get_conf("vendor_name"),
                    "validated": False
                },
                "vendor_id": {
                    "value": to_str(invoice.vendor_id, None),
                    "confidence": get_conf("vendor_id"),
                    "validated": False
                },
                "vendor_phone": {
                    "value": to_str(getattr(invoice, "vendor_phone", None), None),
                    "confidence": get_conf("vendor_phone"),
                    "validated": False
                },
                "customer_name": {
                    "value": to_str(invoice.customer_name, "Not extracted"),
                    "confidence": get_conf("customer_name"),
                    "validated": False
                },
                "customer_id": {
                    "value": to_str(invoice.customer_id, None),
                    "confidence": get_conf("customer_id"),
                    "validated": False
                },
                "remit_to_name": {
                    "value": to_str(getattr(invoice, "remit_to_name", None), None),
                    "confidence": get_conf("remit_to_name"),
                    "validated": False
                },
                "po_number": {
                    "value": to_str(invoice.po_number, None),
                    "confidence": get_conf("purchase_order"),
                    "validated": False
                },
                "contract_id": {
                    "value": to_str(invoice.contract_id, None),
                    "confidence": get_conf("contract_id"),
                    "validated": False
                },
                "standing_offer_number": {
                    "value": to_str(getattr(invoice, "standing_offer_number", None), None),
                    "confidence": get_conf("standing_offer_number"),
                    "validated": False
                },
                "subtotal": {
                    "value": to_number(invoice.subtotal),
                    "confidence": get_conf("subtotal"),
                    "validated": False
                },
                "tax_amount": {
                    "value": to_number(invoice.tax_amount),
                    "confidence": get_conf("total_tax"),
                    "validated": False
                },
                "total_amount": {
                    "value": to_number(invoice.total_amount),
                    "confidence": get_conf("invoice_total"),
                    "validated": False
                },
                "currency": {
                    "value": to_str(invoice.currency, "Not extracted"),
                    "confidence": 1.0,  # Currency is usually high confidence
                    "validated": False
                },
                "payment_terms": {
                    "value": to_str(invoice.payment_terms, None),
                    "confidence": get_conf("payment_term"),
                    "validated": False
                },
                "acceptance_percentage": {
                    "value": to_number(getattr(invoice, "acceptance_percentage", None)),
                    "confidence": get_conf("acceptance_percentage"),
                    "validated": False
                },
                "tax_registration_number": {
                    "value": to_str(getattr(invoice, "tax_registration_number", None), None),
                    "confidence": get_conf("tax_registration_number"),
                    "validated": False
                }
            },
            "addresses": {
                "vendor_address": {
                    "value": invoice.vendor_address.model_dump(mode="json") if invoice.vendor_address else {
                        "street": None,
                        "city": None,
                        "province": None,
                        "postal_code": None,
                        "country": None
                    },
                    "confidence": get_conf("vendor_address"),
                    "validated": False
                },
                "bill_to_address": {
                    "value": invoice.bill_to_address.model_dump(mode="json") if getattr(invoice, "bill_to_address", None) else {
                        "street": None,
                        "city": None,
                        "province": None,
                        "postal_code": None,
                        "country": None
                    },
                    "confidence": get_conf("bill_to_address"),
                    "validated": False
                },
                "remit_to_address": {
                    "value": invoice.remit_to_address.model_dump(mode="json") if getattr(invoice, "remit_to_address", None) else {
                        "street": None,
                        "city": None,
                        "province": None,
                        "postal_code": None,
                        "country": None
                    },
                    "confidence": get_conf("remit_to_address"),
                    "validated": False
                },
                "customer_address": {
                    "value": invoice.bill_to_address.model_dump(mode="json") if getattr(invoice, "bill_to_address", None) else {
                        "street": None,
                        "city": None,
                        "province": None,
                        "postal_code": None,
                        "country": None
                    },
                    "confidence": get_conf("customer_address"),
                    "validated": False
                }
            },
            "line_items": [
                {
                    "line_number": item.line_number,
                    "description": to_str(item.description, "Not extracted"),
                    "quantity": to_number(item.quantity),
                    "unit_price": to_number(item.unit_price),
                    "amount": to_number(item.amount, default=0.0),
                    "confidence": item.confidence,
                    "unit_of_measure": item.unit_of_measure,
                    "tax_rate": to_number(item.tax_rate),
                    "tax_amount": to_number(item.tax_amount),
                    "gst_amount": to_number(getattr(item, "gst_amount", None)),
                    "pst_amount": to_number(getattr(item, "pst_amount", None)),
                    "qst_amount": to_number(getattr(item, "qst_amount", None)),
                    "combined_tax": to_number(getattr(item, "combined_tax", None)),
                    "project_code": item.project_code,
                    "cost_centre_code": item.cost_centre_code,
                    "airport_code": item.airport_code,
                    "validated": False
                }
                for item in invoice.line_items
            ],
            "extensions": invoice.extensions.model_dump(mode="json") if invoice.extensions else None,
            "invoice_subtype": invoice.invoice_subtype.value if invoice.invoice_subtype else None
        }
        
        return JSONResponse(status_code=200, content=jsonable_encoder(response))
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting invoice for validation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/invoice/validate", response_model=InvoiceValidationResponse)
async def validate_invoice(
    request: InvoiceValidationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Validate and correct invoice data (HITL step)
    
    Accepts field-level corrections and validation status.
    Updates invoice with validated/corrected data.
    
    Args:
        request: InvoiceValidationRequest with validations and corrections
        
    Returns:
        InvoiceValidationResponse with validation status
    """
    try:
        # Get invoice from database
        invoice = await DatabaseService.get_invoice(request.invoice_id, db=db)
        if not invoice:
            raise HTTPException(
                status_code=404,
                detail=f"Invoice {request.invoice_id} not found"
            )

        corrections_log = []

        # Apply field validations
        if request.field_validations:
            for field_validation in request.field_validations:
                # Apply corrections to invoice model
                if field_validation.validated and field_validation.corrected_value is not None:
                    # Map field names to invoice attributes
                    field_mapping = {
                        "invoice_number": "invoice_number",
                        "invoice_date": "invoice_date",
                        "due_date": "due_date",
                        "vendor_name": "vendor_name",
                        "vendor_id": "vendor_id",
                        "vendor_phone": "vendor_phone",
                        "customer_name": "customer_name",
                        "customer_id": "customer_id",
                        # addresses
                        "vendor_address": "vendor_address",
                        "bill_to_address": "bill_to_address",
                        "customer_address": "bill_to_address",
                        "remit_to_address": "remit_to_address",
                        "remit_to_name": "remit_to_name",
                        # contract/PO
                        "po_number": "po_number",
                        "contract_id": "contract_id",
                        "standing_offer_number": "standing_offer_number",
                        # financials
                        "subtotal": "subtotal",
                        "tax_amount": "tax_amount",
                        "total_amount": "total_amount",
                        "currency": "currency",
                        "payment_terms": "payment_terms",
                        "acceptance_percentage": "acceptance_percentage",
                        "tax_registration_number": "tax_registration_number",
                    }
                    
                    if field_validation.field_name in field_mapping:
                        attr_name = field_mapping[field_validation.field_name]
                        old_value = getattr(invoice, attr_name, None)
                        # Handle type conversions
                        if attr_name in ["subtotal", "tax_amount", "total_amount", "acceptance_percentage"]:
                            setattr(invoice, attr_name, Decimal(str(field_validation.corrected_value)))
                        elif attr_name in ["invoice_date", "due_date"]:
                            from dateutil.parser import parse
                            setattr(invoice, attr_name, parse(field_validation.corrected_value).date())
                        elif attr_name in ["vendor_address", "bill_to_address", "remit_to_address"]:
                            if isinstance(field_validation.corrected_value, dict):
                                try:
                                    setattr(invoice, attr_name, Address(**field_validation.corrected_value))
                                except Exception:
                                    # store raw dict if not parseable
                                    setattr(invoice, attr_name, field_validation.corrected_value)
                            else:
                                logger.warning(f"Skipping non-dict address correction for {attr_name}")
                        else:
                            setattr(invoice, attr_name, field_validation.corrected_value)
                        corrections_log.append({
                            "invoice_id": invoice.id,
                            "field": field_validation.field_name,
                            "old_value": old_value,
                            "new_value": field_validation.corrected_value,
                            "corrected_at": datetime.utcnow().isoformat()
                        })

        # Apply line item validations
        if request.line_item_validations:
            for item_validation in request.line_item_validations:
                # Find corresponding line item
                for line_item in invoice.line_items:
                    if line_item.line_number == item_validation.line_number:
                        if item_validation.validated and item_validation.corrections:
                            # Apply corrections
                            for field, value in item_validation.corrections.items():
                                if hasattr(line_item, field):
                                    old_value = getattr(line_item, field, None)
                                    if field in ["quantity", "unit_price", "amount", "tax_rate", "tax_amount", "gst_amount", "pst_amount", "qst_amount", "combined_tax"]:
                                        setattr(line_item, field, Decimal(str(value)))
                                    else:
                                        setattr(line_item, field, value)
                                    corrections_log.append({
                                        "invoice_id": invoice.id,
                                        "line_number": line_item.line_number,
                                        "field": field,
                                        "old_value": old_value,
                                        "new_value": value,
                                        "corrected_at": datetime.utcnow().isoformat()
                                    })
                        break

        # Update review status
        invoice.review_status = request.overall_validation_status
        invoice.reviewer = request.reviewer
        invoice.review_timestamp = datetime.utcnow()
        invoice.review_notes = request.validation_notes
        
        # Update status based on validation
        if request.overall_validation_status == "validated":
            invoice.status = "validated"
        elif request.overall_validation_status == "needs_review":
            invoice.status = "in_review"
        
        # Save updated invoice
        await DatabaseService.save_invoice(invoice, db=db)

        # Persist corrections log for training (jsonl)
        if corrections_log:
            try:
                log_dir = Path("logs")
                log_dir.mkdir(exist_ok=True)
                log_file = log_dir / "hitl_corrections.jsonl"
                with log_file.open("a", encoding="utf-8") as f:
                    for entry in corrections_log:
                        f.write(json.dumps(entry, default=str) + "\n")
            except Exception as log_err:
                logger.warning(f"Could not write HITL corrections log: {log_err}")
        
        return InvoiceValidationResponse(
            success=True,
            invoice_id=request.invoice_id,
            validation_status=request.overall_validation_status,
            message="Invoice validation completed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating invoice: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/invoice/{invoice_id}/pdf")
async def get_invoice_pdf(
    invoice_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get invoice PDF for display in HITL UI
    
    Args:
        invoice_id: Invoice ID
        
    Returns:
        PDF file content
    """
    try:
        # Get invoice from database
        invoice = await DatabaseService.get_invoice(invoice_id, db=db)
        if not invoice:
            raise HTTPException(
                status_code=404,
                detail=f"Invoice {invoice_id} not found"
            )
        
        pdf_content = None

        # If file_path is a URL (Azure blob), try HTTP then SDK
        if invoice.file_path and str(invoice.file_path).lower().startswith(("http://", "https://")):
            url_path = str(invoice.file_path)
            try:
                import requests

                resp = requests.get(url_path, timeout=15)
                if resp.status_code == 200:
                    pdf_content = resp.content
                else:
                    logger.warning(f"HTTP download failed for PDF {url_path} status={resp.status_code}; will try SDK/local fallback")
            except Exception as e:
                logger.error(f"Error downloading PDF from URL: {e}", exc_info=True)

            if pdf_content is None:
                try:
                    from urllib.parse import urlsplit
                    from azure.storage.blob import BlobServiceClient
                    from src.config import settings

                    split = urlsplit(url_path)
                    parts = split.path.lstrip("/").split("/", 1)
                    if len(parts) == 2:
                        container, blob_name = parts
                        if settings.AZURE_STORAGE_CONNECTION_STRING:
                            svc = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
                            blob_client = svc.get_blob_client(container=container, blob=blob_name)
                            pdf_content = blob_client.download_blob().readall()
                        elif settings.AZURE_STORAGE_ACCOUNT_NAME and settings.AZURE_STORAGE_ACCOUNT_KEY:
                            from azure.core.credentials import AzureNamedKeyCredential
                            credential = AzureNamedKeyCredential(settings.AZURE_STORAGE_ACCOUNT_NAME, settings.AZURE_STORAGE_ACCOUNT_KEY)
                            account_url = f"https://{settings.AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net"
                            svc = BlobServiceClient(account_url=account_url, credential=credential)
                            blob_client = svc.get_blob_client(container=container, blob=blob_name)
                            pdf_content = blob_client.download_blob().readall()
                    else:
                        logger.error(f"Could not parse container/blob from URL: {url_path}")
                except Exception as e:
                    logger.error(f"Error downloading PDF via Azure SDK: {e}", exc_info=True)

        if pdf_content is None:
            # Download PDF from storage (local or azure blob name)
            from src.ingestion.file_handler import FileHandler
            file_handler = FileHandler()
            try:
                pdf_content = file_handler.download_file(invoice.file_path)
            except Exception as e:
                logger.error(f"Error downloading PDF from storage: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail=f"Internal server error: {str(e)}"
                )
        
        if not pdf_content:
            raise HTTPException(
                status_code=404,
                detail=f"PDF file not found for invoice {invoice_id}"
            )
        
        from fastapi.responses import Response
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'inline; filename="{invoice.file_name}"'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting invoice PDF: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/invoices")
async def list_invoices_for_review(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List invoices for HITL review
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        status: Optional status filter (e.g., "extracted", "in_review")
        
    Returns:
        List of invoices with summary information
    """
    try:
        invoices = await DatabaseService.list_invoices(
            skip=skip,
            limit=limit,
            status=status,
            db=db
        )
        
        summary = [
            {
                "invoice_id": inv.id,
                "invoice_number": inv.invoice_number,
                "vendor_name": inv.vendor_name,
                "total_amount": float(inv.total_amount) if inv.total_amount else None,
                "currency": inv.currency,
                "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
                "status": inv.status,
                "review_status": inv.review_status,
                "extraction_confidence": inv.extraction_confidence,
                "upload_date": inv.upload_date.isoformat() if inv.upload_date else None,
                "line_item_count": len(inv.line_items) if inv.line_items else 0
            }
            for inv in invoices
        ]
        
        return JSONResponse(
            status_code=200,
            content={
                "invoices": summary,
                "total": len(summary),
                "skip": skip,
                "limit": limit
            }
        )
        
    except Exception as e:
        logger.error(f"Error listing invoices for review: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

