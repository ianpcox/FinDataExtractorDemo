# UI Fields Reconciliation with Azure Document Intelligence OCR

This document reconciles fields displayed in the Streamlit UI with fields
that can be extracted from Azure Document Intelligence prebuilt-invoice OCR.

## Azure Document Intelligence Model Confirmation

✅ **Model Used**: `prebuilt-invoice`

The codebase uses Azure Document Intelligence's `prebuilt-invoice` model,
which is specifically designed for invoice extraction. This is confirmed in:
- `src/config.py`: `AZURE_FORM_RECOGNIZER_MODEL = "prebuilt-invoice"` (default)
- `src/extraction/document_intelligence_client.py`: Uses `prebuilt-invoice` model

## Summary

- **Fields in Streamlit UI**: 51
- **Fields mapped from DI OCR (in field_extractor.py)**: 51 ✅
- **Fields in Contract Schema**: 24 ⚠️
- **Fields in UI NOT mapped from DI**: 0
- **Fields in Contract but NOT in UI**: 0

### Key Finding

✅ **ALL 51 fields displayed in the Streamlit UI are mapped from Azure Document Intelligence OCR** in `field_extractor.py`.

⚠️ **The contract schema (`invoice.contract.v1.json`) is incomplete** - it only defines 24 fields, but the actual `FieldExtractor` class has DI mappings for all 51 fields.

This means:
- All UI fields CAN be extracted from DI OCR
- The contract schema needs to be updated to include all DI mappings
- The `invoice_ui_fields.csv` (generated from contract schema) is also incomplete

## Fields in UI with DI OCR Mapping

All fields displayed in the UI are mapped from DI OCR:

### Header Fields

- ✅ `invoice_number` ← `InvoiceId`
- ✅ `invoice_date` ← `InvoiceDate`
- ✅ `due_date` ← `DueDate`
- ✅ `invoice_type` ← `InvoiceType`
- ✅ `reference_number` ← `ReferenceNumber`
- ✅ `po_number` ← `PurchaseOrder`, `PONumber`
- ✅ `standing_offer_number` ← `StandingOfferNumber`
- ✅ `contract_id` ← `ContractId`
- ✅ `entity` ← `Entity`

### Vendor Fields

- ✅ `vendor_name` ← `VendorName`
- ✅ `vendor_id` ← `VendorId`
- ✅ `vendor_phone` ← `VendorPhoneNumber`, `VendorPhone`
- ✅ `vendor_fax` ← `VendorFax`, `VendorFaxNumber`
- ✅ `vendor_email` ← `VendorEmail`
- ✅ `vendor_website` ← `VendorWebsite`

### Vendor Tax Fields

- ✅ `business_number` ← `BusinessNumber`
- ✅ `gst_number` ← `GSTNumber`
- ✅ `qst_number` ← `QSTNumber`
- ✅ `pst_number` ← `PSTNumber`
- ✅ `tax_registration_number` ← `TaxRegistrationNumber`, `SalesTaxNumber`

### Customer Fields

- ✅ `customer_name` ← `CustomerName`
- ✅ `customer_id` ← `CustomerId`
- ✅ `customer_phone` ← `CustomerPhone`
- ✅ `customer_email` ← `CustomerEmail`
- ✅ `customer_fax` ← `CustomerFax`

### Remit-To Fields

- ✅ `remit_to_name` ← `RemitToName`

### Address Fields

- ✅ `vendor_address` ← `VendorAddress`
- ✅ `bill_to_address` ← `CustomerAddress`, `BillToAddress`
- ✅ `remit_to_address` ← `RemitToAddress`, `RemittanceAddress`

### Financial Fields

- ✅ `subtotal` ← `SubTotal`
- ✅ `discount_amount` ← `DiscountAmount`
- ✅ `shipping_amount` ← `ShippingAmount`
- ✅ `handling_fee` ← `HandlingFee`
- ✅ `deposit_amount` ← `DepositAmount`
- ✅ `tax_amount` ← `TotalTax`
- ✅ `total_amount` ← `InvoiceTotal`
- ✅ `currency` ← `CurrencyCode`, `Currency`

### Canadian Tax Amounts/Rates

- ✅ `gst_amount` ← `GSTAmount`
- ✅ `gst_rate` ← `GSTRate`
- ✅ `hst_amount` ← `HSTAmount`
- ✅ `hst_rate` ← `HSTRate`
- ✅ `qst_amount` ← `QSTAmount`
- ✅ `qst_rate` ← `QSTRate`
- ✅ `pst_amount` ← `PSTAmount`
- ✅ `pst_rate` ← `PSTRate`

### Payment Fields

- ✅ `payment_terms` ← `PaymentTerm`, `PaymentTerms`
- ✅ `payment_method` ← `PaymentMethod`
- ✅ `payment_due_upon` ← `PaymentDueUpon`
- ✅ `acceptance_percentage` ← `AcceptancePercentage`

### Period Fields

- ✅ `period_start` ← `ServiceStartDate`
- ✅ `period_end` ← `ServiceEndDate`

## ⚠️ Contract Schema is Out of Sync

The **contract schema (`invoice.contract.v1.json`) is incomplete**:

- **Contract schema has**: 24 fields
- **FieldExtractor has**: 51 fields (all UI fields)
- **Missing from contract**: 27 fields

The missing fields in the contract schema include:
- Financial adjustment fields: `discount_amount`, `shipping_amount`, `handling_fee`, `deposit_amount`
- Canadian tax amounts/rates: `gst_amount`, `gst_rate`, `hst_amount`, `hst_rate`, `qst_amount`, `qst_rate`, `pst_amount`, `pst_rate`
- Payment fields: `payment_method`, `payment_due_upon`
- And other fields displayed in the UI

## Recommendations

1. **Verify Azure DI Capabilities**: While all fields are mapped in code, verify with Azure Document Intelligence documentation that the `prebuilt-invoice` model actually supports all these fields. Some fields may be available but not always populated in all invoices.

2. **Update Contract Schema**: The `invoice.contract.v1.json` file needs to be updated to include all 51 fields that are:
   - Displayed in the UI
   - Mapped from DI OCR in `field_extractor.py`
   - Should be part of the contract definition

3. **Update DI Mappings in Contract**: Add the missing DI field mappings to the `di_to_canonical` section of the contract schema. The mappings should match what's in `field_extractor.py` (`DI_TO_CANONICAL` dictionary).

4. **Regenerate UI Fields CSV**: After updating the contract schema, regenerate `invoice_ui_fields.csv` to include all 51 fields.

5. **Keep FieldExtractor as Source of Truth**: The `field_extractor.py` appears to be the most complete source of DI mappings. The contract schema should be updated to match it.
