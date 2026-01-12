#!/usr/bin/env python3
"""Reconcile Streamlit UI fields with Azure Document Intelligence OCR capabilities"""

import json
import csv
from pathlib import Path
from typing import Set, Dict, List

DEMO_ROOT = Path(__file__).parent.parent
CONTRACT_JSON = DEMO_ROOT / "schemas" / "invoice.contract.v1.json"
FIELD_EXTRACTOR = DEMO_ROOT / "src" / "extraction" / "field_extractor.py"
OUTPUT_FILE = DEMO_ROOT / "ui_di_ocr_reconciliation.md"

# Fields actually displayed in Streamlit UI (from analysis)
STREAMLIT_UI_FIELDS = {
    # Header fields (Tab 1)
    "invoice_number", "invoice_date", "due_date", "invoice_type", "reference_number",
    "po_number", "standing_offer_number", "contract_id", "entity",
    
    # Vendor fields (Tab 1)
    "vendor_name", "vendor_id", "vendor_phone", "vendor_fax", "vendor_email", "vendor_website",
    
    # Vendor tax fields (Tab 1)
    "business_number", "gst_number", "qst_number", "pst_number", "tax_registration_number",
    
    # Customer fields (Tab 1)
    "customer_name", "customer_id", "customer_phone", "customer_email", "customer_fax",
    
    # Remit-to fields (Tab 1)
    "remit_to_name",
    
    # Address fields (Tab 5)
    "vendor_address", "bill_to_address", "remit_to_address",
    
    # Financial fields (Tab 2)
    "subtotal", "discount_amount", "shipping_amount", "handling_fee", "deposit_amount",
    "tax_amount", "total_amount", "currency",
    
    # Canadian tax amounts and rates (Tab 2)
    "gst_amount", "gst_rate", "hst_amount", "hst_rate",
    "qst_amount", "qst_rate", "pst_amount", "pst_rate",
    
    # Payment fields (Tab 3)
    "payment_terms", "payment_method", "payment_due_upon", "acceptance_percentage",
    
    # Period fields (Tab 3)
    "period_start", "period_end",
}

# DI fields mapped in FieldExtractor (from field_extractor.py DI_TO_CANONICAL - ACTUAL mappings)
DI_FIELDS_MAPPED = {
    "InvoiceId": "invoice_number",
    "InvoiceDate": "invoice_date",
    "InvoiceType": "invoice_type",
    "ReferenceNumber": "reference_number",
    "DueDate": "due_date",
    "ShippingDate": "shipping_date",
    "DeliveryDate": "delivery_date",
    "VendorName": "vendor_name",
    "VendorId": "vendor_id",
    "VendorPhoneNumber": "vendor_phone",
    "VendorPhone": "vendor_phone",
    "VendorFax": "vendor_fax",
    "VendorFaxNumber": "vendor_fax",
    "VendorEmail": "vendor_email",
    "VendorWebsite": "vendor_website",
    "VendorAddress": "vendor_address",
    "BusinessNumber": "business_number",
    "GSTNumber": "gst_number",
    "QSTNumber": "qst_number",
    "PSTNumber": "pst_number",
    "CustomerName": "customer_name",
    "CustomerId": "customer_id",
    "CustomerPhone": "customer_phone",
    "CustomerEmail": "customer_email",
    "CustomerFax": "customer_fax",
    "CustomerAddress": "bill_to_address",
    "BillToAddress": "bill_to_address",
    "RemitToAddress": "remit_to_address",
    "RemittanceAddress": "remit_to_address",
    "RemitToName": "remit_to_name",
    "Entity": "entity",
    "ContractId": "contract_id",
    "StandingOfferNumber": "standing_offer_number",
    "PurchaseOrder": "po_number",
    "PONumber": "po_number",
    "ServiceStartDate": "period_start",
    "ServiceEndDate": "period_end",
    "SubTotal": "subtotal",
    "DiscountAmount": "discount_amount",
    "ShippingAmount": "shipping_amount",
    "HandlingFee": "handling_fee",
    "DepositAmount": "deposit_amount",
    "GSTAmount": "gst_amount",
    "GSTRate": "gst_rate",
    "HSTAmount": "hst_amount",
    "HSTRate": "hst_rate",
    "QSTAmount": "qst_amount",
    "QSTRate": "qst_rate",
    "PSTAmount": "pst_amount",
    "PSTRate": "pst_rate",
    "TotalTax": "tax_amount",
    "InvoiceTotal": "total_amount",
    "CurrencyCode": "currency",
    "Currency": "currency",
    "PaymentTerm": "payment_terms",
    "PaymentTerms": "payment_terms",
    "PaymentMethod": "payment_method",
    "PaymentDueUpon": "payment_due_upon",
    "AcceptancePercentage": "acceptance_percentage",
    "TaxRegistrationNumber": "tax_registration_number",
    "SalesTaxNumber": "tax_registration_number",
}

