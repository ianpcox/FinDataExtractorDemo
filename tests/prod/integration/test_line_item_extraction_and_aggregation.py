"""Integration tests for line item extraction and aggregation validation

This test suite validates:
1. Line item extraction from Document Intelligence
2. Per-line-item field extraction (quantity, unit_price, amount, taxes)
3. Aggregation validation (invoice totals = sum of line item values)
4. Data integrity between invoice-level and line-item-level data
"""

import pytest
from decimal import Decimal
from datetime import datetime

from src.extraction.document_intelligence_client import DocumentIntelligenceClient
from src.extraction.field_extractor import FieldExtractor
from src.models.invoice import Invoice, LineItem


@pytest.mark.integration
class TestLineItemExtraction:
    """Tier 2: Test individual line item extraction"""
    
    def test_extract_line_item_basic_fields(self, sample_di_with_line_items):
        """Test extraction of basic line item fields"""
        extractor = FieldExtractor()
        invoice = extractor.extract_invoice(
            doc_intelligence_data=sample_di_with_line_items,
            file_path="test/invoice.pdf",
            file_name="test_invoice.pdf",
            upload_date=datetime.utcnow()
        )
        
        assert len(invoice.line_items) > 0, "Should extract at least one line item"
        
        line_item = invoice.line_items[0]
        assert line_item.line_number > 0, "Line number should be positive"
        assert line_item.description, "Description should not be empty"
        assert line_item.amount is not None, "Amount should be extracted"
        assert line_item.amount > 0, "Amount should be positive"
    
    def test_extract_line_item_quantity_and_unit_price(self, sample_di_with_line_items):
        """Test extraction of quantity and unit_price per line item"""
        extractor = FieldExtractor()
        invoice = extractor.extract_invoice(
            doc_intelligence_data=sample_di_with_line_items,
            file_path="test/invoice.pdf",
            file_name="test_invoice.pdf",
            upload_date=datetime.utcnow()
        )
        
        for line_item in invoice.line_items:
            if line_item.quantity and line_item.unit_price:
                # Validate: amount should equal quantity * unit_price (within rounding)
                expected_amount = line_item.quantity * line_item.unit_price
                # Allow for rounding differences (e.g., 0.01)
                assert abs(line_item.amount - expected_amount) <= Decimal("0.01"), \
                    f"Line {line_item.line_number}: amount ({line_item.amount}) should equal quantity * unit_price ({expected_amount})"
    
    def test_extract_line_item_taxes(self, sample_di_with_line_items):
        """Test extraction of per-line-item tax fields"""
        extractor = FieldExtractor()
        invoice = extractor.extract_invoice(
            doc_intelligence_data=sample_di_with_line_items,
            file_path="test/invoice.pdf",
            file_name="test_invoice.pdf",
            upload_date=datetime.utcnow()
        )
        
        for line_item in invoice.line_items:
            # Check if any tax fields are present
            has_tax = any([
                line_item.gst_amount,
                line_item.pst_amount,
                line_item.qst_amount,
                line_item.tax_amount,
                line_item.combined_tax
            ])
            
            if has_tax:
                # If tax_rate is present, validate tax calculation
                if line_item.tax_rate and line_item.amount:
                    expected_tax = line_item.amount * line_item.tax_rate
                    if line_item.tax_amount:
                        # Allow for rounding differences
                        assert abs(line_item.tax_amount - expected_tax) <= Decimal("0.01"), \
                            f"Line {line_item.line_number}: tax_amount should equal amount * tax_rate"
    
    def test_line_item_confidence_scores(self, sample_di_with_line_items):
        """Test that line items have confidence scores"""
        extractor = FieldExtractor()
        invoice = extractor.extract_invoice(
            doc_intelligence_data=sample_di_with_line_items,
            file_path="test/invoice.pdf",
            file_name="test_invoice.pdf",
            upload_date=datetime.utcnow()
        )
        
        for line_item in invoice.line_items:
            assert 0.0 <= line_item.confidence <= 1.0, \
                f"Line {line_item.line_number}: confidence should be between 0 and 1"


