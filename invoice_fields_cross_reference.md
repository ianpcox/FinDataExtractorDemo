# Invoice Fields Cross-Reference Analysis

This document cross-references the canonical schema fields with the UI fields to identify
which fields are captured/displayed in the UI and which are not, along with reasons.

## Summary

- **Total Canonical Fields**: 112
- **Fields in UI Form**: 24
- **Fields Not in UI Form**: 88

## Field Analysis by Category

### Amounts & Totals

| Field Name | Type | Required | In UI? | Reason/Notes |
|------------|------|----------|--------|--------------|
| `deposit_amount` | decimal_string | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |
| `discount_amount` | decimal_string | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |
| `gst_amount` | decimal_string | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |
| `gst_rate` | decimal_string | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |
| `handling_fee` | decimal_string | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |
| `hst_amount` | decimal_string | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |
| `hst_rate` | decimal_string | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |
| `pst_amount` | decimal_string | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |
| `pst_rate` | decimal_string | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |
| `qst_amount` | decimal_string | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |
| `qst_rate` | decimal_string | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |
| `shipping_amount` | decimal_string | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |
| `subtotal` | decimal_string | No | Yes | ✓ Displayed in UI schema form |
| `tax_amount` | decimal_string | No | Yes | ✓ Displayed in UI schema form |
| `tax_breakdown` | object | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |
| `total_amount` | decimal_string | No | Yes | ✓ Displayed in UI schema form |

### Contract/PO

| Field Name | Type | Required | In UI? | Reason/Notes |
|------------|------|----------|--------|--------------|
| `contract_id` | string, null | No | Yes | ✓ Displayed in UI schema form |
| `entity` | string, null | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |
| `po_number` | string, null | No | Yes | ✓ Displayed in UI schema form |
| `standing_offer_number` | string, null | No | Yes | ✓ Displayed in UI schema form |

### Customer Information

| Field Name | Type | Required | In UI? | Reason/Notes |
|------------|------|----------|--------|--------------|
| `bill_to_address` | address_object | No | Yes | ✓ Displayed in UI schema form |
| `bill_to_address.city` | string, null | No | No | Nested field within 'bill_to_address' object - address fields are displayed as structured objects in UI |
| `bill_to_address.country` | string, null | No | No | Nested field within 'bill_to_address' object - address fields are displayed as structured objects in UI |
| `bill_to_address.postal_code` | string, null | No | No | Nested field within 'bill_to_address' object - address fields are displayed as structured objects in UI |
| `bill_to_address.province` | string, null | No | No | Nested field within 'bill_to_address' object - address fields are displayed as structured objects in UI |
| `bill_to_address.street` | string, null | No | No | Nested field within 'bill_to_address' object - address fields are displayed as structured objects in UI |
| `customer_email` | string, null | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |
| `customer_fax` | string, null | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |
| `customer_id` | string, null | No | Yes | ✓ Displayed in UI schema form |
| `customer_name` | string, null | No | Yes | ✓ Displayed in UI schema form |
| `customer_phone` | string, null | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |

### Extensions

| Field Name | Type | Required | In UI? | Reason/Notes |
|------------|------|----------|--------|--------------|
| `extensions` | null | No | No | Extension fields are handled separately based on invoice_subtype (shift service, per diem travel) |

### Invoice Header

| Field Name | Type | Required | In UI? | Reason/Notes |
|------------|------|----------|--------|--------------|
| `acceptance_percentage` | decimal_string | No | Yes | ✓ Displayed in UI schema form |
| `currency` | string | Yes | Yes | ✓ Displayed in UI schema form |
| `delivery_date` | date | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |
| `due_date` | date | No | Yes | ✓ Displayed in UI schema form |
| `invoice_date` | date | No | Yes | ✓ Displayed in UI schema form |
| `invoice_number` | string, null | No | Yes | ✓ Displayed in UI schema form |
| `invoice_subtype` | null | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |
| `invoice_type` | string, null | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |
| `payment_due_upon` | string, null | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |
| `payment_method` | string, null | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |
| `payment_terms` | string, null | No | Yes | ✓ Displayed in UI schema form |
| `reference_number` | string, null | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |
| `shipping_date` | date | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |

### Line Items

| Field Name | Type | Required | In UI? | Reason/Notes |
|------------|------|----------|--------|--------------|
| `line_items` | array | Yes | No | Line items are displayed in a separate LineItemGrid component, not in the main schema form |
| `line_items[].airport_code` | string, null | No | No | Line items are displayed in a separate LineItemGrid component, not in the main schema form |
| `line_items[].amount` | decimal_string | Yes | No | Line items are displayed in a separate LineItemGrid component, not in the main schema form |
| `line_items[].combined_tax` | decimal_string | No | No | Line items are displayed in a separate LineItemGrid component, not in the main schema form |
| `line_items[].confidence` | unknown | Yes | No | Line items are displayed in a separate LineItemGrid component, not in the main schema form |
| `line_items[].cost_centre_code` | string, null | No | No | Line items are displayed in a separate LineItemGrid component, not in the main schema form |
| `line_items[].description` | string | Yes | No | Line items are displayed in a separate LineItemGrid component, not in the main schema form |
| `line_items[].gst_amount` | decimal_string | No | No | Line items are displayed in a separate LineItemGrid component, not in the main schema form |
| `line_items[].line_number` | integer | Yes | No | Line items are displayed in a separate LineItemGrid component, not in the main schema form |
| `line_items[].project_code` | string, null | No | No | Line items are displayed in a separate LineItemGrid component, not in the main schema form |
| `line_items[].pst_amount` | decimal_string | No | No | Line items are displayed in a separate LineItemGrid component, not in the main schema form |
| `line_items[].qst_amount` | decimal_string | No | No | Line items are displayed in a separate LineItemGrid component, not in the main schema form |
| `line_items[].quantity` | decimal_string | No | No | Line items are displayed in a separate LineItemGrid component, not in the main schema form |
| `line_items[].region_code` | string, null | No | No | Line items are displayed in a separate LineItemGrid component, not in the main schema form |
| `line_items[].tax_amount` | decimal_string | No | No | Line items are displayed in a separate LineItemGrid component, not in the main schema form |
| `line_items[].tax_rate` | decimal_string | No | No | Line items are displayed in a separate LineItemGrid component, not in the main schema form |
| `line_items[].unit_of_measure` | string, null | No | No | Line items are displayed in a separate LineItemGrid component, not in the main schema form |
| `line_items[].unit_price` | decimal_string | No | No | Line items are displayed in a separate LineItemGrid component, not in the main schema form |

### Remit-To Information

| Field Name | Type | Required | In UI? | Reason/Notes |
|------------|------|----------|--------|--------------|
| `remit_to_address` | address_object | No | Yes | ✓ Displayed in UI schema form |
| `remit_to_address.city` | string, null | No | No | Nested field within 'remit_to_address' object - address fields are displayed as structured objects in UI |
| `remit_to_address.country` | string, null | No | No | Nested field within 'remit_to_address' object - address fields are displayed as structured objects in UI |
| `remit_to_address.postal_code` | string, null | No | No | Nested field within 'remit_to_address' object - address fields are displayed as structured objects in UI |
| `remit_to_address.province` | string, null | No | No | Nested field within 'remit_to_address' object - address fields are displayed as structured objects in UI |
| `remit_to_address.street` | string, null | No | No | Nested field within 'remit_to_address' object - address fields are displayed as structured objects in UI |
| `remit_to_name` | string, null | No | Yes | ✓ Displayed in UI schema form |

### Service Period

| Field Name | Type | Required | In UI? | Reason/Notes |
|------------|------|----------|--------|--------------|
| `period_end` | date | No | Yes | ✓ Displayed in UI schema form |
| `period_start` | date | No | Yes | ✓ Displayed in UI schema form |

### System

