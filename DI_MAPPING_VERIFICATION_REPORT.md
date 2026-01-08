# DI_TO_CANONICAL Mapping Verification Report

**Generated:** 2026-01-07  
**Purpose:** Verify that all DI field mappings are correct and complete

---

## Executive Summary

The `DI_TO_CANONICAL` mapping in `FieldExtractor` has been verified against:
1. The `Invoice` model (canonical fields)
2. The `DocumentIntelligenceClient._extract_invoice_fields()` method
3. All extractable DI fields

**Result:** All mappings are **CORRECT and COMPLETE** for extractable fields.

---

## Mapping Statistics

- **Total DI Field Mappings:** 60
- **Unique Canonical Targets:** 52
- **Canonical Fields in Invoice Model:** 63
- **Extractable Canonical Fields (from DI):** 52
- **Review/Metadata Fields (not from DI):** 11

---

## Verification Results

### 1. DI_TO_CANONICAL Mapping Completeness

**Status:** COMPLETE

All 52 extractable canonical fields have DI mappings:
- Header Fields: 5/5 mapped
- Vendor Fields: 7/7 mapped
- Vendor Tax ID Fields: 4/4 mapped
- Customer Fields: 6/6 mapped
- Remit-To Fields: 2/2 mapped
- Contract Fields: 4/4 mapped
- Date Fields: 4/4 mapped
- Financial Fields: 5/5 mapped
- Canadian Tax Fields: 8/8 mapped
- Total Fields: 3/3 mapped
- Payment Fields: 4/4 mapped

**Total:** 52/52 extractable fields mapped (100%)

### 2. Invoice Model Field Coverage

**Status:** CORRECT

- **Extractable Fields:** 52 fields - all have DI mappings
- **Review/Metadata Fields:** 11 fields - correctly NOT mapped (not from DI):
  - `bv_approval_date`, `bv_approval_notes`, `bv_approver`
  - `fa_approval_date`, `fa_approval_notes`, `fa_approver`
  - `review_notes`, `review_status`, `review_timestamp`, `reviewer`
  - `extraction_timestamp`

These fields are added during the review/approval process, not extracted from DI.

### 3. DocumentIntelligenceClient Extraction Coverage

**Status:** COMPLETE

All 52 extractable canonical fields are now being extracted in `_extract_invoice_fields()`:
- All fields from `DI_TO_CANONICAL` are extracted
- Multiple DI field name variants are handled (e.g., `PaymentTerm`/`PaymentTerms`)
- Address fields use `_get_address()` helper method
- Line items are extracted via `_extract_items()` method

### 4. Multiple DI Field Name Support

**Status:** CORRECT

The following canonical fields correctly support multiple DI field names:

| Canonical Field | DI Field Names |
|----------------|---------------|
| `bill_to_address` | `CustomerAddress`, `BillToAddress` |
| `currency` | `CurrencyCode`, `Currency` |
| `payment_terms` | `PaymentTerm`, `PaymentTerms` |
| `po_number` | `PurchaseOrder`, `PONumber` |
| `remit_to_address` | `RemitToAddress`, `RemittanceAddress` |
| `tax_registration_number` | `TaxRegistrationNumber`, `SalesTaxNumber` |
| `vendor_fax` | `VendorFax`, `VendorFaxNumber` |
| `vendor_phone` | `VendorPhoneNumber`, `VendorPhone` |

This is correctly implemented in both:
- `DI_TO_CANONICAL` mapping (both names map to same canonical field)
- `DocumentIntelligenceClient._extract_invoice_fields()` (checks both names with `or`)

---

## Field-by-Field Verification

### Header Fields (5 fields)

| Canonical Field | DI Field Name(s) | Mapping | Extraction | Status |
|----------------|------------------|---------|------------|--------|
| `invoice_number` | `InvoiceId` | Yes | Yes | OK |
| `invoice_date` | `InvoiceDate` | Yes | Yes | OK |
| `due_date` | `DueDate` | Yes | Yes | OK |
| `invoice_type` | `InvoiceType` | Yes | Yes | OK |
| `reference_number` | `ReferenceNumber` | Yes | Yes | OK |