@pytest.mark.integration
class TestAggregationValidation:
    """Tier 3: Test aggregation validation (invoice totals = sum of line items)"""
    
    def test_subtotal_equals_sum_of_line_item_amounts(self, sample_di_with_line_items):
        """Validate: invoice.subtotal == sum(line_item.amount)"""
        extractor = FieldExtractor()
        invoice = extractor.extract_invoice(
            doc_intelligence_data=sample_di_with_line_items,
            file_path="test/invoice.pdf",
            file_name="test_invoice.pdf",
            upload_date=datetime.utcnow()
        )
        
        if invoice.subtotal is not None and len(invoice.line_items) > 0:
            sum_line_amounts = sum(item.amount for item in invoice.line_items)
            # Allow for rounding differences (e.g., 0.01)
            assert abs(invoice.subtotal - sum_line_amounts) <= Decimal("0.01"), \
                f"Subtotal ({invoice.subtotal}) should equal sum of line item amounts ({sum_line_amounts})"
    
    def test_gst_amount_equals_sum_of_line_item_gst(self, sample_di_with_line_items):
        """Validate: invoice.gst_amount == sum(line_item.gst_amount)"""
        extractor = FieldExtractor()
        invoice = extractor.extract_invoice(
            doc_intelligence_data=sample_di_with_line_items,
            file_path="test/invoice.pdf",
            file_name="test_invoice.pdf",
            upload_date=datetime.utcnow()
        )
        
        if invoice.gst_amount is not None and len(invoice.line_items) > 0:
            sum_line_gst = sum(item.gst_amount or Decimal("0") for item in invoice.line_items)
            # Allow for rounding differences
            assert abs(invoice.gst_amount - sum_line_gst) <= Decimal("0.01"), \
                f"GST amount ({invoice.gst_amount}) should equal sum of line item GST ({sum_line_gst})"
    
    def test_pst_amount_equals_sum_of_line_item_pst(self, sample_di_with_line_items):
        """Validate: invoice.pst_amount == sum(line_item.pst_amount)"""
        extractor = FieldExtractor()
        invoice = extractor.extract_invoice(
            doc_intelligence_data=sample_di_with_line_items,
            file_path="test/invoice.pdf",
            file_name="test_invoice.pdf",
            upload_date=datetime.utcnow()
        )
        
        if invoice.pst_amount is not None and len(invoice.line_items) > 0:
            sum_line_pst = sum(item.pst_amount or Decimal("0") for item in invoice.line_items)
            # Allow for rounding differences
            assert abs(invoice.pst_amount - sum_line_pst) <= Decimal("0.01"), \
                f"PST amount ({invoice.pst_amount}) should equal sum of line item PST ({sum_line_pst})"
    
    def test_qst_amount_equals_sum_of_line_item_qst(self, sample_di_with_line_items):
        """Validate: invoice.qst_amount == sum(line_item.qst_amount)"""
        extractor = FieldExtractor()
        invoice = extractor.extract_invoice(
            doc_intelligence_data=sample_di_with_line_items,
            file_path="test/invoice.pdf",
            file_name="test_invoice.pdf",
            upload_date=datetime.utcnow()
        )
        
        if invoice.qst_amount is not None and len(invoice.line_items) > 0:
            sum_line_qst = sum(item.qst_amount or Decimal("0") for item in invoice.line_items)
            # Allow for rounding differences
            assert abs(invoice.qst_amount - sum_line_qst) <= Decimal("0.01"), \
                f"QST amount ({invoice.qst_amount}) should equal sum of line item QST ({sum_line_qst})"
    
    def test_tax_amount_equals_sum_of_line_item_taxes(self, sample_di_with_line_items):
        """Validate: invoice.tax_amount == sum(line_item.tax_amount) OR sum(gst + pst + qst)"""
        extractor = FieldExtractor()
        invoice = extractor.extract_invoice(
            doc_intelligence_data=sample_di_with_line_items,
            file_path="test/invoice.pdf",
            file_name="test_invoice.pdf",
            upload_date=datetime.utcnow()
        )
        
        if invoice.tax_amount is not None and len(invoice.line_items) > 0:
            # Try sum of line_item.tax_amount first
            sum_line_tax = sum(item.tax_amount or Decimal("0") for item in invoice.line_items)
            
            # If that doesn't match, try sum of individual taxes
            if abs(invoice.tax_amount - sum_line_tax) > Decimal("0.01"):
                sum_individual_taxes = sum(
                    (item.gst_amount or Decimal("0")) + 
                    (item.pst_amount or Decimal("0")) + 
                    (item.qst_amount or Decimal("0"))
                    for item in invoice.line_items
                )
                # Allow for rounding differences
                assert abs(invoice.tax_amount - sum_individual_taxes) <= Decimal("0.01"), \
                    f"Tax amount ({invoice.tax_amount}) should equal sum of line item taxes ({sum_individual_taxes})"
            else:
                # First method matched
                assert True
    
    def test_total_amount_calculation(self, sample_di_with_line_items):
        """Validate: invoice.total_amount == subtotal + tax_amount + shipping + handling - discount"""
        extractor = FieldExtractor()
        invoice = extractor.extract_invoice(
            doc_intelligence_data=sample_di_with_line_items,
            file_path="test/invoice.pdf",
            file_name="test_invoice.pdf",
            upload_date=datetime.utcnow()
        )
        
        if invoice.total_amount is not None:
            calculated_total = (
                (invoice.subtotal or Decimal("0")) +
                (invoice.tax_amount or Decimal("0")) +
                (invoice.shipping_amount or Decimal("0")) +
                (invoice.handling_fee or Decimal("0")) -
                (invoice.discount_amount or Decimal("0"))
            )
            # Allow for rounding differences
            assert abs(invoice.total_amount - calculated_total) <= Decimal("0.01"), \
                f"Total amount ({invoice.total_amount}) should equal subtotal + tax + shipping + handling - discount ({calculated_total})"


