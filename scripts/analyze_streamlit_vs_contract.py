#!/usr/bin/env python3
"""Analyze what fields are actually displayed in Streamlit UI vs contract schema"""

import json
import csv
from pathlib import Path

DEMO_ROOT = Path(__file__).parent.parent
CONTRACT_JSON = DEMO_ROOT / "schemas" / "invoice.contract.v1.json"
UI_FIELDS_CSV = DEMO_ROOT / "invoice_ui_fields.csv"
OUTPUT_FILE = DEMO_ROOT / "streamlit_ui_vs_contract_analysis.md"

# Fields actually displayed in Streamlit UI (extracted from streamlit_app.py code analysis)
STREAMLIT_UI_FIELDS = {
    # Header fields (Tab 1)
    "invoice_number",
    "invoice_date", 
    "due_date",
    "invoice_type",
    "reference_number",
    "po_number",
    "standing_offer_number",
    "contract_id",
    "entity",
    
    # Vendor fields (Tab 1)
    "vendor_name",
    "vendor_id",
    "vendor_phone",
    "vendor_fax",
    "vendor_email",
    "vendor_website",
    
    # Vendor tax fields (Tab 1)
    "business_number",
    "gst_number",
    "qst_number",
    "pst_number",
    "tax_registration_number",
    
    # Customer fields (Tab 1)
    "customer_name",
    "customer_id",
    "customer_phone",
    "customer_email",
    "customer_fax",
    
    # Remit-to fields (Tab 1)
    "remit_to_name",
    
    # Address fields (Tab 5) - displayed as structured objects
    "vendor_address",
    "bill_to_address",
    "remit_to_address",
    
    # Financial fields (Tab 2)
    "subtotal",
    "discount_amount",
    "shipping_amount",
    "handling_fee",
    "deposit_amount",
    "tax_amount",
    "total_amount",
    "currency",
    
    # Canadian tax amounts and rates (Tab 2)
    "gst_amount",
    "gst_rate",
    "hst_amount",
    "hst_rate",
    "qst_amount",
    "qst_rate",
    "pst_amount",
    "pst_rate",
    
    # Payment fields (Tab 3)
    "payment_terms",
    "payment_method",
    "payment_due_upon",
    "acceptance_percentage",
    
    # Period fields (Tab 3)
    "period_start",
    "period_end",
}

def load_contract_fields():
    """Load fields from contract schema"""
    with open(CONTRACT_JSON, "r", encoding="utf-8") as f:
        contract = json.load(f)
    return set(contract.get("fields", {}).keys())

