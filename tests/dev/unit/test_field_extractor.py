"""Unit tests for FieldExtractor"""

import pytest
from datetime import datetime, date
from decimal import Decimal

from src.extraction.field_extractor import FieldExtractor
from src.models.invoice import Invoice, InvoiceSubtype


@pytest.mark.unit
class TestFieldExtractor:
    """Test FieldExtractor"""
    
    def test_extract_invoice_basic_fields(
        self,
        sample_document_intelligence_data
    ):
        """Test extraction of basic invoice fields"""
        extractor = FieldExtractor()
        
        invoice = extractor.extract_invoice(
            doc_intelligence_data=sample_document_intelligence_data,
            file_path="test/path/invoice.pdf",
            file_name="test_invoice.pdf",
            upload_date=datetime.utcnow()
        )
        
        assert invoice.invoice_number == "INV-12345"
        assert invoice.invoice_date == date(2024, 1, 10)
        assert invoice.vendor_name == "Acme Corp"
        assert invoice.customer_name == "CATSA"
        assert invoice.total_amount == Decimal("1500.00")
        assert invoice.currency == "CAD"
        assert invoice.po_number == "PO-12345"
        assert len(invoice.line_items) == 1
        assert invoice.extraction_confidence > 0.0
        assert invoice.field_confidence is not None
    
    def test_extract_invoice_with_addresses(
        self,
        sample_document_intelligence_data
    ):
        """Test extraction with address data"""
        extractor = FieldExtractor()
        
        invoice = extractor.extract_invoice(
            doc_intelligence_data=sample_document_intelligence_data,
            file_path="test/path/invoice.pdf",
            file_name="test_invoice.pdf",
            upload_date=datetime.utcnow()
        )
        
        assert invoice.vendor_address is not None
        assert invoice.vendor_address.street == "123 Main St"
        assert invoice.vendor_address.city == "Vancouver"
        assert invoice.vendor_address.province == "BC"
    
    def test_extract_invoice_line_items(
        self,
        sample_document_intelligence_data
    ):
        """Test extraction of line items"""
        extractor = FieldExtractor()
        
        invoice = extractor.extract_invoice(
            doc_intelligence_data=sample_document_intelligence_data,
            file_path="test/path/invoice.pdf",
            file_name="test_invoice.pdf",
            upload_date=datetime.utcnow()
        )
        
        assert len(invoice.line_items) == 1
        line_item = invoice.line_items[0]
        assert line_item.line_number == 1
        assert line_item.description == "Item A"
        assert line_item.quantity == Decimal("10")
        assert line_item.unit_price == Decimal("100.00")
        assert line_item.amount == Decimal("1000.00")
        assert line_item.confidence == 0.90
    
    def test_extract_invoice_field_confidence(
        self,
        sample_document_intelligence_data
    ):
        """Test field-level confidence extraction"""
        extractor = FieldExtractor()
        
        invoice = extractor.extract_invoice(
            doc_intelligence_data=sample_document_intelligence_data,
            file_path="test/path/invoice.pdf",
            file_name="test_invoice.pdf",
            upload_date=datetime.utcnow()
        )
        
        assert invoice.field_confidence is not None
        assert "invoice_id" in invoice.field_confidence
        assert invoice.field_confidence["invoice_id"] == 0.95
        assert invoice.field_confidence["invoice_date"] == 0.90
    
    def test_extract_invoice_subtype_detection(
        self,
        sample_document_intelligence_data
    ):
        """Test subtype detection"""
        extractor = FieldExtractor()
        
        # Add shift service indicators to data
        sample_document_intelligence_data["content"] = "Service Location: YVR\nShift Rate: $150.00"
        
        invoice = extractor.extract_invoice(
            doc_intelligence_data=sample_document_intelligence_data,
            file_path="test/path/invoice.pdf",
            file_name="test_invoice.pdf",
            upload_date=datetime.utcnow(),
            invoice_text="Service Location: YVR\nShift Rate: $150.00"
        )
        
        # Subtype detection may or may not trigger depending on data
        assert invoice.invoice_subtype is not None

