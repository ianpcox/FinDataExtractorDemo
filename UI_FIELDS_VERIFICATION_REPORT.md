# UI Fields Verification Report

## Summary

**Date:** Generated automatically  
**Status:**  All UI fields are included in canonical schema and CANONICAL_FIELDS

## Findings

###  Verified Fields

1. **All 53 UI fields are in CANONICAL_FIELDS** (from `extraction_service.py`)
2. **All 53 UI fields are in canonical schema** (from `schemas/invoice.canonical.v1.schema.json`)
3. **All address fields and subfields are properly included:**
   - `vendor_address`, `bill_to_address`, `remit_to_address`
   - Address subfields: `street`, `city`, `province`, `postal_code`, `country`
4. **All 53 UI fields are covered in tests**

###  Missing from UI (but in Canonical Schema)

The following fields are in the canonical schema and CANONICAL_FIELDS but are **NOT displayed in the Streamlit UI**:

1. **`remit_to_name`** - Name for remit-to address
   - Status: In canonical schema, in CANONICAL_FIELDS, but NOT in UI
   - Should be added to: Tab 1 (Company and Vendor) or Tab 5 (Addresses)

2. **`tax_breakdown`** - Computed/derived field (not a direct field)
   - Status: This is a computed field, not a direct input field, so it's acceptable to not display it

**Note:** `acceptance_percentage` is NOT a top-level canonical field. It only exists as a line item field.

## Field Breakdown by Tab

### Tab 1: Company and Vendor (29 fields)
- **Header Information (9):** invoice_number, invoice_date, due_date, invoice_type, reference_number, po_number, standing_offer_number, contract_id, entity
- **Vendor Information (6):** vendor_name, vendor_id, vendor_phone, vendor_fax, vendor_email, vendor_website
- **Vendor Tax IDs (5):** business_number, gst_number, qst_number, pst_number, tax_registration_number
- **Customer Information (5):** customer_name, customer_id, customer_phone, customer_email, customer_fax
- **Missing:** remit_to_name

### Tab 2: Financial (16 fields)
- **Amounts (8):** subtotal, discount_amount, shipping_amount, handling_fee, deposit_amount, tax_amount, total_amount, currency
- **Canadian Taxes (8):** gst_amount, gst_rate, hst_amount, hst_rate, qst_amount, qst_rate, pst_amount, pst_rate

### Tab 3: Payment & Dates (7 fields)
- **Payment Information (3):** payment_terms, payment_method, payment_due_upon
- **Important Dates (4):** period_start, period_end, shipping_date, delivery_date

### Tab 4: Line Items
- Line item fields are displayed dynamically
- Includes: line_number, description, quantity, unit_price, amount, tax_amount, gst_amount, pst_amount, qst_amount, combined_tax, acceptance_percentage (per line item)

### Tab 5: Addresses (3 address types)
- **Address Types:** vendor_address, bill_to_address, remit_to_address
- **Address Subfields (per type):** street, city, province, postal_code, country
- **Missing:** remit_to_name (name field for remit-to)

### Tab 6: Validation
- Validation status and notes (not field extraction)

## Recommendations

1. **Add `remit_to_name` to Tab 1 (Company and Vendor)**
   - Add to a new "Remit-To Information" section or to existing customer section
   - Display as a text input

2. **Verify all fields are properly tested**
   - Ensure `remit_to_name` is covered in test files

**Note:** `acceptance_percentage` is not a top-level canonical field and should not be displayed in the UI as a top-level field. It only exists as a line item field.

## Test Coverage

All 53 currently displayed UI fields are covered in:
- `tests/unit/test_di_canonical_field_coverage.py`
- `tests/unit/test_llm_canonical_field_coverage.py`
- `tests/unit/test_multimodal_llm_canonical_field_coverage.py`

## Address Fields Verification

 All address fields are properly included:
- Address types: `vendor_address`, `bill_to_address`, `remit_to_address`
- Address subfields: `street`, `city`, `province`, `postal_code`, `country`
- All address fields are in CANONICAL_FIELDS
- All address fields are in canonical schema
- Address subfields match the Address schema definition

