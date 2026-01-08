"""Simplified SQLAlchemy ORM models"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Date, Numeric, Text, JSON, Index
from datetime import datetime, date
from decimal import Decimal
import uuid

from .database import Base


class Invoice(Base):
    """Invoice table with all required fields"""
    __tablename__ = "invoices"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # File information
    file_path = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    upload_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(String(50), nullable=False, default="processing")
    
    # Extracted Data - Header
    invoice_number = Column(String(100), nullable=True, index=True)
    invoice_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)
    invoice_type = Column(String(50), nullable=True)  # Original, Revised, Credit Note
    reference_number = Column(String(100), nullable=True)
    
    # Vendor Information
    vendor_name = Column(String, nullable=True)
    vendor_id = Column(String, nullable=True)
    vendor_phone = Column(String, nullable=True)
    vendor_fax = Column(String, nullable=True)
    vendor_email = Column(String, nullable=True)
    vendor_website = Column(String, nullable=True)
    vendor_address = Column(JSON, nullable=True)
    
    # Vendor Tax Registration
    gst_number = Column(String(50), nullable=True)
    qst_number = Column(String(50), nullable=True)
    pst_number = Column(String(50), nullable=True)
    business_number = Column(String(50), nullable=True)
    
    # Customer Information
    customer_name = Column(String, nullable=True)
    customer_id = Column(String, nullable=True)
    customer_phone = Column(String, nullable=True)
    customer_email = Column(String, nullable=True)
    customer_fax = Column(String, nullable=True)
    bill_to_address = Column(JSON, nullable=True)
    
    # Remit-To Information
    remit_to_address = Column(JSON, nullable=True)
    remit_to_name = Column(String, nullable=True)
    
    # Entity/Contract
    entity = Column(String, nullable=True)
    contract_id = Column(String, nullable=True)
    standing_offer_number = Column(String, nullable=True)
    po_number = Column(String(100), nullable=True, index=True)
    
    # Dates
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    shipping_date = Column(Date, nullable=True)
    delivery_date = Column(Date, nullable=True)
    
    # Financial Totals
    subtotal = Column(Numeric(18, 2), nullable=True)
    discount_amount = Column(Numeric(18, 2), nullable=True)
    shipping_amount = Column(Numeric(18, 2), nullable=True)
    handling_fee = Column(Numeric(18, 2), nullable=True)
    
    # Canadian Tax Fields
    gst_amount = Column(Numeric(18, 2), nullable=True)
    gst_rate = Column(Numeric(5, 4), nullable=True)
    hst_amount = Column(Numeric(18, 2), nullable=True)
    hst_rate = Column(Numeric(5, 4), nullable=True)
    qst_amount = Column(Numeric(18, 2), nullable=True)
    qst_rate = Column(Numeric(5, 4), nullable=True)
    pst_amount = Column(Numeric(18, 2), nullable=True)
    pst_rate = Column(Numeric(5, 4), nullable=True)
    
    tax_breakdown = Column(JSON, nullable=True)
    tax_amount = Column(Numeric(18, 2), nullable=True)
    total_amount = Column(Numeric(18, 2), nullable=True)
    deposit_amount = Column(Numeric(18, 2), nullable=True)
    
    currency = Column(String(10), nullable=True, default="CAD")
    acceptance_percentage = Column(Numeric(5, 2), nullable=True)
    tax_registration_number = Column(String, nullable=True)
    
    # Payment Information
    payment_terms = Column(String, nullable=True)
    payment_method = Column(String(50), nullable=True)
    payment_due_upon = Column(String, nullable=True)
    
    # Line items (stored as JSON)
    line_items = Column(JSON, nullable=True)
    
    # Subtype and Extensions
    invoice_subtype = Column(String(50), nullable=True)
    extensions = Column(JSON, nullable=True)
    
    # Metadata
    extraction_confidence = Column(Float, nullable=True)
    field_confidence = Column(JSON, nullable=True)
    extraction_timestamp = Column(DateTime, nullable=True)
    review_version = Column(Integer, nullable=False, default=0)
    processing_state = Column(String(32), nullable=False, default="PENDING")
    content_sha256 = Column(String(128), nullable=True)
    
    # Review
    review_status = Column(String(50), nullable=True)
    reviewer = Column(String(100), nullable=True)
    review_timestamp = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)
    
    # Approval workflow
    bv_approver = Column(String(100), nullable=True)
    bv_approval_date = Column(DateTime, nullable=True)
    bv_approval_notes = Column(Text, nullable=True)
    fa_approver = Column(String(100), nullable=True)
    fa_approval_date = Column(DateTime, nullable=True)
    fa_approval_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('ix_invoices_status', 'status'),
        Index('ix_invoices_upload_date', 'upload_date'),
    )

