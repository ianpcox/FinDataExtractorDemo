"""Simplified Invoice data models"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Address(BaseModel):
    """Address model"""
    street: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None


class LineItem(BaseModel):
    """Invoice line item model"""
    line_number: int
    description: str
    quantity: Optional[Decimal] = None
    unit_price: Optional[Decimal] = None
    amount: Decimal
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)


class Invoice(BaseModel):
    """Simplified Invoice model"""
    id: Optional[str] = None
    file_path: str
    file_name: str
    upload_date: datetime
    status: str = "processing"  # processing, extracted, validated, in_review, approved, rejected
    
    # Extracted Data
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    vendor_name: Optional[str] = None
    vendor_address: Optional[Address] = None
    customer_name: Optional[str] = None
    customer_id: Optional[str] = None
    subtotal: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None
    currency: str = "CAD"
    line_items: List[LineItem] = []
    payment_terms: Optional[str] = None
    po_number: Optional[str] = None
    
    # Metadata
    extraction_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    extraction_timestamp: Optional[datetime] = None
    
    # Review (simplified)
    review_status: Optional[str] = None  # pending_review, reviewed, skipped
    reviewer: Optional[str] = None
    review_timestamp: Optional[datetime] = None
    review_notes: Optional[str] = None
    
    class Config:
        json_encoders = {
            Decimal: str,
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat(),
        }