# Reverse mapping: canonical -> DI fields
CANONICAL_TO_DI = {}
for di_field, canonical_field in DI_FIELDS_MAPPED.items():
    if canonical_field not in CANONICAL_TO_DI:
        CANONICAL_TO_DI[canonical_field] = []
    CANONICAL_TO_DI[canonical_field].append(di_field)

def load_contract_fields():
    """Load fields from contract schema"""
    with open(CONTRACT_JSON, "r", encoding="utf-8") as f:
        contract = json.load(f)
    return set(contract.get("fields", {}).keys())

def get_di_fields_for_canonical(canonical_field: str) -> List[str]:
    """Get DI field names that map to a canonical field"""
    return CANONICAL_TO_DI.get(canonical_field, [])

def generate_reconciliation():
    """Generate reconciliation analysis"""
    contract_fields = load_contract_fields()
    
    # Fields in UI but not mapped from DI
    ui_fields_not_from_di = STREAMLIT_UI_FIELDS - set(CANONICAL_TO_DI.keys())
    
    # Fields in UI that ARE mapped from DI
    ui_fields_from_di = STREAMLIT_UI_FIELDS & set(CANONICAL_TO_DI.keys())
    
    # Fields in contract but not in UI
    contract_not_in_ui = contract_fields - STREAMLIT_UI_FIELDS
    
    # Generate report
    report_lines = []
    report_lines.append("# UI Fields Reconciliation with Azure Document Intelligence OCR")
    report_lines.append("")
    report_lines.append("This document reconciles fields displayed in the Streamlit UI with fields")
    report_lines.append("that can be extracted from Azure Document Intelligence prebuilt-invoice OCR.")
    report_lines.append("")
    
    report_lines.append("## Azure Document Intelligence Model Confirmation")
    report_lines.append("")
    report_lines.append("✅ **Model Used**: `prebuilt-invoice`")
    report_lines.append("")
    report_lines.append("The codebase uses Azure Document Intelligence's `prebuilt-invoice` model,")
    report_lines.append("which is specifically designed for invoice extraction.")
    report_lines.append("")
    
    report_lines.append("## Summary")
    report_lines.append("")
    report_lines.append(f"- **Fields in Streamlit UI**: {len(STREAMLIT_UI_FIELDS)}")
    report_lines.append(f"- **Fields mapped from DI OCR**: {len(ui_fields_from_di)}")
    report_lines.append(f"- **Fields in UI NOT mapped from DI**: {len(ui_fields_not_from_di)}")
    report_lines.append(f"- **Fields in Contract but NOT in UI**: {len(contract_not_in_ui)}")
    report_lines.append("")
    
    report_lines.append("## Fields in UI with DI OCR Mapping")
    report_lines.append("")
    report_lines.append("These fields are displayed in the UI and can be extracted from DI OCR:")
    report_lines.append("")
    
    # Group by category
    categories = {
        "Header Fields": ["invoice_number", "invoice_date", "due_date", "invoice_type", "reference_number",
                          "po_number", "standing_offer_number", "contract_id", "entity"],
        "Vendor Fields": ["vendor_name", "vendor_id", "vendor_phone", "vendor_fax", "vendor_email", "vendor_website"],
        "Vendor Tax Fields": ["business_number", "gst_number", "qst_number", "pst_number", "tax_registration_number"],
        "Customer Fields": ["customer_name", "customer_id", "customer_phone", "customer_email", "customer_fax"],
        "Remit-To Fields": ["remit_to_name"],
        "Address Fields": ["vendor_address", "bill_to_address", "remit_to_address"],
        "Financial Fields": ["subtotal", "tax_amount", "total_amount", "currency"],
        "Payment Fields": ["payment_terms", "acceptance_percentage"],
        "Period Fields": ["period_start", "period_end"],
    }
    
    for category, fields_list in categories.items():
        report_lines.append(f"### {category}")
        report_lines.append("")
        for field in fields_list:
            if field in ui_fields_from_di:
                di_fields = get_di_fields_for_canonical(field)
                di_field_str = ", ".join([f"`{df}`" for df in di_fields])
                report_lines.append(f"- ✅ `{field}` ← {di_field_str}")
            elif field in STREAMLIT_UI_FIELDS:
                report_lines.append(f"- ⚠️ `{field}` ← **NOT mapped from DI OCR**")
        report_lines.append("")
    
    # Fields NOT mapped from DI
    report_lines.append("## ⚠️ Fields in UI NOT Mapped from DI OCR")
    report_lines.append("")
    report_lines.append("These fields are displayed in the Streamlit UI but are **NOT** mapped")
    report_lines.append("from Azure Document Intelligence OCR fields. This means they either:")
    report_lines.append("1. Cannot be extracted from DI OCR (not available in prebuilt-invoice model)")
    report_lines.append("2. Are computed/derived fields")
    report_lines.append("3. Need to be added to the DI mapping")
    report_lines.append("")
    
    # Group missing fields by type
    financial_adjustments = ["discount_amount", "shipping_amount", "handling_fee", "deposit_amount"]
    tax_amounts_rates = ["gst_amount", "gst_rate", "hst_amount", "hst_rate", "qst_amount", "qst_rate", 
                         "pst_amount", "pst_rate"]
    payment_fields = ["payment_method", "payment_due_upon"]
    
    missing_financial = [f for f in financial_adjustments if f in ui_fields_not_from_di]
    missing_tax = [f for f in tax_amounts_rates if f in ui_fields_not_from_di]
    missing_payment = [f for f in payment_fields if f in ui_fields_not_from_di]
    other_missing = ui_fields_not_from_di - set(financial_adjustments) - set(tax_amounts_rates) - set(payment_fields)
    
    if missing_financial:
        report_lines.append("### Financial Adjustment Fields")
        report_lines.append("")
        for field in sorted(missing_financial):
            report_lines.append(f"- `{field}`")
        report_lines.append("")
    
    if missing_tax:
        report_lines.append("### Canadian Tax Amounts/Rates")
        report_lines.append("")
        for field in sorted(missing_tax):
            report_lines.append(f"- `{field}`")
        report_lines.append("")
    
    if missing_payment:
        report_lines.append("### Payment Fields")
        report_lines.append("")
        for field in sorted(missing_payment):
            report_lines.append(f"- `{field}`")
        report_lines.append("")
    
    if other_missing:
        report_lines.append("### Other Fields")
        report_lines.append("")
        for field in sorted(other_missing):
            report_lines.append(f"- `{field}`")
        report_lines.append("")
    
    # Fields in contract but not in UI
    if contract_not_in_ui:
        report_lines.append("## Fields in Contract Schema but NOT in UI")
        report_lines.append("")
        report_lines.append("These fields are defined in the contract schema but are not displayed in the UI:")
        report_lines.append("")
        for field in sorted(contract_not_in_ui):
            di_fields = get_di_fields_for_canonical(field)
            if di_fields:
                di_field_str = ", ".join([f"`{df}`" for df in di_fields])
                report_lines.append(f"- `{field}` ← {di_field_str}")
            else:
                report_lines.append(f"- `{field}` ← **NOT mapped from DI**")
        report_lines.append("")
    
    # Recommendations
    report_lines.append("## Recommendations")
    report_lines.append("")
    report_lines.append("1. **Verify DI OCR Capabilities**: Check Azure Document Intelligence")
    report_lines.append("   prebuilt-invoice documentation to confirm which of the 'missing' fields")
    report_lines.append("   are actually available from DI OCR but not yet mapped.")
    report_lines.append("")
    report_lines.append("2. **Update DI Mappings**: If fields are available from DI OCR but not")
    report_lines.append("   mapped, add them to the `DI_TO_CANONICAL` mapping in `field_extractor.py`")
    report_lines.append("   and update the contract schema `di_to_canonical` mappings.")
    report_lines.append("")
    report_lines.append("3. **Remove or Clarify Non-DI Fields**: Fields that cannot be extracted")
    report_lines.append("   from DI OCR should either:")
    report_lines.append("   - Be removed from the UI if not needed")
    report_lines.append("   - Be clearly marked as computed/derived fields")
    report_lines.append("   - Be documented as requiring LLM fallback or manual entry")
    report_lines.append("")
    report_lines.append("4. **Align UI with Contract**: Consider removing fields from the UI that")
    report_lines.append("   are not in the contract schema, OR add them to the contract schema")
    report_lines.append("   if they are needed.")
    report_lines.append("")
    
    # Write report
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    
    print(f"Generated reconciliation: {OUTPUT_FILE}")
    print(f"\nUI fields: {len(STREAMLIT_UI_FIELDS)}")
    print(f"Mapped from DI: {len(ui_fields_from_di)}")
    print(f"NOT mapped from DI: {len(ui_fields_not_from_di)}")
    if ui_fields_not_from_di:
        print(f"\nFields NOT mapped from DI:")
        for field in sorted(ui_fields_not_from_di):
            print(f"  - {field}")

if __name__ == "__main__":
    generate_reconciliation()
