"""Unit tests for ValidationService"""

import pytest
from decimal import Decimal
from datetime import date

from src.services.validation_service import (
    ValidationService,
    ValidationRule,
    LineItemsTotalMatchesSubtotal,
    TotalAmountCalculation,
    NegativeAmountsValidation,
    RequiredFieldsPresent,
)
from src.models.invoice import Invoice, LineItem


@pytest.mark.unit
class TestValidationService:
    """Test ValidationService"""

    def test_validate_invoice_success(self):
        """Test successful invoice validation"""
        invoice = Invoice(
            invoice_number="INV-001",
            invoice_date=date.today(),
            subtotal=Decimal("1000.00"),
            tax_amount=Decimal("150.00"),
            total_amount=Decimal("1150.00"),
            line_items=[
                LineItem(
                    description="Item 1",
                    quantity=Decimal("1"),
                    unit_price=Decimal("500.00"),
                    amount=Decimal("500.00"),
                ),
                LineItem(
                    description="Item 2",
                    quantity=Decimal("1"),
                    unit_price=Decimal("500.00"),
                    amount=Decimal("500.00"),
                ),
            ],
        )
        
        service = ValidationService()
        result = service.validate(invoice)
        
        assert result["is_valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_invoice_missing_required_fields(self):
        """Test validation fails for missing required fields"""
        invoice = Invoice(
            invoice_number=None,  # Missing required field
            invoice_date=date.today(),
        )
        
        service = ValidationService()
        result = service.validate(invoice)
        
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0
        assert any("required" in str(error).lower() or "invoice_number" in str(error).lower() 
                   for error in result["errors"])

    def test_validate_invoice_totals_mismatch(self):
        """Test validation fails when totals don't match"""
        invoice = Invoice(
            invoice_number="INV-001",
            invoice_date=date.today(),
            subtotal=Decimal("1000.00"),
            tax_amount=Decimal("150.00"),
            total_amount=Decimal("1200.00"),  # Should be 1150.00
            line_items=[
                LineItem(
                    description="Item 1",
                    quantity=Decimal("1"),
                    unit_price=Decimal("500.00"),
                    amount=Decimal("500.00"),
                ),
                LineItem(
                    description="Item 2",
                    quantity=Decimal("1"),
                    unit_price=Decimal("500.00"),
                    amount=Decimal("500.00"),
                ),
            ],
        )
        
        service = ValidationService()
        result = service.validate(invoice)
        
        # Should detect total calculation mismatch
        assert result["is_valid"] is False
        assert len(result["warnings"]) > 0
        assert any("total" in str(warning).lower() for warning in result["warnings"])

    def test_validate_invoice_negative_amounts(self):
        """Test validation handles negative amounts"""
        invoice = Invoice(
            invoice_number="INV-001",
            invoice_date=date.today(),
            subtotal=Decimal("-100.00"),  # Negative amount
            tax_amount=Decimal("0.00"),
            total_amount=Decimal("-100.00"),
        )
        
        service = ValidationService()
        result = service.validate(invoice)
        
        # Should flag negative amounts as warnings
        assert len(result["warnings"]) > 0
        assert any("negative" in str(warning).lower() for warning in result["warnings"])

    def test_validate_invoice_credit_note_allows_negative(self):
        """Test validation allows negative amounts for credit notes"""
        invoice = Invoice(
            invoice_number="CREDIT-001",
            invoice_date=date.today(),
            invoice_type="Credit Note",
            subtotal=Decimal("-100.00"),  # Negative for credit note
            tax_amount=Decimal("-15.00"),
            total_amount=Decimal("-115.00"),
        )
        
        service = ValidationService()
        result = service.validate(invoice)
        
        # Credit notes should allow negative amounts
        # Should not have negative amount warnings
        negative_warnings = [w for w in result["warnings"] if "negative" in str(w).lower()]
        assert len(negative_warnings) == 0

    def test_validate_and_log_success(self):
        """Test validate_and_log returns True for valid invoice"""
        invoice = Invoice(
            invoice_number="INV-001",
            invoice_date=date.today(),
            subtotal=Decimal("1000.00"),
            tax_amount=Decimal("150.00"),
            total_amount=Decimal("1150.00"),
        )
        
        service = ValidationService()
        result = service.validate_and_log(invoice)
        
        assert result is True

    def test_validate_and_log_failure(self):
        """Test validate_and_log returns False for invalid invoice"""
        invoice = Invoice(
            invoice_number=None,  # Missing required
            invoice_date=date.today(),
        )
        
        service = ValidationService()
        result = service.validate_and_log(invoice)
        
        assert result is False

    def test_add_custom_rule(self):
        """Test adding custom validation rule"""
        class CustomRule(ValidationRule):
            def validate(self, invoice):
                if invoice.invoice_number == "CUSTOM":
                    return (False, "Custom validation failed")
                return (True, None)
        
        invoice = Invoice(
            invoice_number="CUSTOM",
            invoice_date=date.today(),
        )
        
        service = ValidationService()
        service.add_rule(CustomRule("Custom rule", severity="error"))
        
        result = service.validate(invoice)
        
        assert result["is_valid"] is False
        assert any("Custom" in str(error) for error in result["errors"])

    def test_validation_rule_error_handling(self):
        """Test that validation service handles rule errors gracefully"""
        class FaultyRule(ValidationRule):
            def validate(self, invoice):
                raise Exception("Rule error")
        
        invoice = Invoice(
            invoice_number="INV-001",
            invoice_date=date.today(),
        )
        
        service = ValidationService()
        service.add_rule(FaultyRule("Faulty rule", severity="error"))
        
        result = service.validate(invoice)
        
        # Should handle error gracefully and add to errors
        assert len(result["errors"]) > 0
        assert any("error" in str(error).lower() for error in result["errors"])


@pytest.mark.unit
class TestValidationRules:
    """Test individual validation rules"""

    def test_line_items_total_matches_subtotal_success(self):
        """Test line items total matches subtotal"""
        invoice = Invoice(
            subtotal=Decimal("1000.00"),
            line_items=[
                LineItem(amount=Decimal("600.00")),
                LineItem(amount=Decimal("400.00")),
            ],
        )
        
        rule = LineItemsTotalMatchesSubtotal()
        is_valid, message = rule.validate(invoice)
        
        assert is_valid is True
        assert message is None

    def test_line_items_total_matches_subtotal_failure(self):
        """Test line items total doesn't match subtotal"""
        invoice = Invoice(
            subtotal=Decimal("1000.00"),
            line_items=[
                LineItem(amount=Decimal("600.00")),
                LineItem(amount=Decimal("300.00")),  # Total = 900, not 1000
            ],
        )
        
        rule = LineItemsTotalMatchesSubtotal(tolerance=Decimal("0.01"))
        is_valid, message = rule.validate(invoice)
        
        assert is_valid is False
        assert message is not None

    def test_total_amount_calculation_success(self):
        """Test total amount calculation is correct"""
        invoice = Invoice(
            subtotal=Decimal("1000.00"),
            tax_amount=Decimal("150.00"),
            total_amount=Decimal("1150.00"),
        )
        
        rule = TotalAmountCalculation()
        is_valid, message = rule.validate(invoice)
        
        assert is_valid is True

    def test_total_amount_calculation_failure(self):
        """Test total amount calculation mismatch"""
        invoice = Invoice(
            subtotal=Decimal("1000.00"),
            tax_amount=Decimal("150.00"),
            total_amount=Decimal("1200.00"),  # Should be 1150.00
        )
        
        rule = TotalAmountCalculation(tolerance=Decimal("0.01"))
        is_valid, message = rule.validate(invoice)
        
        assert is_valid is False
        assert message is not None
