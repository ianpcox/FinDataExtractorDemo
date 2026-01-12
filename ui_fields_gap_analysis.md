# UI Fields Gap Analysis: DEMO vs Vanilla

This document analyzes the gap between contract schema fields and what should be
displayed in the UI for both DEMO and Vanilla projects.

## Problem Summary

**The contract schemas and UI CSV files do NOT match what is actually displayed
in the Streamlit UI.**

From analysis of the Streamlit UI code:
- **DEMO Streamlit UI displays**: 51 fields
- **DEMO Contract Schema defines**: 24 fields
- **Missing from DEMO Contract**: 27 fields

This means 27 fields shown in the UI cannot be properly extracted/validated
according to the contract schema.

## Contract Schema Comparison

- **DEMO Contract Fields**: 24
- **Vanilla Contract Fields**: 24
- **Common Fields**: 24
- **Only in DEMO Contract**: 0
- **Only in Vanilla Contract**: 0

## CSV Comparison

- **DEMO CSV Fields**: 24
- **Vanilla CSV Fields**: 24
- **Common Fields**: 24
- **Only in DEMO CSV**: 0
- **Only in Vanilla CSV**: 0

## Recommendations

1. **Update Contract Schemas**: The contract schemas need to include ALL fields
   that are displayed in the Streamlit UI. Currently missing 27+ fields.

2. **Update UI CSV Files**: After updating contract schemas, regenerate the
   invoice_ui_fields.csv files to reflect all UI fields.

3. **Verify Both Projects**: Ensure both DEMO and Vanilla projects have
   consistent field definitions in their contract schemas.

4. **Field Categories**: The missing fields include:
   - Vendor contact fields (email, fax, website)
   - Customer contact fields (phone, email, fax)
   - Tax registration numbers (business_number, gst_number, qst_number, pst_number)
   - Financial adjustment fields (discount_amount, shipping_amount, handling_fee, deposit_amount)
   - Canadian tax amounts and rates (gst_amount, gst_rate, hst_amount, hst_rate, qst_amount, qst_rate, pst_amount, pst_rate)
   - Payment fields (payment_method, payment_due_upon)
   - Invoice metadata (invoice_type, reference_number, entity)
