"""Simplified utilities for converting between Pydantic and SQLAlchemy models"""

from typing import Optional
from datetime import datetime
import json
from decimal import Decimal
import logging

from .invoice import Invoice as InvoicePydantic, LineItem as LineItemPydantic, Address, InvoiceSubtype
from .db_models import Invoice as InvoiceDB
from .line_item_db_models import LineItem as LineItemDB
from .decimal_wire import decimal_to_wire, wire_to_decimal

logger = logging.getLogger(__name__)


def address_to_dict(address: Optional[Address]) -> Optional[dict]:
    """Convert Pydantic Address to dict for JSON storage"""
    if address is None:
        return None
    return {
        "street": address.street,
        "city": address.city,
        "province": address.province,
        "postal_code": address.postal_code,
        "country": address.country,
    }


def dict_to_address(data: Optional[dict]) -> Optional[Address]:
    """Convert dict to Pydantic Address"""
    if data is None:
        return None
    if isinstance(data, str):
        data = json.loads(data)
    return Address(**data)


def _sanitize_tax_breakdown(tb: Optional[dict]) -> Optional[dict]:
    """Convert tax breakdown dict to JSON-safe format using decimal strings"""
    if not tb:
        return None
    out = {}
    for k, v in tb.items():
        if isinstance(v, Decimal):
            out[k] = decimal_to_wire(v)
        else:
            # Try to convert to Decimal first, then to wire format
            d = wire_to_decimal(v)
            out[k] = decimal_to_wire(d) if d is not None else v
    return out


def line_items_to_json(line_items: list) -> Optional[dict]:
    """Convert list of LineItem Pydantic models to JSON-serializable dict using decimal strings
    
    Returns:
        - None: if line_items is None (represents "unset" - should not overwrite DB)
        - []: if line_items is explicitly empty list (represents "explicit empty" - but treated conservatively)
        - [items...]: if line_items contains items (represents "replace with these items")
    """
    if line_items is None:
        return None
    if not line_items:  # Empty list
        return []
    return [
        {
            "line_number": item.line_number,
            "description": item.description,
            "quantity": decimal_to_wire(item.quantity),
            "unit_price": decimal_to_wire(item.unit_price),
            "amount": decimal_to_wire(item.amount),
            "tax_rate": decimal_to_wire(item.tax_rate) if hasattr(item, 'tax_rate') else None,
            "tax_amount": decimal_to_wire(item.tax_amount) if hasattr(item, 'tax_amount') else None,
            "gst_amount": decimal_to_wire(item.gst_amount) if hasattr(item, 'gst_amount') else None,
            "pst_amount": decimal_to_wire(item.pst_amount) if hasattr(item, 'pst_amount') else None,
            "qst_amount": decimal_to_wire(item.qst_amount) if hasattr(item, 'qst_amount') else None,
            "combined_tax": decimal_to_wire(item.combined_tax) if hasattr(item, 'combined_tax') else None,
            "confidence": item.confidence,
            "unit_of_measure": item.unit_of_measure if hasattr(item, 'unit_of_measure') else None,
            "project_code": item.project_code if hasattr(item, 'project_code') else None,
            "region_code": item.region_code if hasattr(item, 'region_code') else None,
            "airport_code": item.airport_code if hasattr(item, 'airport_code') else None,
            "cost_centre_code": item.cost_centre_code if hasattr(item, 'cost_centre_code') else None,
        }
        for item in line_items
    ]


def json_to_line_items(data: Optional[dict]) -> list:
    """Convert JSON data to list of LineItem Pydantic models, parsing decimal strings"""
    if not data:
        return []
    if isinstance(data, str):
        data = json.loads(data)
    return [
        LineItemPydantic(
            line_number=item.get("line_number", i + 1),
            description=item.get("description", ""),
            quantity=wire_to_decimal(item.get("quantity")),
            unit_price=wire_to_decimal(item.get("unit_price")),
            amount=wire_to_decimal(item.get("amount")) or Decimal("0"),
            tax_rate=wire_to_decimal(item.get("tax_rate")),
            tax_amount=wire_to_decimal(item.get("tax_amount")),
            gst_amount=wire_to_decimal(item.get("gst_amount")),
            pst_amount=wire_to_decimal(item.get("pst_amount")),
            qst_amount=wire_to_decimal(item.get("qst_amount")),
            combined_tax=wire_to_decimal(item.get("combined_tax")),
            confidence=item.get("confidence", 0.0),
            unit_of_measure=item.get("unit_of_measure"),
            project_code=item.get("project_code"),
            region_code=item.get("region_code"),
            airport_code=item.get("airport_code"),
            cost_centre_code=item.get("cost_centre_code"),
        )
        for i, item in enumerate(data)
    ]


