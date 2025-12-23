"""Business rule validation service for invoice data quality"""

from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal
import logging
from datetime import date

from src.models.invoice import Invoice

logger = logging.getLogger(__name__)


class ValidationRule:
    """Base class for validation rules"""
    
    def __init__(self, name: str, severity: str = "warning"):
        """
        Initialize validation rule
        
        Args:
            name: Rule name/description
            severity: "error" (blocking) or "warning" (non-blocking)
        """
        self.name = name
        self.severity = severity
    
    def validate(self, invoice: Invoice) -> Tuple[bool, Optional[str]]:
        """
        Validate invoice against this rule
        
        Returns:
            (is_valid, error_message)
        """
        raise NotImplementedError()


class LineItemsTotalMatchesSubtotal(ValidationRule):
    """Validate that line items sum to subtotal"""
    
    def __init__(self, tolerance: Decimal = Decimal("0.02")):
        super().__init__("Line items sum matches subtotal", severity="warning")
        self.tolerance = tolerance
    
    def validate(self, invoice: Invoice) -> Tuple[bool, Optional[str]]:
        if not invoice.line_items or not invoice.subtotal:
            return (True, None)  # Skip if no data
        
        line_items_total = sum(
            (item.amount or Decimal("0")) for item in invoice.line_items
        )
        
        diff = abs(line_items_total - invoice.subtotal)
        if diff > self.tolerance:
            return (
                False,
                f"Line items total ${line_items_total} differs from subtotal ${invoice.subtotal} by ${diff}"
            )
        
        return (True, None)


class TotalAmountCalculation(ValidationRule):
    """Validate that total = subtotal + tax"""
    
    def __init__(self, tolerance: Decimal = Decimal("0.02")):
        super().__init__("Total amount = subtotal + tax", severity="warning")
        self.tolerance = tolerance
    
    def validate(self, invoice: Invoice) -> Tuple[bool, Optional[str]]:
        if not invoice.total_amount:
            return (True, None)
        
        if not invoice.subtotal:
            return (True, None)  # Can't validate without subtotal
        
        tax_amount = invoice.tax_amount or Decimal("0")
        calculated_total = invoice.subtotal + tax_amount
        
        diff = abs(calculated_total - invoice.total_amount)
        if diff > self.tolerance:
            return (
                False,
                f"Calculated total ${calculated_total} (subtotal ${invoice.subtotal} + tax ${tax_amount}) differs from invoice total ${invoice.total_amount} by ${diff}"
            )
        
        return (True, None)


class CanadianTaxCalculation(ValidationRule):
    """Validate Canadian tax calculations (GST/HST/PST/QST)"""
    
    def __init__(self, tolerance: Decimal = Decimal("0.02")):
        super().__init__("Canadian tax calculation", severity="warning")
        self.tolerance = tolerance
    
    def validate(self, invoice: Invoice) -> Tuple[bool, Optional[str]]:
        if not invoice.subtotal:
            return (True, None)
        
        # Calculate expected tax amounts based on rates
        warnings = []
        
        if invoice.gst_rate and invoice.gst_amount:
            expected_gst = invoice.subtotal * invoice.gst_rate
            diff = abs(expected_gst - invoice.gst_amount)
            if diff > self.tolerance:
                warnings.append(
                    f"GST: expected ${expected_gst} ({invoice.gst_rate*100}%), got ${invoice.gst_amount}"
                )
        
        if invoice.hst_rate and invoice.hst_amount:
            expected_hst = invoice.subtotal * invoice.hst_rate
            diff = abs(expected_hst - invoice.hst_amount)
            if diff > self.tolerance:
                warnings.append(
                    f"HST: expected ${expected_hst} ({invoice.hst_rate*100}%), got ${invoice.hst_amount}"
                )
        
        if invoice.qst_rate and invoice.qst_amount:
            expected_qst = invoice.subtotal * invoice.qst_rate
            diff = abs(expected_qst - invoice.qst_amount)
            if diff > self.tolerance:
                warnings.append(
                    f"QST: expected ${expected_qst} ({invoice.qst_rate*100}%), got ${invoice.qst_amount}"
                )
        
        if invoice.pst_rate and invoice.pst_amount:
            expected_pst = invoice.subtotal * invoice.pst_rate
            diff = abs(expected_pst - invoice.pst_amount)
            if diff > self.tolerance:
                warnings.append(
                    f"PST: expected ${expected_pst} ({invoice.pst_rate*100}%), got ${invoice.pst_amount}"
                )
        
        if warnings:
            return (False, "; ".join(warnings))
        
        return (True, None)


class RequiredFieldsPresent(ValidationRule):
    """Validate that required fields are present"""
    
    def __init__(self):
        super().__init__("Required fields present", severity="error")
        self.required_fields = [
            "invoice_number",
            "invoice_date",
            "vendor_name",
            "total_amount",
        ]
    
    def validate(self, invoice: Invoice) -> Tuple[bool, Optional[str]]:
        missing = []
        for field in self.required_fields:
            value = getattr(invoice, field, None)
            if value is None or value == "":
                missing.append(field)
        
        if missing:
            return (False, f"Missing required fields: {', '.join(missing)}")
        
        return (True, None)


