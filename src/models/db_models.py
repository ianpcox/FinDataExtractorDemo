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
    vendor_name = Column(String, nullable=True)
    vendor_id = Column(String, nullable=True)
    vendor_phone = Column(String, nullable=True)
    vendor_address = Column(JSON, nullable=True)
    remit_to_address = Column(JSON, nullable=True)
    remit_to_name = Column(String, nullable=True)
    customer_name = Column(String, nullable=True)
    customer_id = Column(String, nullable=True)
    entity = Column(String, nullable=True)
    bill_to_address = Column(JSON, nullable=True)
    contract_id = Column(String, nullable=True)
    standing_offer_number = Column(String, nullable=True)
    po_number = Column(String(100), nullable=True, index=True)
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    subtotal = Column(Numeric(18, 2), nullable=True)
    tax_breakdown = Column(JSON, nullable=True)
    tax_amount = Column(Numeric(18, 2), nullable=True)
    total_amount = Column(Numeric(18, 2), nullable=True)
    currency = Column(String(10), nullable=True, default="CAD")
    acceptance_percentage = Column(Numeric(5, 2), nullable=True)
    tax_registration_number = Column(String, nullable=True)
    payment_terms = Column(String, nullable=True)
    
    # Line items (stored as JSON)
    line_items = Column(JSON, nullable=True)
    
    # Subtype and Extensions
    invoice_subtype = Column(String(50), nullable=True)
    extensions = Column(JSON, nullable=True)
    
    # Metadata
    extraction_confidence = Column(Float, nullable=True)
    field_confidence = Column(JSON, nullable=True)
    extraction_timestamp = Column(DateTime, nullable=True)
    
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

