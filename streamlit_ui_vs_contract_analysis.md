# Streamlit UI vs Contract Schema Field Analysis

This document analyzes the discrepancy between fields displayed in the Streamlit UI
and fields defined in the contract schema (which should represent the UI fields).

## Summary

- **Fields in Streamlit UI**: 51
- **Fields in Contract Schema**: 24
- **Fields in UI CSV**: 24
- **Fields in Both Streamlit & Contract**: 24
- **Only in Streamlit UI (not in contract)**: 27
- **Only in Contract Schema (not in Streamlit UI)**: 0

## Fields Displayed in Streamlit UI

### Header Fields (Tab 1: Company and Vendor)
- ✓ `invoice_number`
- ✓ `invoice_date`
- ✓ `due_date`
- ✗ `invoice_type`
- ✗ `reference_number`
- ✓ `po_number`
- ✓ `standing_offer_number`
- ✓ `contract_id`
- ✗ `entity`

### Vendor Fields (Tab 1)
- ✓ `vendor_name`
- ✓ `vendor_id`
- ✓ `vendor_phone`
- ✗ `vendor_fax`
- ✗ `vendor_email`
- ✗ `vendor_website`

### Vendor Tax Fields (Tab 1)
- ✗ `business_number`
- ✗ `gst_number`
- ✗ `qst_number`
- ✗ `pst_number`
- ✓ `tax_registration_number`

### Customer Fields (Tab 1)
- ✓ `customer_name`
- ✓ `customer_id`
- ✗ `customer_phone`
- ✗ `customer_email`
- ✗ `customer_fax`

### Remit-To Fields (Tab 1)
- ✓ `remit_to_name`

### Address Fields (Tab 5: Addresses)
- ✓ `vendor_address`
- ✓ `bill_to_address`
- ✓ `remit_to_address`

### Financial Fields (Tab 2: Financial)
- ✓ `subtotal`
- ✗ `discount_amount`
- ✗ `shipping_amount`
- ✗ `handling_fee`
- ✗ `deposit_amount`
- ✓ `tax_amount`
- ✓ `total_amount`
- ✓ `currency`

### Canadian Tax Fields (Tab 2: Financial)
- ✗ `gst_amount`
- ✗ `gst_rate`
- ✗ `hst_amount`
- ✗ `hst_rate`
- ✗ `qst_amount`
- ✗ `qst_rate`
- ✗ `pst_amount`
- ✗ `pst_rate`

### Payment Fields (Tab 3: Payment & Dates)
- ✓ `payment_terms`
- ✗ `payment_method`
- ✗ `payment_due_upon`
- ✓ `acceptance_percentage`

### Period Fields (Tab 3: Payment & Dates)
- ✓ `period_start`
- ✓ `period_end`

## ⚠️ Fields in Streamlit UI but NOT in Contract Schema

These fields are displayed in the Streamlit UI but are **missing** from the contract schema.
This means they cannot be properly extracted/validated according to the contract.

- `business_number`
- `customer_email`
- `customer_fax`
- `customer_phone`
- `deposit_amount`
- `discount_amount`
- `entity`
- `gst_amount`
- `gst_number`
- `gst_rate`
- `handling_fee`
- `hst_amount`
- `hst_rate`
- `invoice_type`
- `payment_due_upon`
- `payment_method`
- `pst_amount`
- `pst_number`
- `pst_rate`
- `qst_amount`
- `qst_number`
- `qst_rate`
- `reference_number`
- `shipping_amount`
- `vendor_email`
- `vendor_fax`
- `vendor_website`

## Comparison with invoice_ui_fields.csv

- **Fields in Both Streamlit & CSV**: 24
- **Only in CSV (not in Streamlit UI)**: 0
- **Only in Streamlit UI (not in CSV)**: 27

### Fields in Streamlit UI but NOT in CSV

- `business_number`
- `customer_email`
- `customer_fax`
- `customer_phone`
- `deposit_amount`
- `discount_amount`
- `entity`
- `gst_amount`
- `gst_number`
- `gst_rate`
- `handling_fee`
- `hst_amount`
- `hst_rate`
- `invoice_type`
- `payment_due_upon`
- `payment_method`
- `pst_amount`
- `pst_number`
- `pst_rate`
- `qst_amount`
- `qst_number`
- `qst_rate`
- `reference_number`
- `shipping_amount`
- `vendor_email`
- `vendor_fax`
- `vendor_website`