@pytest.mark.integration
class TestLineItemDataIntegrity:
    """Test data integrity between invoice and line items"""
    
    def test_line_item_line_numbers_are_sequential(self, sample_di_with_line_items):
        """Validate line numbers are sequential starting from 1"""
        extractor = FieldExtractor()
        invoice = extractor.extract_invoice(
            doc_intelligence_data=sample_di_with_line_items,
            file_path="test/invoice.pdf",
            file_name="test_invoice.pdf",
            upload_date=datetime.utcnow()
        )
        
        if len(invoice.line_items) > 0:
            line_numbers = sorted([item.line_number for item in invoice.line_items])
            # Line numbers should be sequential starting from 1
            assert line_numbers == list(range(1, len(invoice.line_items) + 1)), \
                f"Line numbers should be sequential: {line_numbers}"
    
    def test_all_line_items_have_required_fields(self, sample_di_with_line_items):
        """Validate all line items have required fields (line_number, description, amount)"""
        extractor = FieldExtractor()
        invoice = extractor.extract_invoice(
            doc_intelligence_data=sample_di_with_line_items,
            file_path="test/invoice.pdf",
            file_name="test_invoice.pdf",
            upload_date=datetime.utcnow()
        )
        
        for line_item in invoice.line_items:
            assert line_item.line_number > 0, f"Line {line_item.line_number}: line_number is required"
            assert line_item.description, f"Line {line_item.line_number}: description is required"
            assert line_item.amount is not None, f"Line {line_item.line_number}: amount is required"
            assert line_item.amount >= 0, f"Line {line_item.line_number}: amount should be non-negative"


@pytest.fixture
def sample_di_with_line_items():
    """Fixture providing sample DI data with line items in normalized format"""
    # Return data in the format that normalize_di_data expects
    # This matches the format from DocumentIntelligenceClient._extract_invoice_fields
    return {
        "invoice_number": "INV-001",
        "invoice_date": "2024-01-15",
        "vendor_name": "Test Vendor",
        "customer_name": "Test Customer",
        "subtotal": "1000.00",
        "tax_amount": "120.00",
        "total_amount": "1120.00",
        "currency": "CAD",
        "items": [
            {
                "description": "Item A",
                "quantity": "10",
                "unit_price": "50.00",
                "amount": "500.00",
                "tax": "60.00",
                "gst_amount": "25.00",
                "pst_amount": "35.00",
                "confidence": 0.90
            },
            {
                "description": "Item B",
                "quantity": "10",
                "unit_price": "50.00",
                "amount": "500.00",
                "tax": "60.00",
                "gst_amount": "25.00",
                "pst_amount": "35.00",
                "confidence": 0.90
            }
        ],
        "field_confidence": {
            "invoice_number": 0.95,
            "invoice_date": 0.90,
            "vendor_name": 0.92,
            "subtotal": 0.98,
            "total_amount": 0.98
        },
        "confidence": 0.88
    }
