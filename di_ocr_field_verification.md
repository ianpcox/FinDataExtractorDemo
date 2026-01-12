# Azure Document Intelligence Prebuilt-Invoice Field Verification

This document compares the DI fields mapped in both DEMO and VANILLA projects with
the capabilities of Azure Document Intelligence's prebuilt-invoice model.

## Model Confirmation

✅ **Azure Document Intelligence Model**: `prebuilt-invoice`

Both projects use Azure Document Intelligence's `prebuilt-invoice` model, which is
specifically designed for invoice extraction.

## Important Notes

⚠️ **Documentation Limitations**: The official Azure documentation lists core fields,
but the API may return additional fields that are not explicitly documented. This is
common with Azure services where the API evolves faster than documentation.

✅ **Code Handles Missing Fields Gracefully**: The codebase uses `.get()` methods and
null-safe checks, so fields that are not present in the DI response are handled
appropriately without errors.

📋 **Field Availability Varies**: Field extraction depends on:
- Invoice format and structure
- Language/locale of the invoice
- Model version
- Whether the field is present and clearly labeled in the invoice

## Core Fields (Officially Documented)

These fields are consistently documented and supported by the prebuilt-invoice model:

- `InvoiceId` → `invoice_number`
- `InvoiceDate` → `invoice_date`
- `DueDate` → `due_date`
- `InvoiceTotal` → `total_amount`
- `SubTotal` → `subtotal`
- `TotalTax` → `tax_amount`
- `VendorName` → `vendor_name`
- `VendorAddress` → `vendor_address`
- `CustomerName` → `customer_name`
- `CustomerId` → `customer_id`
- `CustomerAddress` → `bill_to_address`
- `PurchaseOrder` → `po_number`
- `PaymentTerm` → `payment_terms`
- `CurrencyCode` → `currency`
- `ServiceStartDate` → `period_start`
- `ServiceEndDate` → `period_end`
- `RemittanceAddress` → `remit_to_address`

## Extended Fields (May Be Available)

Based on web search and codebase analysis, many additional fields may be available
but are not consistently documented. These include:

### Vendor Contact Fields
- `VendorId`, `VendorPhone`, `VendorPhoneNumber`, `VendorFax`, `VendorFaxNumber`
- `VendorEmail`, `VendorWebsite`

### Customer Contact Fields
- `CustomerPhone`, `CustomerEmail`, `CustomerFax`

### Tax Registration Fields (Canadian-specific)
- `BusinessNumber`, `GSTNumber`, `QSTNumber`, `PSTNumber`
- `TaxRegistrationNumber`, `SalesTaxNumber`

### Tax Amount/Rate Fields (Canadian-specific)
- `GSTAmount`, `GSTRate`, `HSTAmount`, `HSTRate`
- `QSTAmount`, `QSTRate`, `PSTAmount`, `PSTRate`

### Financial Adjustment Fields
- `DiscountAmount`, `ShippingAmount`, `HandlingFee`, `DepositAmount`

### Payment Fields
- `PaymentMethod`, `PaymentDueUpon`, `PaymentTerms` (variant of PaymentTerm)

### Other Fields
- `InvoiceType`, `ReferenceNumber`, `ShippingDate`, `DeliveryDate`
- `Entity`, `ContractId`, `StandingOfferNumber`, `RemitToName`
- `BillToAddress`, `AcceptancePercentage`

## Verification Results

### DEMO Project
- **Total DI fields mapped**: 60
- **Core documented fields**: 17
- **Extended fields mapped**: 43

### VANILLA Project
- **Total DI fields mapped**: 61
- **Core documented fields**: 17
- **Extended fields mapped**: 44

## Recommendations

1. **Test with Real Invoices**: 
   - Run actual invoices through Azure DI
   - Inspect the API responses to see which fields are actually returned
   - Test with various invoice formats (PDF, images) and languages

2. **Monitor Field Availability**:
   - Check Azure DI release notes for new fields
   - Fields may be added in newer model versions
   - Some fields may be locale-specific (e.g., Canadian tax fields)

3. **Handle Missing Fields Gracefully** (✅ Already Implemented):
   - The code already uses `.get()` methods and null checks
   - Missing fields result in `None` values, which is handled correctly
   - No errors occur when fields are not present

4. **Consider Query Fields** (Azure DI Feature):
   - Azure DI supports "Query Fields" to extract additional custom fields
   - This could be used if specific fields are consistently needed but not available

5. **Document Field Reliability**:
   - Keep track of which fields are consistently populated
   - Document which fields are rarely/never populated in your invoices
   - Consider marking fields as "optional" or "low confidence" in the UI

6. **Verify Canadian Tax Fields**:
   - Many Canadian-specific tax fields (GST, HST, QST, PST) are mapped
   - These may be available for Canadian invoices but not documented
   - Test specifically with Canadian invoices to verify availability

## Conclusion

✅ **Code is Safe**: The codebase correctly handles missing fields using null-safe
operations, so even if some mapped fields are not available from DI OCR, the code
will not fail.

⚠️ **Field Availability Unknown**: Without testing actual invoices, we cannot be
certain which of the 60+ mapped fields are actually returned by Azure DI for your
specific invoices.

📋 **Action Required**: 
1. Test with sample invoices to verify which fields are actually returned
2. Document which fields are consistently available vs. rarely available
3. Consider removing or marking fields that are never populated
