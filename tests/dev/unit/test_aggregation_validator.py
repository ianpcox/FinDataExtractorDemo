"""Unit tests for AggregationValidator"""

import pytest
from decimal import Decimal

from src.validation.aggregation_validator import AggregationValidator
from src.models.invoice import Invoice, LineItem


@pytest.mark.unit
class TestAggregationValidator:
    """Test AggregationValidator"""

    def test_validate_subtotal_success(self):
        """Test successful subtotal validation"""
        invoice = Invoice(
            subtotal=Decimal("1000.00"),
            line_items=[
                LineItem(amount=Decimal("400.00")),
                LineItem(amount=Decimal("600.00")),
            ],
        )
        
        is_valid, message = AggregationValidator.validate_subtotal(invoice)
        
        assert is_valid is True
        assert message is None

    def test_validate_subtotal_mismatch(self):
        """Test subtotal validation with mismatch"""
        invoice = Invoice(
            subtotal=Decimal("1000.00"),
            line_items=[
                LineItem(amount=Decimal("400.00")),
                LineItem(amount=Decimal("500.00")),  # Sum = 900, not 1000
            ],
        )
        
        is_valid, message = AggregationValidator.validate_subtotal(invoice)
        
        assert is_valid is False
        assert message is not None
        assert "mismatch" in message.lower() or "difference" in message.lower()

    def test_validate_subtotal_within_tolerance(self):
        """Test subtotal validation within tolerance"""
        invoice = Invoice(
            subtotal=Decimal("1000.00"),
            line_items=[
                LineItem(amount=Decimal("400.00")),
                LineItem(amount=Decimal("600.01")),  # 0.01 difference (within tolerance)
            ],
        )
        
        is_valid, message = AggregationValidator.validate_subtotal(invoice)
        
        assert is_valid is True  # Within 1 cent tolerance

    def test_validate_subtotal_no_line_items(self):
        """Test subtotal validation with no line items"""
        invoice = Invoice(
            subtotal=Decimal("1000.00"),
            line_items=[],
        )
        
        is_valid, message = AggregationValidator.validate_subtotal(invoice)
        
        assert is_valid is True  # No line items to validate
        assert message is None

    def test_validate_subtotal_no_subtotal(self):
        """Test subtotal validation with no subtotal"""
        invoice = Invoice(
            line_items=[
                LineItem(amount=Decimal("500.00")),
            ],
        )
        
        is_valid, message = AggregationValidator.validate_subtotal(invoice)
        
        assert is_valid is True  # No subtotal to validate
        assert message is None

    def test_validate_total_amount_success(self):
        """Test successful total amount validation"""
        invoice = Invoice(
            subtotal=Decimal("1000.00"),
            tax_amount=Decimal("150.00"),
            shipping_amount=Decimal("0.00"),
            handling_fee=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("1150.00"),
        )
        
        is_valid, message = AggregationValidator.validate_total_amount(invoice)
        
        assert is_valid is True
        assert message is None

    def test_validate_total_amount_mismatch(self):
        """Test total amount validation with mismatch"""
        invoice = Invoice(
            subtotal=Decimal("1000.00"),
            tax_amount=Decimal("150.00"),
            shipping_amount=Decimal("0.00"),
            handling_fee=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            total_amount=Decimal("1200.00"),  # Should be 1150.00
        )
        
        is_valid, message = AggregationValidator.validate_total_amount(invoice)
        
        assert is_valid is False
        assert message is not None

    def test_validate_total_amount_with_shipping_handling_discount(self):
        """Test total amount validation with shipping, handling, and discount"""
        invoice = Invoice(
            subtotal=Decimal("1000.00"),
            tax_amount=Decimal("150.00"),
            shipping_amount=Decimal("50.00"),
            handling_fee=Decimal("25.00"),
            discount_amount=Decimal("100.00"),
            total_amount=Decimal("1125.00"),  # 1000 + 150 + 50 + 25 - 100
        )
        
        is_valid, message = AggregationValidator.validate_total_amount(invoice)
        
        assert is_valid is True
        assert message is None

    def test_validate_all_aggregations_comprehensive(self):
        """Test validate_all method"""
        invoice = Invoice(
            subtotal=Decimal("1000.00"),
            tax_amount=Decimal("150.00"),
            total_amount=Decimal("1150.00"),
            gst_amount=Decimal("50.00"),
            pst_amount=Decimal("50.00"),
            qst_amount=Decimal("50.00"),
            shipping_amount=Decimal("0.00"),
            handling_fee=Decimal("0.00"),
            discount_amount=Decimal("0.00"),
            line_items=[
                LineItem(
                    amount=Decimal("500.00"),
                    gst_amount=Decimal("25.00"),
                    pst_amount=Decimal("25.00"),
                    qst_amount=Decimal("25.00"),
                    tax_amount=Decimal("75.00"),
                ),
                LineItem(
                    amount=Decimal("500.00"),
                    gst_amount=Decimal("25.00"),
                    pst_amount=Decimal("25.00"),
                    qst_amount=Decimal("25.00"),
                    tax_amount=Decimal("75.00"),
                ),
            ],
        )
        
        results = AggregationValidator.validate_all(invoice)
        
        assert "subtotal" in results
        assert "gst_amount" in results
        assert "pst_amount" in results
        assert "qst_amount" in results
        assert "tax_amount" in results
        assert "total_amount" in results
        assert all(is_valid for is_valid, _ in results.values())

    def test_get_validation_summary(self):
        """Test get_validation_summary method"""
        invoice = Invoice(
            subtotal=Decimal("1000.00"),
            tax_amount=Decimal("150.00"),
            total_amount=Decimal("1150.00"),
            line_items=[
                LineItem(amount=Decimal("500.00")),
                LineItem(amount=Decimal("500.00")),
            ],
        )
        
        summary = AggregationValidator.get_validation_summary(invoice)
        
        assert "all_valid" in summary
        assert "validations" in summary
        assert "errors" in summary
        assert "total_validations" in summary
        assert "passed_validations" in summary
        assert "failed_validations" in summary
        assert summary["all_valid"] is True
        assert len(summary["errors"]) == 0

    def test_validate_gst_amount_success(self):
        """Test successful GST amount validation"""
        invoice = Invoice(
            gst_amount=Decimal("70.00"),
            line_items=[
                LineItem(gst_amount=Decimal("30.00")),
                LineItem(gst_amount=Decimal("40.00")),
            ],
        )
        
        is_valid, message = AggregationValidator.validate_gst_amount(invoice)
        
        assert is_valid is True
        assert message is None

    def test_validate_gst_amount_mismatch(self):
        """Test GST amount validation with mismatch"""
        invoice = Invoice(
            gst_amount=Decimal("70.00"),
            line_items=[
                LineItem(gst_amount=Decimal("30.00")),
                LineItem(gst_amount=Decimal("35.00")),  # Sum = 65, not 70
            ],
        )
        
        is_valid, message = AggregationValidator.validate_gst_amount(invoice)
        
        assert is_valid is False
        assert message is not None

    def test_validate_pst_amount_success(self):
        """Test successful PST amount validation"""
        invoice = Invoice(
            pst_amount=Decimal("50.00"),
            line_items=[
                LineItem(pst_amount=Decimal("25.00")),
                LineItem(pst_amount=Decimal("25.00")),
            ],
        )
        
        is_valid, message = AggregationValidator.validate_pst_amount(invoice)
        
        assert is_valid is True
        assert message is None

    def test_validate_qst_amount_success(self):
        """Test successful QST amount validation"""
        invoice = Invoice(
            qst_amount=Decimal("60.00"),
            line_items=[
                LineItem(qst_amount=Decimal("30.00")),
                LineItem(qst_amount=Decimal("30.00")),
            ],
        )
        
        is_valid, message = AggregationValidator.validate_qst_amount(invoice)
        
        assert is_valid is True
        assert message is None

    def test_validate_all_aggregations(self):
        """Test validating all aggregations"""
        invoice = Invoice(
            subtotal=Decimal("1000.00"),
            tax_amount=Decimal("150.00"),
            total_amount=Decimal("1150.00"),
            gst_amount=Decimal("50.00"),
            pst_amount=Decimal("50.00"),
            line_items=[
                LineItem(
                    amount=Decimal("500.00"),
                    gst_amount=Decimal("25.00"),
                    pst_amount=Decimal("25.00"),
                ),
                LineItem(
                    amount=Decimal("500.00"),
                    gst_amount=Decimal("25.00"),
                    pst_amount=Decimal("25.00"),
                ),
            ],
        )
        
        # Validate all aggregations
        subtotal_valid, _ = AggregationValidator.validate_subtotal(invoice)
        gst_valid, _ = AggregationValidator.validate_gst_amount(invoice)
        pst_valid, _ = AggregationValidator.validate_pst_amount(invoice)
        qst_valid, _ = AggregationValidator.validate_qst_amount(invoice)
        tax_valid, _ = AggregationValidator.validate_tax_amount(invoice)
        
        assert subtotal_valid is True
        assert gst_valid is True
        assert pst_valid is True
        assert qst_valid is True
        assert tax_valid is True

    def test_validate_with_none_values(self):
        """Test validation handles None values gracefully"""
        invoice = Invoice(
            subtotal=None,
            total_amount=None,
            line_items=[
                LineItem(amount=Decimal("500.00")),
            ],
        )
        
        is_valid, message = AggregationValidator.validate_subtotal(invoice)
        
        assert is_valid is True  # None values handled gracefully
        assert message is None

    def test_validate_with_string_amounts(self):
        """Test validation handles string amounts"""
        invoice = Invoice(
            subtotal=Decimal("1000.00"),
            line_items=[
                LineItem(amount=Decimal("600.00")),
                LineItem(amount=Decimal("400.00")),
            ],
        )
        
        # Test that string conversion works (from LLM responses)
        invoice.subtotal = "1000.00"  # String value
        
        is_valid, message = AggregationValidator.validate_subtotal(invoice)
        
        # Should handle string conversion gracefully
        assert is_valid is True or is_valid is False  # Should not crash

    def test_validate_tax_amount_success(self):
        """Test successful tax amount validation"""
        invoice = Invoice(
            tax_amount=Decimal("150.00"),
            line_items=[
                LineItem(tax_amount=Decimal("75.00")),
                LineItem(tax_amount=Decimal("75.00")),
            ],
        )
        
        is_valid, message = AggregationValidator.validate_tax_amount(invoice)
        
        assert is_valid is True
        assert message is None

    def test_validate_tax_amount_with_individual_taxes(self):
        """Test tax amount validation using individual taxes (GST+PST+QST)"""
        invoice = Invoice(
            tax_amount=Decimal("150.00"),
            line_items=[
                LineItem(
                    gst_amount=Decimal("25.00"),
                    pst_amount=Decimal("25.00"),
                    qst_amount=Decimal("25.00"),
                ),
                LineItem(
                    gst_amount=Decimal("25.00"),
                    pst_amount=Decimal("25.00"),
                    qst_amount=Decimal("25.00"),
                ),
            ],
        )
        
        is_valid, message = AggregationValidator.validate_tax_amount(invoice)
        
        # Should match using sum of individual taxes (GST+PST+QST)
        assert is_valid is True
