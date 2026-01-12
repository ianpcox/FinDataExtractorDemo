# Streamlit UI Fields Analysis

This document compares the fields actually displayed in the Streamlit UI
with the fields defined in the contract schema (invoice_ui_fields.csv).

## Summary

- **Fields in Streamlit UI**: 37
- **Fields in Contract Schema**: 24
- **Fields in UI CSV**: 24
- **Fields in Both Streamlit & Contract**: 24
- **Only in Streamlit UI (not in contract)**: 13
- **Only in Contract Schema (not in Streamlit UI)**: 0

## Fields Displayed in Streamlit UI

### Address Fields

- ✓ `vendor_address`
- ✓ `bill_to_address`
- ✓ `remit_to_address`

### Amount Fields

- ✓ `subtotal`
- ✓ `tax_amount`
- ✓ `total_amount`
- ✓ `currency`
- ✓ `payment_terms`
- ✓ `acceptance_percentage`

### Customer Fields

- ✓ `customer_name`
- ✓ `customer_id`
- ✗ `customer_phone`
- ✗ `customer_email`
- ✗ `customer_fax`

### Header Fields

- ✓ `invoice_number`
- ✓ `invoice_date`
- ✓ `due_date`
- ✗ `invoice_type`
- ✗ `reference_number`
- ✓ `po_number`
- ✓ `standing_offer_number`
- ✓ `contract_id`
- ✗ `entity`

### Period Fields

- ✓ `period_start`
- ✓ `period_end`

### Remit To Fields

- ✓ `remit_to_name`

### Vendor Fields

- ✓ `vendor_name`
- ✓ `vendor_id`
- ✓ `vendor_phone`
- ✗ `vendor_fax`
- ✗ `vendor_email`
- ✗ `vendor_website`

### Vendor Tax Fields

- ✗ `business_number`
- ✗ `gst_number`
- ✗ `qst_number`
- ✗ `pst_number`
- ✓ `tax_registration_number`

## Fields in Streamlit UI but NOT in Contract Schema

These fields are displayed in the UI but are not defined in the contract schema:

- `business_number`
- `customer_email`
- `customer_fax`
- `customer_phone`
- `entity`
- `gst_number`
- `invoice_type`
- `pst_number`
- `qst_number`
- `reference_number`
- `vendor_email`
- `vendor_fax`
- `vendor_website`

## Comparison with invoice_ui_fields.csv

- **Fields in Both**: 24
- **Only in CSV (not in Streamlit UI)**: 0
- **Only in Streamlit UI (not in CSV)**: 13

### Fields in Streamlit UI but NOT in CSV

- `business_number`
- `customer_email`
- `customer_fax`
- `customer_phone`
- `entity`
- `gst_number`
- `invoice_type`
- `pst_number`
- `qst_number`
- `reference_number`
- `vendor_email`
- `vendor_fax`
- `vendor_website`