### Vendor Fields (7 fields)

| Canonical Field | DI Field Name(s) | Mapping | Extraction | Status |
|----------------|------------------|---------|------------|--------|
| `vendor_name` | `VendorName` | Yes | Yes | OK |
| `vendor_id` | `VendorId` | Yes | Yes | OK |
| `vendor_phone` | `VendorPhoneNumber`, `VendorPhone` | Yes | Yes | OK |
| `vendor_fax` | `VendorFax`, `VendorFaxNumber` | Yes | Yes | OK |
| `vendor_email` | `VendorEmail` | Yes | Yes | OK |
| `vendor_website` | `VendorWebsite` | Yes | Yes | OK |
| `vendor_address` | `VendorAddress` | Yes | Yes | OK |

### Vendor Tax ID Fields (4 fields)

| Canonical Field | DI Field Name(s) | Mapping | Extraction | Status |
|----------------|------------------|---------|------------|--------|
| `business_number` | `BusinessNumber` | Yes | Yes | OK |
| `gst_number` | `GSTNumber` | Yes | Yes | OK |
| `qst_number` | `QSTNumber` | Yes | Yes | OK |
| `pst_number` | `PSTNumber` | Yes | Yes | OK |

### Customer Fields (6 fields)

| Canonical Field | DI Field Name(s) | Mapping | Extraction | Status |
|----------------|------------------|---------|------------|--------|
| `customer_name` | `CustomerName` | Yes | Yes | OK |
| `customer_id` | `CustomerId` | Yes | Yes | OK |
| `customer_phone` | `CustomerPhone` | Yes | Yes | OK |
| `customer_email` | `CustomerEmail` | Yes | Yes | OK |
| `customer_fax` | `CustomerFax` | Yes | Yes | OK |
| `bill_to_address` | `CustomerAddress`, `BillToAddress` | Yes | Yes | OK |

### Remit-To Fields (2 fields)

| Canonical Field | DI Field Name(s) | Mapping | Extraction | Status |
|----------------|------------------|---------|------------|--------|
| `remit_to_address` | `RemitToAddress`, `RemittanceAddress` | Yes | Yes | OK |
| `remit_to_name` | `RemitToName` | Yes | Yes | OK |

### Contract Fields (4 fields)

| Canonical Field | DI Field Name(s) | Mapping | Extraction | Status |
|----------------|------------------|---------|------------|--------|
| `entity` | `Entity` | Yes | Yes | OK |
| `contract_id` | `ContractId` | Yes | Yes | OK |
| `standing_offer_number` | `StandingOfferNumber` | Yes | Yes | OK |
| `po_number` | `PurchaseOrder`, `PONumber` | Yes | Yes | OK |

### Date Fields (4 fields)

| Canonical Field | DI Field Name(s) | Mapping | Extraction | Status |
|----------------|------------------|---------|------------|--------|
| `period_start` | `ServiceStartDate` | Yes | Yes | OK |
| `period_end` | `ServiceEndDate` | Yes | Yes | OK |
| `shipping_date` | `ShippingDate` | Yes | Yes | OK |
| `delivery_date` | `DeliveryDate` | Yes | Yes | OK |

### Financial Fields (5 fields)

| Canonical Field | DI Field Name(s) | Mapping | Extraction | Status |
|----------------|------------------|---------|------------|--------|
| `subtotal` | `SubTotal` | Yes | Yes | OK |
| `discount_amount` | `DiscountAmount` | Yes | Yes | OK |
| `shipping_amount` | `ShippingAmount` | Yes | Yes | OK |
| `handling_fee` | `HandlingFee` | Yes | Yes | OK |
| `deposit_amount` | `DepositAmount` | Yes | Yes | OK |

### Canadian Tax Fields (8 fields)