def load_ui_csv_fields():
    """Load fields from UI CSV"""
    fields = set()
    with open(UI_FIELDS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fields.add(row["Field Name"])
    return fields

def generate_analysis():
    """Generate comprehensive analysis"""
    contract_fields = load_contract_fields()
    csv_fields = load_ui_csv_fields()
    
    # Compare
    only_in_streamlit = STREAMLIT_UI_FIELDS - contract_fields
    only_in_contract = contract_fields - STREAMLIT_UI_FIELDS
    in_both = STREAMLIT_UI_FIELDS & contract_fields
    
    only_in_streamlit_vs_csv = STREAMLIT_UI_FIELDS - csv_fields
    only_in_csv = csv_fields - STREAMLIT_UI_FIELDS
    
    # Generate report
    report_lines = []
    report_lines.append("# Streamlit UI vs Contract Schema Field Analysis")
    report_lines.append("")
    report_lines.append("This document analyzes the discrepancy between fields displayed in the Streamlit UI")
    report_lines.append("and fields defined in the contract schema (which should represent the UI fields).")
    report_lines.append("")
    
    report_lines.append("## Summary")
    report_lines.append("")
    report_lines.append(f"- **Fields in Streamlit UI**: {len(STREAMLIT_UI_FIELDS)}")
    report_lines.append(f"- **Fields in Contract Schema**: {len(contract_fields)}")
    report_lines.append(f"- **Fields in UI CSV**: {len(csv_fields)}")
    report_lines.append(f"- **Fields in Both Streamlit & Contract**: {len(in_both)}")
    report_lines.append(f"- **Only in Streamlit UI (not in contract)**: {len(only_in_streamlit)}")
    report_lines.append(f"- **Only in Contract Schema (not in Streamlit UI)**: {len(only_in_contract)}")
    report_lines.append("")
    
    report_lines.append("## Fields Displayed in Streamlit UI")
    report_lines.append("")
    report_lines.append("### Header Fields (Tab 1: Company and Vendor)")
    header_fields = ["invoice_number", "invoice_date", "due_date", "invoice_type", "reference_number", 
                     "po_number", "standing_offer_number", "contract_id", "entity"]
    for field in header_fields:
        status = "✓" if field in contract_fields else "✗"
        report_lines.append(f"- {status} `{field}`")
    report_lines.append("")
    
    report_lines.append("### Vendor Fields (Tab 1)")
    vendor_fields = ["vendor_name", "vendor_id", "vendor_phone", "vendor_fax", "vendor_email", "vendor_website"]
    for field in vendor_fields:
        status = "✓" if field in contract_fields else "✗"
        report_lines.append(f"- {status} `{field}`")
    report_lines.append("")
    
    report_lines.append("### Vendor Tax Fields (Tab 1)")
    tax_fields = ["business_number", "gst_number", "qst_number", "pst_number", "tax_registration_number"]
    for field in tax_fields:
        status = "✓" if field in contract_fields else "✗"
        report_lines.append(f"- {status} `{field}`")
    report_lines.append("")
    
    report_lines.append("### Customer Fields (Tab 1)")
    customer_fields = ["customer_name", "customer_id", "customer_phone", "customer_email", "customer_fax"]
    for field in customer_fields:
        status = "✓" if field in contract_fields else "✗"
        report_lines.append(f"- {status} `{field}`")
    report_lines.append("")
    
    report_lines.append("### Remit-To Fields (Tab 1)")
    remit_fields = ["remit_to_name"]
    for field in remit_fields:
        status = "✓" if field in contract_fields else "✗"
        report_lines.append(f"- {status} `{field}`")
    report_lines.append("")
    
    report_lines.append("### Address Fields (Tab 5: Addresses)")
    address_fields = ["vendor_address", "bill_to_address", "remit_to_address"]
    for field in address_fields:
        status = "✓" if field in contract_fields else "✗"
        report_lines.append(f"- {status} `{field}`")
    report_lines.append("")
    
    report_lines.append("### Financial Fields (Tab 2: Financial)")
    financial_fields = ["subtotal", "discount_amount", "shipping_amount", "handling_fee", "deposit_amount",
                        "tax_amount", "total_amount", "currency"]
    for field in financial_fields:
        status = "✓" if field in contract_fields else "✗"
        report_lines.append(f"- {status} `{field}`")
    report_lines.append("")
    
    report_lines.append("### Canadian Tax Fields (Tab 2: Financial)")
    canadian_tax_fields = ["gst_amount", "gst_rate", "hst_amount", "hst_rate", "qst_amount", "qst_rate",
                           "pst_amount", "pst_rate"]
    for field in canadian_tax_fields:
        status = "✓" if field in contract_fields else "✗"
        report_lines.append(f"- {status} `{field}`")
    report_lines.append("")
    
    report_lines.append("### Payment Fields (Tab 3: Payment & Dates)")
    payment_fields = ["payment_terms", "payment_method", "payment_due_upon", "acceptance_percentage"]
    for field in payment_fields:
        status = "✓" if field in contract_fields else "✗"
        report_lines.append(f"- {status} `{field}`")
    report_lines.append("")
    
    report_lines.append("### Period Fields (Tab 3: Payment & Dates)")
    period_fields = ["period_start", "period_end"]
    for field in period_fields:
        status = "✓" if field in contract_fields else "✗"
        report_lines.append(f"- {status} `{field}`")
    report_lines.append("")
    
    # Fields only in Streamlit
    if only_in_streamlit:
        report_lines.append("## ⚠️ Fields in Streamlit UI but NOT in Contract Schema")
        report_lines.append("")
        report_lines.append("These fields are displayed in the Streamlit UI but are **missing** from the contract schema.")
        report_lines.append("This means they cannot be properly extracted/validated according to the contract.")
        report_lines.append("")
        for field in sorted(only_in_streamlit):
            report_lines.append(f"- `{field}`")
        report_lines.append("")
    
    # Fields only in contract
    if only_in_contract:
        report_lines.append("## ⚠️ Fields in Contract Schema but NOT in Streamlit UI")
        report_lines.append("")
        report_lines.append("These fields are defined in the contract schema but are **NOT displayed** in the Streamlit UI.")
        report_lines.append("Users cannot review/edit these fields even though they are part of the contract.")
        report_lines.append("")
        for field in sorted(only_in_contract):
            report_lines.append(f"- `{field}`")
        report_lines.append("")
    
    # Comparison with CSV
    report_lines.append("## Comparison with invoice_ui_fields.csv")
    report_lines.append("")
    report_lines.append(f"- **Fields in Both Streamlit & CSV**: {len(STREAMLIT_UI_FIELDS & csv_fields)}")
    report_lines.append(f"- **Only in CSV (not in Streamlit UI)**: {len(only_in_csv)}")
    report_lines.append(f"- **Only in Streamlit UI (not in CSV)**: {len(only_in_streamlit_vs_csv)}")
    report_lines.append("")
    
    if only_in_csv:
        report_lines.append("### Fields in CSV but NOT in Streamlit UI")
        report_lines.append("")
        for field in sorted(only_in_csv):
            report_lines.append(f"- `{field}`")
        report_lines.append("")
    
    if only_in_streamlit_vs_csv:
        report_lines.append("### Fields in Streamlit UI but NOT in CSV")
        report_lines.append("")
        for field in sorted(only_in_streamlit_vs_csv):
            report_lines.append(f"- `{field}`")
        report_lines.append("")
    
    # Write report
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    
    print(f"Generated analysis: {OUTPUT_FILE}")
    print(f"\nStreamlit UI fields: {len(STREAMLIT_UI_FIELDS)}")
    print(f"Contract schema fields: {len(contract_fields)}")
    print(f"UI CSV fields: {len(csv_fields)}")
    print(f"\nOnly in Streamlit (not in contract): {len(only_in_streamlit)} fields")
    if only_in_streamlit:
        print(f"  {sorted(only_in_streamlit)}")
    print(f"\nOnly in Contract (not in Streamlit): {len(only_in_contract)} fields")
    if only_in_contract:
        print(f"  {sorted(only_in_contract)}")

if __name__ == "__main__":
    generate_analysis()