| Field Name | Type | Required | In UI? | Reason/Notes |
|------------|------|----------|--------|--------------|
| `bv_approval_date` | date | No | No | System/internal field - not exposed in UI (e.g., database IDs, timestamps, processing state) |
| `bv_approval_notes` | string, null | No | No | System/internal field - not exposed in UI (e.g., database IDs, timestamps, processing state) |
| `bv_approver` | string, null | No | No | System/internal field - not exposed in UI (e.g., database IDs, timestamps, processing state) |
| `content_sha256` | string, null | No | No | System/internal field - not exposed in UI (e.g., database IDs, timestamps, processing state) |
| `created_at` | date | No | No | System/internal field - not exposed in UI (e.g., database IDs, timestamps, processing state) |
| `extraction_confidence` | unknown | Yes | No | System/internal field - not exposed in UI (e.g., database IDs, timestamps, processing state) |
| `extraction_timestamp` | date | No | No | System/internal field - not exposed in UI (e.g., database IDs, timestamps, processing state) |
| `fa_approval_date` | date | No | No | System/internal field - not exposed in UI (e.g., database IDs, timestamps, processing state) |
| `fa_approval_notes` | string, null | No | No | System/internal field - not exposed in UI (e.g., database IDs, timestamps, processing state) |
| `fa_approver` | string, null | No | No | System/internal field - not exposed in UI (e.g., database IDs, timestamps, processing state) |
| `field_confidence` | object | No | No | System/internal field - not exposed in UI (e.g., database IDs, timestamps, processing state) |
| `file_name` | string | Yes | No | System/internal field - not exposed in UI (e.g., database IDs, timestamps, processing state) |
| `file_path` | string | Yes | No | System/internal field - not exposed in UI (e.g., database IDs, timestamps, processing state) |
| `id` | string, null | No | No | System/internal field - not exposed in UI (e.g., database IDs, timestamps, processing state) |
| `processing_state` | string | No | No | System/internal field - not exposed in UI (e.g., database IDs, timestamps, processing state) |
| `review_notes` | string, null | No | No | System/internal field - not exposed in UI (e.g., database IDs, timestamps, processing state) |
| `review_status` | string, null | No | No | System/internal field - not exposed in UI (e.g., database IDs, timestamps, processing state) |
| `review_timestamp` | date | No | No | System/internal field - not exposed in UI (e.g., database IDs, timestamps, processing state) |
| `review_version` | integer | No | No | System/internal field - not exposed in UI (e.g., database IDs, timestamps, processing state) |
| `reviewer` | string, null | No | No | System/internal field - not exposed in UI (e.g., database IDs, timestamps, processing state) |
| `status` | string | Yes | No | System/internal field - not exposed in UI (e.g., database IDs, timestamps, processing state) |
| `updated_at` | date | No | No | System/internal field - not exposed in UI (e.g., database IDs, timestamps, processing state) |
| `upload_date` | date | Yes | No | System/internal field - not exposed in UI (e.g., database IDs, timestamps, processing state) |

### Tax Registration

| Field Name | Type | Required | In UI? | Reason/Notes |
|------------|------|----------|--------|--------------|
| `business_number` | string, null | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |
| `gst_number` | string, null | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |
| `pst_number` | string, null | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |
| `qst_number` | string, null | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |
| `tax_registration_number` | string, null | No | Yes | ✓ Displayed in UI schema form |

### Vendor Information

| Field Name | Type | Required | In UI? | Reason/Notes |
|------------|------|----------|--------|--------------|
| `vendor_address` | address_object | No | Yes | ✓ Displayed in UI schema form |
| `vendor_address.city` | string, null | No | No | Nested field within 'vendor_address' object - address fields are displayed as structured objects in UI |
| `vendor_address.country` | string, null | No | No | Nested field within 'vendor_address' object - address fields are displayed as structured objects in UI |
| `vendor_address.postal_code` | string, null | No | No | Nested field within 'vendor_address' object - address fields are displayed as structured objects in UI |
| `vendor_address.province` | string, null | No | No | Nested field within 'vendor_address' object - address fields are displayed as structured objects in UI |
| `vendor_address.street` | string, null | No | No | Nested field within 'vendor_address' object - address fields are displayed as structured objects in UI |
| `vendor_email` | string, null | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |
| `vendor_fax` | string, null | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |
| `vendor_id` | string, null | No | Yes | ✓ Displayed in UI schema form |
| `vendor_name` | string, null | No | Yes | ✓ Displayed in UI schema form |
| `vendor_phone` | string, null | No | Yes | ✓ Displayed in UI schema form |
| `vendor_website` | string, null | No | No | Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically |

## Notes

### Fields Handled Separately

1. **Line Items**: The `line_items` array and all sub-fields are displayed in a separate
   `LineItemGrid` component, not in the main schema form. This provides a better
   user experience for tabular data.

2. **Address Fields**: Address objects (vendor_address, bill_to_address, remit_to_address)
   are displayed as structured objects in the UI. Individual address components
   (street, city, province, postal_code, country) are nested within these objects.

3. **System Fields**: Fields marked as 'System' are internal to the application and
   are not exposed in the UI for user editing. These include:
   - Database identifiers (id)
   - File metadata (file_path, file_name, upload_date)
   - Processing state (status, processing_state)
   - Extraction metadata (extraction_confidence, field_confidence, extraction_timestamp)
   - Review metadata (review_status, reviewer, review_timestamp, review_notes, review_version)
   - Approval metadata (bv_approver, fa_approver, approval dates/notes)
   - Timestamps (created_at, updated_at)

4. **Extensions**: The `extensions` field contains subtype-specific data (shift service,
   per diem travel, timesheet data) that is handled dynamically based on the
   invoice_subtype value.

### Missing UI Fields Analysis

The following fields from non-system categories are not currently in the UI schema form:

- **business_number** (Tax Registration): Canadian Business Number (BN)
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically

- **customer_email** (Customer Information): Customer email address
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically

- **customer_fax** (Customer Information): Customer fax number
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically

- **customer_phone** (Customer Information): Customer phone number
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically

- **delivery_date** (Invoice Header): Date when goods/services were delivered
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically

- **deposit_amount** (Amounts & Totals): Deposit or prepayment amount
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically

- **discount_amount** (Amounts & Totals): Total discount applied
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically

- **entity** (Contract/PO): 
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically

- **gst_amount** (Amounts & Totals): GST (Goods and Services Tax) amount
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically

- **gst_number** (Tax Registration): GST Registration Number
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically

- **gst_rate** (Amounts & Totals): GST rate as decimal (e.g., 0.05 for 5%)
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically

- **handling_fee** (Amounts & Totals): Handling or processing fee
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically

- **hst_amount** (Amounts & Totals): HST (Harmonized Sales Tax) amount
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically

- **hst_rate** (Amounts & Totals): HST rate as decimal (e.g., 0.13 for 13%)
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically

- **invoice_subtype** (Invoice Header): 
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically

- **invoice_type** (Invoice Header): Type of invoice (e.g., Standard, Credit Note, Debit Note)
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically

- **payment_due_upon** (Invoice Header): Payment due condition (e.g., Receipt, Net 30, End of Month)
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically

- **payment_method** (Invoice Header): Payment method (e.g., Check, Wire Transfer, Credit Card)
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically

- **pst_amount** (Amounts & Totals): PST (Provincial Sales Tax) amount
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically

- **pst_number** (Tax Registration): PST Registration Number (Provincial)
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically

- **pst_rate** (Amounts & Totals): PST rate as decimal (e.g., 0.07 for 7%)
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically

- **qst_amount** (Amounts & Totals): QST (Quebec Sales Tax) amount
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically

- **qst_number** (Tax Registration): QST Registration Number (Quebec)
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically

- **qst_rate** (Amounts & Totals): QST rate as decimal (e.g., 0.09975 for 9.975%)
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically

- **reference_number** (Invoice Header): Additional reference or tracking number
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically

- **shipping_amount** (Amounts & Totals): Shipping and freight charges
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically

- **shipping_date** (Invoice Header): Date when goods/services were shipped
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically

- **tax_breakdown** (Amounts & Totals): 
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically

- **vendor_email** (Vendor Information): Vendor email address
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically

- **vendor_fax** (Vendor Information): Vendor fax number
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically

- **vendor_website** (Vendor Information): Vendor website URL
  - Reason: Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically
