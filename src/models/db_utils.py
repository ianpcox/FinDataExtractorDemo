"""Simplified utilities for converting between Pydantic and SQLAlchemy models"""

from typing import Optional
from datetime import datetime
import json

from .invoice import Invoice as InvoicePydantic, LineItem as LineItemPydantic, Address
from .db_models import Invoice as InvoiceDB


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


def line_items_to_json(line_items: list) -> Optional[dict]:
    """Convert list of LineItem Pydantic models to JSON-serializable dict"""
    if not line_items:
        return None
    return [
        {
            "line_number": item.line_number,
            "description": item.description,
            "quantity": float(item.quantity) if item.quantity else None,
            "unit_price": float(item.unit_price) if item.unit_price else None,
            "amount": float(item.amount),
            "confidence": item.confidence,
        }
        for item in line_items
    ]


def json_to_line_items(data: Optional[dict]) -> list:
    """Convert JSON data to list of LineItem Pydantic models"""
    if not data:
        return []
    if isinstance(data, str):
        data = json.loads(data)
    return [
        LineItemPydantic(
            line_number=item.get("line_number", i + 1),
            description=item.get("description", ""),
            quantity=item.get("quantity"),
            unit_price=item.get("unit_price"),
            amount=item.get("amount", 0),
            confidence=item.get("confidence", 0.0),
        )
        for i, item in enumerate(data)
    ]


def pydantic_to_db_invoice(invoice_pydantic: InvoicePydantic) -> InvoiceDB:
    """Convert Pydantic Invoice to SQLAlchemy Invoice (simplified)"""
    invoice_db = InvoiceDB(
        id=invoice_pydantic.id or str(datetime.utcnow().timestamp()),
        file_path=invoice_pydantic.file_path,
        file_name=invoice_pydantic.file_name,
        upload_date=invoice_pydantic.upload_date,
        status=invoice_pydantic.status,
        invoice_number=invoice_pydantic.invoice_number,
        invoice_date=invoice_pydantic.invoice_date,
        due_date=invoice_pydantic.due_date,
        vendor_name=invoice_pydantic.vendor_name,
        vendor_address=address_to_dict(invoice_pydantic.vendor_address),
        customer_name=invoice_pydantic.customer_name,
        customer_id=invoice_pydantic.customer_id,
        subtotal=invoice_pydantic.subtotal,
        tax_amount=invoice_pydantic.tax_amount,
        total_amount=invoice_pydantic.total_amount,
        currency=invoice_pydantic.currency,
        payment_terms=invoice_pydantic.payment_terms,
        po_number=invoice_pydantic.po_number,
        line_items=line_items_to_json(invoice_pydantic.line_items),
        extraction_confidence=invoice_pydantic.extraction_confidence,
        extraction_timestamp=invoice_pydantic.extraction_timestamp,
        review_status=invoice_pydantic.review_status,
        reviewer=invoice_pydantic.reviewer,
        review_timestamp=invoice_pydantic.review_timestamp,
        review_notes=invoice_pydantic.review_notes,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    return invoice_db


def db_to_pydantic_invoice(invoice_db: InvoiceDB) -> InvoicePydantic:
    """Convert SQLAlchemy Invoice to Pydantic Invoice (simplified)"""
    invoice_pydantic = InvoicePydantic(
        id=invoice_db.id,
        file_path=invoice_db.file_path,
        file_name=invoice_db.file_name,
        upload_date=invoice_db.upload_date,
        status=invoice_db.status,
        invoice_number=invoice_db.invoice_number,
        invoice_date=invoice_db.invoice_date,
        due_date=invoice_db.due_date,
        vendor_name=invoice_db.vendor_name,
        vendor_address=dict_to_address(invoice_db.vendor_address),
        customer_name=invoice_db.customer_name,
        customer_id=invoice_db.customer_id,
        subtotal=invoice_db.subtotal,
        tax_amount=invoice_db.tax_amount,
        total_amount=invoice_db.total_amount,
        currency=invoice_db.currency or "CAD",
        payment_terms=invoice_db.payment_terms,
        po_number=invoice_db.po_number,
        line_items=json_to_line_items(invoice_db.line_items),
        extraction_confidence=invoice_db.extraction_confidence or 0.0,
        extraction_timestamp=invoice_db.extraction_timestamp,
        review_status=invoice_db.review_status,
        reviewer=invoice_db.reviewer,
        review_timestamp=invoice_db.review_timestamp,
        review_notes=invoice_db.review_notes,
    )
    return invoice_pydantic

