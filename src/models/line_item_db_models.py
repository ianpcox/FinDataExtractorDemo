"""SQLAlchemy ORM model for Line Items - separate table with foreign key to Invoice

NOTE: This is a proposed model for future database migration.
Currently, line items are stored as JSON in the Invoice table.
"""

from sqlalchemy import Column, String, Integer, Numeric, Float, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from decimal import Decimal
import uuid

from .database import Base


class LineItem(Base):
    """Line Item table - separate from Invoice with foreign key relationship"""
    __tablename__ = "line_items"
    
    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Foreign key to Invoice
    invoice_id = Column(String(36), ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Line item fields
    line_number = Column(Integer, nullable=False)
    description = Column(String, nullable=False)
    quantity = Column(Numeric(18, 4), nullable=True)
    unit_price = Column(Numeric(18, 4), nullable=True)
    amount = Column(Numeric(18, 2), nullable=False)
    confidence = Column(Float, nullable=False, default=0.0)
    
    # Optional fields
    unit_of_measure = Column(String(50), nullable=True)
    tax_rate = Column(Numeric(5, 4), nullable=True)
    tax_amount = Column(Numeric(18, 2), nullable=True)
    gst_amount = Column(Numeric(18, 2), nullable=True)
    pst_amount = Column(Numeric(18, 2), nullable=True)
    qst_amount = Column(Numeric(18, 2), nullable=True)
    combined_tax = Column(Numeric(18, 2), nullable=True)
    acceptance_percentage = Column(Numeric(5, 2), nullable=True)
    
    # Project/Cost Centre codes
    project_code = Column(String(50), nullable=True)
    region_code = Column(String(50), nullable=True)
    airport_code = Column(String(10), nullable=True)
    cost_centre_code = Column(String(50), nullable=True)
    
    # Relationship
    invoice = relationship("Invoice", back_populates="line_items")
    
    # Indexes
    __table_args__ = (
        Index('ix_line_items_invoice_id', 'invoice_id'),
        Index('ix_line_items_line_number', 'invoice_id', 'line_number'),
    )