def _get_line_items_from_db(invoice_db: InvoiceDB) -> list:
    """
    Get line items from database, checking table first, then falling back to JSON.
    
    This supports the migration period where line items may be in either location.
    Priority: line_items table > JSON column
    """
    # Try to get line items from table (relationship)
    # The relationship should be loaded via selectinload in DatabaseService.get_invoice
    try:
        if hasattr(invoice_db, 'line_items_relationship'):
            # Check if relationship is loaded and has items
            relationship_items = getattr(invoice_db, 'line_items_relationship', None)
            if relationship_items is not None:
                # Check if it's a list/collection with items
                if hasattr(relationship_items, '__iter__') and not isinstance(relationship_items, str):
                    items_list = list(relationship_items)
                    if items_list:  # Only return if we have items from table
                        # Convert from DB models to Pydantic models
                        return [
                            LineItemPydantic(
                                line_number=item.line_number,
                                description=item.description,
                                quantity=item.quantity,
                                unit_price=item.unit_price,
                                amount=item.amount or Decimal("0"),
                                confidence=item.confidence or 0.0,
                                unit_of_measure=item.unit_of_measure,
                                tax_rate=item.tax_rate,
                                tax_amount=item.tax_amount,
                                gst_amount=item.gst_amount,
                                pst_amount=item.pst_amount,
                                qst_amount=item.qst_amount,
                                combined_tax=item.combined_tax,
                                acceptance_percentage=item.acceptance_percentage,
                                project_code=item.project_code,
                                region_code=item.region_code,
                                airport_code=item.airport_code,
                                cost_centre_code=item.cost_centre_code,
                            )
                            for item in items_list
                        ]
    except Exception as e:
        logger.debug(f"Could not load line items from relationship: {e}")
    
    # Fall back to JSON column (for backward compatibility during migration)
    return json_to_line_items(invoice_db.line_items)


def pydantic_to_db_invoice(invoice_pydantic: InvoicePydantic) -> InvoiceDB:
    """Convert Pydantic Invoice to SQLAlchemy Invoice (simplified)"""
    if not invoice_pydantic.id:
        raise ValueError("Invoice.id (invoice_id) is required and is the primary key.")

    # Convert invoice_subtype to string for DB storage
    subtype_str = None
    if invoice_pydantic.invoice_subtype is not None:
        if isinstance(invoice_pydantic.invoice_subtype, InvoiceSubtype):
            # Standard case: Enum → string
            subtype_str = invoice_pydantic.invoice_subtype.value
        elif isinstance(invoice_pydantic.invoice_subtype, str):
            # Legacy case: validate string is a valid subtype value
            try:
                InvoiceSubtype(invoice_pydantic.invoice_subtype)
                subtype_str = invoice_pydantic.invoice_subtype
            except ValueError:
                raise ValueError(
                    f"Invalid invoice_subtype: '{invoice_pydantic.invoice_subtype}'. "
                    f"Must be one of: {[e.value for e in InvoiceSubtype]}"
                )
        else:
            raise ValueError(
                f"invoice_subtype must be InvoiceSubtype Enum or valid string, got {type(invoice_pydantic.invoice_subtype)}"
            )

    invoice_db = InvoiceDB(
        id=invoice_pydantic.id,
        file_path=invoice_pydantic.file_path,
        file_name=invoice_pydantic.file_name,
        upload_date=invoice_pydantic.upload_date,
        status=invoice_pydantic.status,
        review_version=invoice_pydantic.review_version or 0,
        processing_state=invoice_pydantic.processing_state or "PENDING",
        content_sha256=invoice_pydantic.content_sha256,
        invoice_number=invoice_pydantic.invoice_number,
        invoice_date=invoice_pydantic.invoice_date,
        due_date=invoice_pydantic.due_date,
        vendor_name=invoice_pydantic.vendor_name,
        vendor_id=invoice_pydantic.vendor_id,
        vendor_phone=invoice_pydantic.vendor_phone,
        vendor_address=address_to_dict(invoice_pydantic.vendor_address),
        customer_name=invoice_pydantic.customer_name,
        customer_id=invoice_pydantic.customer_id,
        entity=invoice_pydantic.entity,
        bill_to_address=address_to_dict(invoice_pydantic.bill_to_address),
        remit_to_address=address_to_dict(invoice_pydantic.remit_to_address),
        remit_to_name=invoice_pydantic.remit_to_name,
        contract_id=invoice_pydantic.contract_id,
        standing_offer_number=invoice_pydantic.standing_offer_number,
        po_number=invoice_pydantic.po_number,
        period_start=invoice_pydantic.period_start,
        period_end=invoice_pydantic.period_end,
        subtotal=invoice_pydantic.subtotal,
        tax_breakdown=_sanitize_tax_breakdown(invoice_pydantic.tax_breakdown),
        tax_amount=invoice_pydantic.tax_amount,
        total_amount=invoice_pydantic.total_amount,
        currency=invoice_pydantic.currency,
        acceptance_percentage=invoice_pydantic.acceptance_percentage,
        tax_registration_number=invoice_pydantic.tax_registration_number,
        payment_terms=invoice_pydantic.payment_terms,
        line_items=line_items_to_json(invoice_pydantic.line_items),
        invoice_subtype=subtype_str,
        extensions=invoice_pydantic.extensions.dict() if invoice_pydantic.extensions else None,
        extraction_confidence=invoice_pydantic.extraction_confidence,
        field_confidence=invoice_pydantic.field_confidence,
        extraction_timestamp=invoice_pydantic.extraction_timestamp,
        review_status=invoice_pydantic.review_status,
        reviewer=invoice_pydantic.reviewer,
        review_timestamp=invoice_pydantic.review_timestamp,
        review_notes=invoice_pydantic.review_notes,
        bv_approver=invoice_pydantic.bv_approver,
        bv_approval_date=invoice_pydantic.bv_approval_date,
        bv_approval_notes=invoice_pydantic.bv_approval_notes,
        fa_approver=invoice_pydantic.fa_approver,
        fa_approval_date=invoice_pydantic.fa_approval_date,
        fa_approval_notes=invoice_pydantic.fa_approval_notes,
    )
    return invoice_db


