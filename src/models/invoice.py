"""Simplified Invoice data models with subtype support"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class InvoiceSubtype(str, Enum):
    """Invoice subtypes"""
    STANDARD_INVOICE = "STANDARD_INVOICE"
    SHIFT_SERVICE_INVOICE = "SHIFT_SERVICE_INVOICE"
    PER_DIEM_TRAVEL_INVOICE = "PER_DIEM_TRAVEL_INVOICE"


class InvoiceState(str, Enum):
    """Canonical invoice lifecycle states"""
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    EXTRACTED = "EXTRACTED"
    FAILED = "FAILED"
    VALIDATED = "VALIDATED"
    STAGED = "STAGED"


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
    # Optional fields
    unit_of_measure: Optional[str] = None
    tax_rate: Optional[Decimal] = None
    tax_amount: Optional[Decimal] = None
    gst_amount: Optional[Decimal] = None
    pst_amount: Optional[Decimal] = None
    qst_amount: Optional[Decimal] = None
    combined_tax: Optional[Decimal] = None
    project_code: Optional[str] = None
    region_code: Optional[str] = None
    airport_code: Optional[str] = None
    cost_centre_code: Optional[str] = None


class ShiftServiceExtension(BaseModel):
    """Extension data for shift-based service invoices"""
    service_location: Optional[str] = None
    billing_period_start: Optional[date] = None
    billing_period_end: Optional[date] = None
    shift_rate: Optional[Decimal] = None
    total_shifts_billed: Optional[int] = None
    min_shifts_per_period: Optional[int] = None


class TimesheetShift(BaseModel):
    """Individual shift entry from timesheet"""
    date: date
    worker_name: str
    shift_number: int
    time_in: Optional[str] = None
    time_out: Optional[str] = None


class TimesheetData(BaseModel):
    """Timesheet supporting document data"""
    representative_name: Optional[str] = None
    signature_present: bool = False
    comments: Optional[str] = None
    shifts: List[TimesheetShift] = Field(default_factory=list)


class PerDiemTravelExtension(BaseModel):
    """Extension data for per-diem travel invoices (per line item)"""
    traveller_id: Optional[str] = None
    traveller_name: Optional[str] = None
    programme_or_course_code: Optional[str] = None
    work_location: Optional[str] = None
    destination_location: Optional[str] = None
    travel_from_date: Optional[date] = None
    travel_to_date: Optional[date] = None
    training_start_date: Optional[date] = None
    training_end_date: Optional[date] = None
    travel_days: Optional[int] = None
    daily_rate: Optional[Decimal] = None
    line_total: Optional[Decimal] = None


class InvoiceExtensions(BaseModel):
    """Container for invoice subtype-specific extensions"""
    shift_service: Optional[ShiftServiceExtension] = None
    per_diem_travel: Optional[List[PerDiemTravelExtension]] = None
    timesheet_data: Optional[TimesheetData] = None


class Invoice(BaseModel):
    """Simplified Invoice model with subtype support"""
    id: Optional[str] = None
    file_path: str
    file_name: str
    upload_date: datetime
    status: str = "processing"  # processing, extracted, validated, in_review, approved, rejected
    review_version: int = 0
    processing_state: str = "PENDING"  # PENDING, PROCESSING, EXTRACTED, FAILED
    content_sha256: Optional[str] = None
    
    # Extracted Data - Header
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    vendor_name: Optional[str] = None
    vendor_id: Optional[str] = None
    vendor_phone: Optional[str] = None
    vendor_address: Optional[Address] = None
    bill_to_address: Optional[Address] = None
    remit_to_address: Optional[Address] = None
    remit_to_name: Optional[str] = None
    customer_name: Optional[str] = None
    customer_id: Optional[str] = None
    entity: Optional[str] = None
    contract_id: Optional[str] = None
    standing_offer_number: Optional[str] = None
    po_number: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    subtotal: Optional[Decimal] = None
    tax_breakdown: Optional[Dict[str, Decimal]] = None  # Tax type -> amount
    tax_amount: Optional[Decimal] = None
    total_amount: Optional[Decimal] = None
    acceptance_percentage: Optional[Decimal] = None
    tax_registration_number: Optional[str] = None
    currency: str = "CAD"
    line_items: List[LineItem] = Field(default_factory=list)
    payment_terms: Optional[str] = None
    
    # Subtype and Extensions
    invoice_subtype: Optional[InvoiceSubtype] = InvoiceSubtype.STANDARD_INVOICE
    extensions: Optional[InvoiceExtensions] = None
    
    # Metadata
    extraction_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    field_confidence: Optional[Dict[str, float]] = None  # Field name -> confidence
    extraction_timestamp: Optional[datetime] = None
    
    # Review (simplified)
    review_status: Optional[str] = None  # pending_review, reviewed, skipped
    reviewer: Optional[str] = None
    review_timestamp: Optional[datetime] = None
    review_notes: Optional[str] = None
    
    # Approval workflow (simplified)
    bv_approver: Optional[str] = None
    bv_approval_date: Optional[datetime] = None
    bv_approval_notes: Optional[str] = None
    fa_approver: Optional[str] = None
    fa_approval_date: Optional[datetime] = None
    fa_approval_notes: Optional[str] = None
    
    class Config:
        json_encoders = {
            Decimal: str,
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat(),
        }