class DateLogicValidation(ValidationRule):
    """Validate date logic (due date after invoice date, etc.)"""
    
    def __init__(self):
        super().__init__("Date logic", severity="warning")
    
    def validate(self, invoice: Invoice) -> Tuple[bool, Optional[str]]:
        warnings = []
        
        # Due date should be after invoice date
        if invoice.invoice_date and invoice.due_date:
            if invoice.due_date < invoice.invoice_date:
                warnings.append(
                    f"Due date {invoice.due_date} is before invoice date {invoice.invoice_date}"
                )
        
        # Period end should be after period start
        if invoice.period_start and invoice.period_end:
            if invoice.period_end < invoice.period_start:
                warnings.append(
                    f"Period end {invoice.period_end} is before period start {invoice.period_start}"
                )
        
        # Delivery date should be after shipping date
        if invoice.shipping_date and invoice.delivery_date:
            if invoice.delivery_date < invoice.shipping_date:
                warnings.append(
                    f"Delivery date {invoice.delivery_date} is before shipping date {invoice.shipping_date}"
                )
        
        if warnings:
            return (False, "; ".join(warnings))
        
        return (True, None)


class NegativeAmountsValidation(ValidationRule):
    """Validate that amounts are not negative (except for credit notes)"""
    
    def __init__(self):
        super().__init__("No negative amounts", severity="warning")
    
    def validate(self, invoice: Invoice) -> Tuple[bool, Optional[str]]:
        # Allow negative amounts for credit notes
        if invoice.invoice_type and "credit" in invoice.invoice_type.lower():
            return (True, None)
        
        warnings = []
        
        if invoice.subtotal and invoice.subtotal < 0:
            warnings.append(f"Negative subtotal: ${invoice.subtotal}")
        
        if invoice.tax_amount and invoice.tax_amount < 0:
            warnings.append(f"Negative tax amount: ${invoice.tax_amount}")
        
        if invoice.total_amount and invoice.total_amount < 0:
            warnings.append(f"Negative total amount: ${invoice.total_amount}")
        
        # Check line items
        for idx, item in enumerate(invoice.line_items or []):
            if item.amount and item.amount < 0:
                warnings.append(f"Line item {idx+1}: negative amount ${item.amount}")
        
        if warnings:
            return (False, "; ".join(warnings))
        
        return (True, None)


class ValidationService:
    """Service for validating invoice business rules"""
    
    def __init__(self):
        """Initialize validation service with default rules"""
        self.rules: List[ValidationRule] = [
            RequiredFieldsPresent(),
            LineItemsTotalMatchesSubtotal(),
            TotalAmountCalculation(),
            CanadianTaxCalculation(),
            DateLogicValidation(),
            NegativeAmountsValidation(),
        ]
    
    def add_rule(self, rule: ValidationRule):
        """Add a custom validation rule"""
        self.rules.append(rule)
    
    def validate(self, invoice: Invoice) -> Dict[str, Any]:
        """
        Validate invoice against all rules
        
        Returns:
            {
                "is_valid": bool,
                "errors": [{"rule": str, "message": str, "severity": str}],
                "warnings": [{"rule": str, "message": str}],
                "passed_rules": int,
                "total_rules": int
            }
        """
        errors = []
        warnings = []
        passed = 0
        
        for rule in self.rules:
            try:
                is_valid, message = rule.validate(invoice)
                
                if is_valid:
                    passed += 1
                else:
                    failure = {
                        "rule": rule.name,
                        "message": message,
                        "severity": rule.severity
                    }
                    
                    if rule.severity == "error":
                        errors.append(failure)
                    else:
                        warnings.append(failure)
                        
            except Exception as e:
                logger.error(f"Error running validation rule '{rule.name}': {e}", exc_info=True)
                errors.append({
                    "rule": rule.name,
                    "message": f"Validation rule error: {str(e)}",
                    "severity": "error"
                })
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "passed_rules": passed,
            "total_rules": len(self.rules)
        }
    
    def validate_and_log(self, invoice: Invoice) -> bool:
        """
        Validate invoice and log results
        
        Returns:
            True if valid (no errors), False if errors found
        """
        result = self.validate(invoice)
        
        if result["errors"]:
            logger.warning(
                f"Invoice {invoice.id} validation failed with {len(result['errors'])} error(s)"
            )
            for error in result["errors"]:
                logger.warning(f"  - [{error['severity'].upper()}] {error['rule']}: {error['message']}")
        
        if result["warnings"]:
            logger.info(
                f"Invoice {invoice.id} has {len(result['warnings'])} validation warning(s)"
            )
            for warning in result["warnings"]:
                logger.info(f"  - [WARNING] {warning['rule']}: {warning['message']}")
        
        if result["is_valid"] and not result["warnings"]:
            logger.info(f"Invoice {invoice.id} passed all {result['total_rules']} validation rules")
        
        return result["is_valid"]