| Canonical Field | DI Field Name(s) | Mapping | Extraction | Status |
|----------------|------------------|---------|------------|--------|
| `gst_amount` | `GSTAmount` | Yes | Yes | OK |
| `gst_rate` | `GSTRate` | Yes | Yes | OK |
| `hst_amount` | `HSTAmount` | Yes | Yes | OK |
| `hst_rate` | `HSTRate` | Yes | Yes | OK |
| `qst_amount` | `QSTAmount` | Yes | Yes | OK |
| `qst_rate` | `QSTRate` | Yes | Yes | OK |
| `pst_amount` | `PSTAmount` | Yes | Yes | OK |
| `pst_rate` | `PSTRate` | Yes | Yes | OK |

### Total Fields (3 fields)

| Canonical Field | DI Field Name(s) | Mapping | Extraction | Status |
|----------------|------------------|---------|------------|--------|
| `tax_amount` | `TotalTax` | Yes | Yes | OK |
| `total_amount` | `InvoiceTotal` | Yes | Yes | OK |
| `currency` | `CurrencyCode`, `Currency` | Yes | Yes | OK |

### Payment Fields (4 fields)

| Canonical Field | DI Field Name(s) | Mapping | Extraction | Status |
|----------------|------------------|---------|------------|--------|
| `payment_terms` | `PaymentTerm`, `PaymentTerms` | Yes | Yes | OK |
| `payment_method` | `PaymentMethod` | Yes | Yes | OK |
| `payment_due_upon` | `PaymentDueUpon` | Yes | Yes | OK |
| `tax_registration_number` | `TaxRegistrationNumber`, `SalesTaxNumber` | Yes | Yes | OK |

---

## Expected Non-Mapped Fields

The following fields are in the Invoice model but correctly do NOT have DI mappings because they are not extracted from Document Intelligence:

### Review/Approval Metadata Fields (11 fields)

These fields are added during the HITL review process, not from DI extraction:

1. `bv_approval_date` - Business validation approval date
2. `bv_approval_notes` - Business validation approval notes
3. `bv_approver` - Business validation approver name
4. `fa_approval_date` - Financial approval date
5. `fa_approval_notes` - Financial approval notes
6. `fa_approver` - Financial approver name
7. `review_notes` - General review notes
8. `review_status` - Review status (approved/rejected/pending)
9. `review_timestamp` - Review timestamp
10. `reviewer` - Reviewer name
11. `extraction_timestamp` - Extraction timestamp (system-generated)

**Status:** CORRECT - These should NOT have DI mappings.

---

## Nested Structures

The following fields are extracted but are nested structures, not top-level canonical fields:

### Address Sub-Fields
- `street_address`, `city`, `state`, `postal_code`, `country_region`, `house_number`, `road`
- These are extracted via `_get_address()` and mapped to `Address` objects

### Line Item Sub-Fields
- `amount`, `date`, `description`, `product_code`, `quantity`, `tax`, `unit`, `unit_price`
- These are extracted via `_extract_items()` and mapped to `LineItem` objects

**Status:** CORRECT - These are properly handled as nested structures.

---

## Conclusion

**All DI_TO_CANONICAL mappings are VERIFIED and CORRECT:**

1. All 52 extractable canonical fields have proper DI mappings
2. All DI mapping targets exist in the Invoice model
3. All mapped fields are being extracted in `DocumentIntelligenceClient._extract_invoice_fields()`
4. Multiple DI field name variants are correctly supported
5. Review/metadata fields correctly do NOT have DI mappings
6. Nested structures (addresses, line items) are correctly handled

**No changes needed** - the mappings are complete and accurate.

---

## Recommendations

1. **Documentation:** The mappings are correct, but consider adding inline documentation explaining:
   - Why certain fields have multiple DI name mappings
   - Which fields are not from DI (review metadata)
   - How nested structures are handled

2. **Testing:** With the updated `_extract_invoice_fields()` method, DI OCR test coverage should improve significantly. Re-run tests to verify.

3. **Maintenance:** When adding new canonical fields:
   - If extractable from DI: Add to both `DI_TO_CANONICAL` and `_extract_invoice_fields()`
   - If review metadata: Do NOT add to `DI_TO_CANONICAL`

---

**Report End**

