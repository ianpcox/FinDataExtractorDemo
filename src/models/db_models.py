"""Simplified SQLAlchemy ORM models"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Date, Numeric, Text, JSON
from datetime import datetime, date
from decimal import Decimal
import uuid

from .database import Base


class Invoice(Base):
    """Simplified Invoice table"""
    __tablename__ = "invoices"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # File information
    file_path = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    upload_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    status = Column(String(50), nullable=False, default="processing")
    
    # Extracted Data
    invoice_number = Column(String(100), nullable=True, index=True)
    invoice_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)
    vendor_name = Column(String, nullable=True)
    vendor_address = Column(JSON, nullable=True)
    customer_name = Column(String, nullable=True)
    customer_id = Column(String, nullable=True)
    subtotal = Column(Numeric(18, 2), nullable=True)
    tax_amount = Column(Numeric(18, 2), nullable=True)
    total_amount = Column(Numeric(18, 2), nullable=True)
    currency = Column(String(10), nullable=True, default="CAD")
    payment_terms = Column(String, nullable=True)
    po_number = Column(String(100), nullable=True, index=True)
    
    # Line items (stored as JSON)
    line_items = Column(JSON, nullable=True)
    
    # Metadata
    extraction_confidence = Column(Float, nullable=True)
    extraction_timestamp = Column(DateTime, nullable=True)
    
    # Review
    review_status = Column(String(50), nullable=True)
    reviewer = Column(String(100), nullable=True)
    review_timestamp = Column(DateTime, nullable=True)
    review_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

