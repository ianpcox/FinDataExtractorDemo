"""
Metrics configuration - single source of truth for canonical field definitions.

This module provides the canonical field count and definitions used across
all metrics calculations to ensure consistency with canonical field coverage reports.
"""

from src.extraction.extraction_service import CANONICAL_FIELDS

# Total number of canonical fields (used as denominator for extraction rate)
CANONICAL_FIELD_COUNT = len(CANONICAL_FIELDS)

# Required fields for "hard pass" evaluation
REQUIRED_FIELDS = [
    "invoice_number",
    "invoice_date",
    "vendor_name",
    "total_amount",
]

# Field importance weights for business impact scoring
FIELD_WEIGHTS = {
    # Critical fields (weight = 3.0)
    "invoice_number": 3.0,
    "invoice_date": 3.0,
    "total_amount": 3.0,
    "vendor_name": 3.0,
    
    # High importance (weight = 2.0)
    "due_date": 2.0,
    "subtotal": 2.0,
    "tax_amount": 2.0,
    "customer_name": 2.0,
    "currency": 2.0,
    "po_number": 2.0,
    
    # Medium importance (weight = 1.5)
    "vendor_address": 1.5,
    "bill_to_address": 1.5,
    "payment_terms": 1.5,
    "gst_amount": 1.5,
    "gst_rate": 1.5,
    "hst_amount": 1.5,
    "hst_rate": 1.5,
    "qst_amount": 1.5,
    "qst_rate": 1.5,
    "pst_amount": 1.5,
    "pst_rate": 1.5,
    
    # Standard importance (weight = 1.0) - default for all other fields
}

def get_canonical_field_count() -> int:
    """Get the total number of canonical fields (from canonical field coverage reports)"""
    return CANONICAL_FIELD_COUNT

def get_all_canonical_fields() -> list:
    """Get list of all canonical field names"""
    return list(CANONICAL_FIELDS)

def get_required_fields() -> list:
    """Get list of required fields for hard pass evaluation"""
    return REQUIRED_FIELDS.copy()

def get_field_weight(field_name: str) -> float:
    """Get importance weight for a field"""
    return FIELD_WEIGHTS.get(field_name, 1.0)