def db_to_pydantic_invoice(invoice_db: InvoiceDB) -> InvoicePydantic:
    """Convert SQLAlchemy Invoice to Pydantic Invoice (simplified)"""
    
    # Convert invoice_subtype from DB string to Enum
    subtype_enum = None
    if invoice_db.invoice_subtype:
        try:
            subtype_enum = InvoiceSubtype(invoice_db.invoice_subtype)
        except ValueError:
            logger.warning(
                f"Unknown invoice_subtype '{invoice_db.invoice_subtype}' for invoice {invoice_db.id}; "
                f"setting to None. Valid values: {[e.value for e in InvoiceSubtype]}"
            )
            subtype_enum = None
    
    invoice_pydantic = InvoicePydantic(
        id=invoice_db.id,
        file_path=invoice_db.file_path,
        file_name=invoice_db.file_name,
        upload_date=invoice_db.upload_date,
        status=invoice_db.status,
        review_version=invoice_db.review_version or 0,
        processing_state=invoice_db.processing_state or "PENDING",
        content_sha256=invoice_db.content_sha256,
        invoice_number=invoice_db.invoice_number,
        invoice_date=invoice_db.invoice_date,
        due_date=invoice_db.due_date,
        vendor_name=invoice_db.vendor_name,
        vendor_id=invoice_db.vendor_id,
        vendor_phone=invoice_db.vendor_phone,
        vendor_address=dict_to_address(invoice_db.vendor_address),
        customer_name=invoice_db.customer_name,
        customer_id=invoice_db.customer_id,
        entity=invoice_db.entity,
        bill_to_address=dict_to_address(invoice_db.bill_to_address),
        remit_to_address=dict_to_address(invoice_db.remit_to_address),
        remit_to_name=invoice_db.remit_to_name,
        contract_id=invoice_db.contract_id,
        standing_offer_number=invoice_db.standing_offer_number,
        subtotal=invoice_db.subtotal,
        tax_breakdown=invoice_db.tax_breakdown,
        tax_amount=invoice_db.tax_amount,
        total_amount=invoice_db.total_amount,
        currency=invoice_db.currency or "CAD",
        acceptance_percentage=invoice_db.acceptance_percentage,
        tax_registration_number=invoice_db.tax_registration_number,
        payment_terms=invoice_db.payment_terms,
        po_number=invoice_db.po_number,
        line_items=_get_line_items_from_db(invoice_db),
        extraction_confidence=invoice_db.extraction_confidence or 0.0,
        extraction_timestamp=invoice_db.extraction_timestamp,
        field_confidence=invoice_db.field_confidence or {},
        invoice_subtype=subtype_enum,
        extensions=invoice_db.extensions,
        review_status=invoice_db.review_status,
        reviewer=invoice_db.reviewer,
        review_timestamp=invoice_db.review_timestamp,
        review_notes=invoice_db.review_notes,
        bv_approver=invoice_db.bv_approver,
        bv_approval_date=invoice_db.bv_approval_date,
        bv_approval_notes=invoice_db.bv_approval_notes,
        fa_approver=invoice_db.fa_approver,
        fa_approval_date=invoice_db.fa_approval_date,
        fa_approval_notes=invoice_db.fa_approval_notes,
    )
    return invoice_pydantic

