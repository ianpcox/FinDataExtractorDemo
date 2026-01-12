#!/usr/bin/env python3
"""
Verify DI OCR field mappings against Azure Document Intelligence documentation.

This script compares the fields mapped in field_extractor.py with the official
Azure Document Intelligence prebuilt-invoice model fields.
"""

from pathlib import Path
import sys

DEMO_ROOT = Path(__file__).parent.parent
VANILLA_ROOT = DEMO_ROOT.parent / "FinDataExtractorVanilla"

def get_field_extractor_mappings(project_root: Path):
    """Extract DI_TO_CANONICAL mappings from field_extractor.py"""
    field_extractor_path = project_root / "src" / "extraction" / "field_extractor.py"
    
    if not field_extractor_path.exists():
        return {}
    
    with open(field_extractor_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Find DI_TO_CANONICAL dictionary
    mappings = {}
    in_dict = False
    lines = content.split("\n")
    
    for i, line in enumerate(lines):
        if "DI_TO_CANONICAL" in line and "=" in line:
            in_dict = True
            continue
        
        if in_dict:
            # Stop at closing brace
            if line.strip().startswith("}"):
                break
            
            # Parse mapping lines like: "InvoiceId": "invoice_number",
            if '": "' in line:
                try:
                    parts = line.split('": "')
                    if len(parts) == 2:
                        di_field = parts[0].strip().strip('"').strip("'")
                        canon_field = parts[1].strip().strip('"').strip("'").rstrip(",").rstrip('"').rstrip("'")
                        mappings[di_field] = canon_field
                except Exception:
                    pass
    
    return mappings

# Official Azure Document Intelligence prebuilt-invoice fields
# Based on Microsoft documentation
OFFICIAL_DI_INVOICE_FIELDS = {
    # Core invoice fields
    "InvoiceId": "Invoice ID/Number",
    "InvoiceDate": "Invoice Date",
    "DueDate": "Due Date",
    "InvoiceTotal": "Invoice Total",
    "SubTotal": "Subtotal",
    "TotalTax": "Total Tax",
    "VendorName": "Vendor Name",
    "VendorAddress": "Vendor Address",
    "VendorAddressRecipient": "Vendor Address Recipient",
    "CustomerName": "Customer Name",
    "CustomerId": "Customer ID",
    "CustomerAddress": "Customer Address",
    "CustomerAddressRecipient": "Customer Address Recipient",
    "BillingAddress": "Billing Address",
    "BillingAddressRecipient": "Billing Address Recipient",
    "ShippingAddress": "Shipping Address",
    "ShippingAddressRecipient": "Shipping Address Recipient",
    "RemittanceAddress": "Remittance Address",
    "RemittanceAddressRecipient": "Remittance Address Recipient",
    "PurchaseOrder": "Purchase Order",
    "Items": "Line Items",
    
    # Payment information
    "PaymentTerm": "Payment Terms",
    "AmountDue": "Amount Due",
    
    # Currency
    "CurrencyCode": "Currency Code",
    
    # Contact information (may be available)
    "VendorAddressRecipient": "Vendor Address Recipient",
    
    # Service dates (may be available)
    "ServiceDate": "Service Date",
    "ServiceStartDate": "Service Start Date",
    "ServiceEndDate": "Service End Date",
}

# Note: Many fields we're mapping may not be in the official documentation
# but may still be available in the API response. This is a conservative list
# based on public documentation.

def generate_verification_report():
    """Generate verification report for both projects"""
    
    demo_mappings = get_field_extractor_mappings(DEMO_ROOT)
    vanilla_mappings = get_field_extractor_mappings(VANILLA_ROOT)
    
    # Get unique DI fields from mappings
    demo_di_fields = set(demo_mappings.keys())
    vanilla_di_fields = set(vanilla_mappings.keys())
    
    # Compare with official fields
    official_fields = set(OFFICIAL_DI_INVOICE_FIELDS.keys())
    
    demo_official = demo_di_fields & official_fields
    demo_unofficial = demo_di_fields - official_fields
    
    vanilla_official = vanilla_di_fields & official_fields
    vanilla_unofficial = vanilla_di_fields - official_fields
    
    report_lines = []
    report_lines.append("# Azure Document Intelligence Prebuilt-Invoice Field Verification")
    report_lines.append("")
    report_lines.append("This document compares the DI fields mapped in the codebase with")
    report_lines.append("the officially documented fields from Azure Document Intelligence")
    report_lines.append("prebuilt-invoice model.")
    report_lines.append("")
    report_lines.append("## Important Notes")
    report_lines.append("")
    report_lines.append("⚠️ **Limitation**: The official Azure documentation may not list all")
    report_lines.append("fields that are actually available in the API response. Some fields")
    report_lines.append("may be available but not documented, or may be available in certain")
    report_lines.append("invoice formats but not others.")
    report_lines.append("")
    report_lines.append("📋 **Recommendation**: This analysis should be supplemented with:")
    report_lines.append("1. Testing with actual invoice documents")
    report_lines.append("2. Inspecting actual API responses from Azure DI")
    report_lines.append("3. Checking Azure SDK source code or API reference")
    report_lines.append("")
    
    report_lines.append("## DEMO Project Analysis")
    report_lines.append("")
    report_lines.append(f"- **Total DI fields mapped**: {len(demo_di_fields)}")
    report_lines.append(f"- **Fields in official documentation**: {len(demo_official)}")
    report_lines.append(f"- **Fields NOT in official documentation**: {len(demo_unofficial)}")
    report_lines.append("")
    
    if demo_official:
        report_lines.append("### ✅ Fields Mapped that ARE in Official Documentation")
        report_lines.append("")
        for field in sorted(demo_official):
            canonical = demo_mappings[field]
            description = OFFICIAL_DI_INVOICE_FIELDS.get(field, "")
            report_lines.append(f"- `{field}` → `{canonical}` ({description})")
        report_lines.append("")
    
    if demo_unofficial:
        report_lines.append("### ⚠️ Fields Mapped that are NOT in Official Documentation")
        report_lines.append("")
        report_lines.append("These fields are mapped in the code but are not listed in the")
        report_lines.append("official Azure documentation. They may still be available in")
        report_lines.append("actual API responses, or may be custom/computed fields.")
        report_lines.append("")
        
        # Group by type
        vendor_fields = [f for f in demo_unofficial if "Vendor" in f]
        customer_fields = [f for f in demo_unofficial if "Customer" in f]
        tax_fields = [f for f in demo_unofficial if any(t in f for t in ["Tax", "GST", "HST", "QST", "PST", "Business"])]
        payment_fields = [f for f in demo_unofficial if "Payment" in f]
        financial_fields = [f for f in demo_unofficial if any(t in f for t in ["Amount", "Discount", "Shipping", "Handling", "Deposit", "Fee"])]
        other_fields = demo_unofficial - set(vendor_fields) - set(customer_fields) - set(tax_fields) - set(payment_fields) - set(financial_fields)
        
        if vendor_fields:
            report_lines.append("#### Vendor Contact Fields")
            for field in sorted(vendor_fields):
                canonical = demo_mappings[field]
                report_lines.append(f"- `{field}` → `{canonical}`")
            report_lines.append("")
        
        if customer_fields:
            report_lines.append("#### Customer Contact Fields")
            for field in sorted(customer_fields):
                canonical = demo_mappings[field]
                report_lines.append(f"- `{field}` → `{canonical}`")
            report_lines.append("")
        
        if tax_fields:
            report_lines.append("#### Tax Registration/Amount Fields")
            for field in sorted(tax_fields):
                canonical = demo_mappings[field]
                report_lines.append(f"- `{field}` → `{canonical}`")
            report_lines.append("")
        
        if payment_fields:
            report_lines.append("#### Payment Fields")
            for field in sorted(payment_fields):
                canonical = demo_mappings[field]
                report_lines.append(f"- `{field}` → `{canonical}`")
            report_lines.append("")
        
        if financial_fields:
            report_lines.append("#### Financial Adjustment Fields")
            for field in sorted(financial_fields):
                canonical = demo_mappings[field]
                report_lines.append(f"- `{field}` → `{canonical}`")
            report_lines.append("")
        
        if other_fields:
            report_lines.append("#### Other Fields")
            for field in sorted(other_fields):
                canonical = demo_mappings[field]
                report_lines.append(f"- `{field}` → `{canonical}`")
            report_lines.append("")
    
    report_lines.append("## VANILLA Project Analysis")
    report_lines.append("")
    report_lines.append(f"- **Total DI fields mapped**: {len(vanilla_di_fields)}")
    report_lines.append(f"- **Fields in official documentation**: {len(vanilla_official)}")
    report_lines.append(f"- **Fields NOT in official documentation**: {len(vanilla_unofficial)}")
    report_lines.append("")
    
    # Compare projects
    report_lines.append("## Project Comparison")
    report_lines.append("")
    common_fields = demo_di_fields & vanilla_di_fields
    only_demo = demo_di_fields - vanilla_di_fields
    only_vanilla = vanilla_di_fields - demo_di_fields
    
    report_lines.append(f"- **Fields in both projects**: {len(common_fields)}")
    report_lines.append(f"- **Only in DEMO**: {len(only_demo)}")
    report_lines.append(f"- **Only in VANILLA**: {len(only_vanilla)}")
    report_lines.append("")
    
    if only_demo:
        report_lines.append("### Fields Only in DEMO")
        for field in sorted(only_demo):
            report_lines.append(f"- `{field}` → `{demo_mappings[field]}`")
        report_lines.append("")
    
    if only_vanilla:
        report_lines.append("### Fields Only in VANILLA")
        for field in sorted(only_vanilla):
            report_lines.append(f"- `{field}` → `{vanilla_mappings[field]}`")
        report_lines.append("")
    
    report_lines.append("## Recommendations")
    report_lines.append("")
    report_lines.append("1. **Test with Real Invoices**: Run actual invoices through Azure DI")
    report_lines.append("   and inspect the API response to see which fields are actually")
    report_lines.append("   returned.")
    report_lines.append("")
    report_lines.append("2. **Check Azure SDK/API Reference**: The Python SDK or REST API")
    report_lines.append("   documentation may have more complete field lists than general")
    report_lines.append("   documentation.")
    report_lines.append("")
    report_lines.append("3. **Verify Field Availability**: Fields not in official documentation")
    report_lines.append("   may still work, but should be tested to ensure they're actually")
    report_lines.append("   available in the API response.")
    report_lines.append("")
    report_lines.append("4. **Handle Missing Fields Gracefully**: Code should handle cases where")
    report_lines.append("   mapped fields are not present in the DI response.")
    report_lines.append("")
    
    # Write report
    output_file = DEMO_ROOT / "di_ocr_field_verification.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    
    print(f"Generated verification report: {output_file}")
    print(f"\nDEMO Project:")
    print(f"  Total fields: {len(demo_di_fields)}")
    print(f"  In official docs: {len(demo_official)}")
    print(f"  Not in official docs: {len(demo_unofficial)}")
    print(f"\nVANILLA Project:")
    print(f"  Total fields: {len(vanilla_di_fields)}")
    print(f"  In official docs: {len(vanilla_official)}")
    print(f"  Not in official docs: {len(vanilla_unofficial)}")

if __name__ == "__main__":
    generate_verification_report()
