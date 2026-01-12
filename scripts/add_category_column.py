#!/usr/bin/env python3
"""Add Category column to canonical fields CSV"""

import csv
from pathlib import Path

CSV_FILE = Path(__file__).parent.parent / "invoice_canonical_fields.csv"

def get_category(field_name: str) -> str:
    """Determine the category/tab for a field"""
    
    # System/Internal fields
    system_fields = {
        "id", "file_path", "file_name", "upload_date", "status", "processing_state",
        "content_sha256", "created_at", "updated_at", "extraction_confidence",
        "extraction_timestamp", "review_status", "reviewer", "review_timestamp",
        "review_notes", "review_version", "bv_approver", "bv_approval_date",
        "bv_approval_notes", "fa_approver", "fa_approval_date", "fa_approval_notes",
        "field_confidence"
    }
    
    if field_name in system_fields:
        return "System"
    
    # Invoice Header/Basic Info
    header_fields = {
        "invoice_number", "invoice_date", "due_date", "invoice_type", "reference_number",
        "shipping_date", "delivery_date", "currency", "payment_terms", "payment_method",
        "payment_due_upon", "acceptance_percentage", "invoice_subtype"
    }
    
    if field_name in header_fields:
        return "Invoice Header"
    
    # Vendor Information
    if field_name.startswith("vendor_"):
        if field_name == "vendor_address" or ("." in field_name and field_name.startswith("vendor_address")):
            return "Vendor Information"
        return "Vendor Information"
    
    # Customer/Bill-To Information
    if field_name.startswith("customer_") or field_name.startswith("bill_to_address"):
        if "." in field_name and "bill_to_address" in field_name:
            return "Customer Information"
        return "Customer Information"
    
    # Remit-To Information
    if field_name.startswith("remit_to"):
        if "." in field_name and "remit_to_address" in field_name:
            return "Remit-To Information"
        return "Remit-To Information"
    
    # Tax Registration Numbers
    tax_reg_fields = {
        "business_number", "gst_number", "qst_number", "pst_number", "tax_registration_number"
    }
    if field_name in tax_reg_fields:
        return "Tax Registration"
    
    # Contract/PO Information
    contract_fields = {
        "entity", "contract_id", "standing_offer_number", "po_number"
    }
    if field_name in contract_fields:
        return "Contract/PO"
    
    # Service Period
    if field_name in {"period_start", "period_end"}:
        return "Service Period"
    
    # Amounts and Totals
    amount_fields = {
        "subtotal", "discount_amount", "shipping_amount", "handling_fee", "deposit_amount",
        "tax_amount", "total_amount", "gst_amount", "gst_rate", "hst_amount", "hst_rate",
        "qst_amount", "qst_rate", "pst_amount", "pst_rate", "tax_breakdown"
    }
    if field_name in amount_fields:
        return "Amounts & Totals"
    
    # Line Items
    if field_name == "line_items" or field_name.startswith("line_items[]"):
        return "Line Items"
    
    # Extensions
    if field_name in {"extensions"}:
        return "Extensions"
    
    return "Other"

def update_csv():
    """Add Category column to CSV"""
    rows = []
    
    # Read existing CSV
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            field_name = row["Field Name"]
            category = get_category(field_name)
            row["Category"] = category
            rows.append(row)
    
    # Write updated CSV
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        fieldnames_list = list(fieldnames) + ["Category"]
        writer = csv.DictWriter(f, fieldnames=fieldnames_list)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Updated {CSV_FILE} with Category column")
    print(f"Total fields: {len(rows)}")
    
    # Print category summary
    from collections import Counter
    categories = Counter(row["Category"] for row in rows)
    print("\nCategory distribution:")
    for category, count in sorted(categories.items()):
        print(f"  {category}: {count}")

if __name__ == "__main__":
    update_csv()
