"""Aggregation validation utilities

Validates that invoice-level aggregated fields match the sum of line item values.
"""

from decimal import Decimal
from typing import Optional, List
from src.models.invoice import Invoice, LineItem
import logging

logger = logging.getLogger(__name__)


class AggregationValidator:
    """Validates aggregation consistency between invoice and line items"""
    
    TOLERANCE = Decimal("0.01")  # Allow 1 cent rounding differences
    
    @staticmethod
    def validate_subtotal(invoice: Invoice) -> tuple[bool, Optional[str]]:
        """
        Validate: invoice.subtotal == sum(line_item.amount)
        
        Returns:
            (is_valid, error_message)
        """
        if invoice.subtotal is None:
            return True, None  # No subtotal to validate
        
        if not invoice.line_items:
            return True, None  # No line items to sum
        
        sum_line_amounts = sum(item.amount for item in invoice.line_items)
        difference = abs(invoice.subtotal - sum_line_amounts)
        
        if difference > AggregationValidator.TOLERANCE:
            return False, (
                f"Subtotal mismatch: invoice.subtotal={invoice.subtotal} != "
                f"sum(line_item.amount)={sum_line_amounts}, difference={difference}"
            )
        
        return True, None
    
    @staticmethod
    def validate_gst_amount(invoice: Invoice) -> tuple[bool, Optional[str]]:
        """
        Validate: invoice.gst_amount == sum(line_item.gst_amount)
        
        Returns:
            (is_valid, error_message)
        """
        if invoice.gst_amount is None:
            return True, None  # No GST to validate
        
        if not invoice.line_items:
            return True, None  # No line items to sum
        
        sum_line_gst = sum(item.gst_amount or Decimal("0") for item in invoice.line_items)
        difference = abs(invoice.gst_amount - sum_line_gst)
        
        if difference > AggregationValidator.TOLERANCE:
            return False, (
                f"GST amount mismatch: invoice.gst_amount={invoice.gst_amount} != "
                f"sum(line_item.gst_amount)={sum_line_gst}, difference={difference}"
            )
        
        return True, None
    
    @staticmethod
    def validate_pst_amount(invoice: Invoice) -> tuple[bool, Optional[str]]:
        """
        Validate: invoice.pst_amount == sum(line_item.pst_amount)
        
        Returns:
            (is_valid, error_message)
        """
        if invoice.pst_amount is None:
            return True, None  # No PST to validate
        
        if not invoice.line_items:
            return True, None  # No line items to sum
        
        sum_line_pst = sum(item.pst_amount or Decimal("0") for item in invoice.line_items)
        difference = abs(invoice.pst_amount - sum_line_pst)
        
        if difference > AggregationValidator.TOLERANCE:
            return False, (
                f"PST amount mismatch: invoice.pst_amount={invoice.pst_amount} != "
                f"sum(line_item.pst_amount)={sum_line_pst}, difference={difference}"
            )
        
        return True, None
    
    @staticmethod
    def validate_qst_amount(invoice: Invoice) -> tuple[bool, Optional[str]]:
        """
        Validate: invoice.qst_amount == sum(line_item.qst_amount)
        
        Returns:
            (is_valid, error_message)
        """
        if invoice.qst_amount is None:
            return True, None  # No QST to validate
        
        if not invoice.line_items:
            return True, None  # No line items to sum
        
        sum_line_qst = sum(item.qst_amount or Decimal("0") for item in invoice.line_items)
        difference = abs(invoice.qst_amount - sum_line_qst)
        
        if difference > AggregationValidator.TOLERANCE:
            return False, (
                f"QST amount mismatch: invoice.qst_amount={invoice.qst_amount} != "
                f"sum(line_item.qst_amount)={sum_line_qst}, difference={difference}"
            )
        
        return True, None
    
    @staticmethod
    def validate_tax_amount(invoice: Invoice) -> tuple[bool, Optional[str]]:
        """
        Validate: invoice.tax_amount == sum(line_item.tax_amount) OR sum(gst + pst + qst)
        
        Returns:
            (is_valid, error_message)
        """
        if invoice.tax_amount is None:
            return True, None  # No tax amount to validate
        
        if not invoice.line_items:
            return True, None  # No line items to sum
        
        # Try sum of line_item.tax_amount first
        sum_line_tax = sum(item.tax_amount or Decimal("0") for item in invoice.line_items)
        difference = abs(invoice.tax_amount - sum_line_tax)
        
        if difference <= AggregationValidator.TOLERANCE:
            return True, None  # Matched using tax_amount
        
        # If that doesn't match, try sum of individual taxes
        sum_individual_taxes = sum(
            (item.gst_amount or Decimal("0")) + 
            (item.pst_amount or Decimal("0")) + 
            (item.qst_amount or Decimal("0"))
            for item in invoice.line_items
        )
        difference = abs(invoice.tax_amount - sum_individual_taxes)
        
        if difference > AggregationValidator.TOLERANCE:
            return False, (
                f"Tax amount mismatch: invoice.tax_amount={invoice.tax_amount} != "
                f"sum(line_item.tax_amount)={sum_line_tax} and != "
                f"sum(gst+pst+qst)={sum_individual_taxes}, difference={difference}"
            )
        
        return True, None
    
    @staticmethod
    def validate_total_amount(invoice: Invoice) -> tuple[bool, Optional[str]]:
        """
        Validate: invoice.total_amount == subtotal + tax_amount + shipping + handling - discount
        
        Returns:
            (is_valid, error_message)
        """
        if invoice.total_amount is None:
            return True, None  # No total to validate
        
        calculated_total = (
            (invoice.subtotal or Decimal("0")) +
            (invoice.tax_amount or Decimal("0")) +
            (invoice.shipping_amount or Decimal("0")) +
            (invoice.handling_fee or Decimal("0")) -
            (invoice.discount_amount or Decimal("0"))
        )
        difference = abs(invoice.total_amount - calculated_total)
        
        if difference > AggregationValidator.TOLERANCE:
            return False, (
                f"Total amount mismatch: invoice.total_amount={invoice.total_amount} != "
                f"calculated (subtotal + tax + shipping + handling - discount)={calculated_total}, "
                f"difference={difference}"
            )
        
        return True, None
    
    @staticmethod
    def validate_all(invoice: Invoice) -> dict[str, tuple[bool, Optional[str]]]:
        """
        Run all aggregation validations.
        
        Returns:
            Dictionary mapping validation name to (is_valid, error_message)
        """
        results = {}
        
        results["subtotal"] = AggregationValidator.validate_subtotal(invoice)
        results["gst_amount"] = AggregationValidator.validate_gst_amount(invoice)
        results["pst_amount"] = AggregationValidator.validate_pst_amount(invoice)
        results["qst_amount"] = AggregationValidator.validate_qst_amount(invoice)
        results["tax_amount"] = AggregationValidator.validate_tax_amount(invoice)
        results["total_amount"] = AggregationValidator.validate_total_amount(invoice)
        
        return results
    
    @staticmethod
    def get_validation_summary(invoice: Invoice) -> dict[str, any]:
        """
        Get a summary of aggregation validation results.
        
        Returns:
            Dictionary with validation summary including:
            - all_valid: bool
            - validations: dict of validation results
            - errors: list of error messages
        """
        results = AggregationValidator.validate_all(invoice)
        
        all_valid = all(is_valid for is_valid, _ in results.values())
        errors = [error for is_valid, error in results.values() if not is_valid and error]
        
        return {
            "all_valid": all_valid,
            "validations": results,
            "errors": errors,
            "total_validations": len(results),
            "passed_validations": sum(1 for is_valid, _ in results.values() if is_valid),
            "failed_validations": len(errors)
        }
