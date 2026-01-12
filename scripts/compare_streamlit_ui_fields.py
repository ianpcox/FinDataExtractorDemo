#!/usr/bin/env python3
"""Compare Streamlit UI fields with contract schema fields"""

import csv
import json
from pathlib import Path
from typing import Set, Dict, List

DEMO_ROOT = Path(__file__).parent.parent
STREAMLIT_APP = DEMO_ROOT / "streamlit_app.py"
CONTRACT_JSON = DEMO_ROOT / "schemas" / "invoice.contract.v1.json"
UI_FIELDS_CSV = DEMO_ROOT / "invoice_ui_fields.csv"
OUTPUT_FILE = DEMO_ROOT / "streamlit_ui_fields_analysis.md"

def extract_streamlit_fields() -> Dict[str, List[str]]:
    """Extract field lists from Streamlit app"""
    with open(STREAMLIT_APP, "r", encoding="utf-8") as f:
        content = f.read()
    
    fields_dict = {}
    
    # Extract header_fields
    import re
    header_match = re.search(r'header_fields\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if header_match:
        header_str = header_match.group(1)
        fields_dict["header_fields"] = [f.strip().strip('"\'') for f in re.findall(r'"(.*?)"', header_str)]
    
    vendor_match = re.search(r'vendor_fields\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if vendor_match:
        vendor_str = vendor_match.group(1)
        fields_dict["vendor_fields"] = [f.strip().strip('"\'') for f in re.findall(r'"(.*?)"', vendor_str)]
    
    vendor_tax_match = re.search(r'vendor_tax_fields\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if vendor_tax_match:
        vendor_tax_str = vendor_tax_match.group(1)
        fields_dict["vendor_tax_fields"] = [f.strip().strip('"\'') for f in re.findall(r'"(.*?)"', vendor_tax_str)]
    
    customer_match = re.search(r'customer_fields\s*=\s*\[(.*?)\]', content, re.DOTALL)
    if customer_match:
        customer_str = customer_match.group(1)
        fields_dict["customer_fields"] = [f.strip().strip('"\'') for f in re.findall(r'"(.*?)"', customer_str)]
    
    # Look for address fields
    if 'vendor_address' in content or 'bill_to_address' in content or 'remit_to_address' in content:
        fields_dict["address_fields"] = ["vendor_address", "bill_to_address", "remit_to_address"]
    
    # Look for amount fields - check for subtotal, tax_amount, total_amount, currency, payment_terms
    amount_fields = []
    for field in ["subtotal", "tax_amount", "total_amount", "currency", "payment_terms", "acceptance_percentage"]:
        if field in content and f'"{field}"' in content:
            amount_fields.append(field)
    if amount_fields:
        fields_dict["amount_fields"] = amount_fields
    
    # Look for period fields
    period_fields = []
    for field in ["period_start", "period_end"]:
        if field in content:
            period_fields.append(field)
    if period_fields:
        fields_dict["period_fields"] = period_fields
    
    # Look for remit_to_name
    if "remit_to_name" in content:
        fields_dict["remit_to_fields"] = ["remit_to_name"]
    
    return fields_dict

def load_contract_fields() -> Set[str]:
    """Load fields from contract schema"""
    with open(CONTRACT_JSON, "r", encoding="utf-8") as f:
        contract = json.load(f)
    return set(contract.get("fields", {}).keys())

def load_ui_fields_csv() -> Set[str]:
    """Load fields from UI fields CSV"""
    fields = set()
    with open(UI_FIELDS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fields.add(row["Field Name"])
    return fields

def generate_analysis():
    """Generate analysis report"""
    streamlit_fields_dict = extract_streamlit_fields()
    
    # Flatten all Streamlit fields
    all_streamlit_fields = set()
    for field_list in streamlit_fields_dict.values():
        all_streamlit_fields.update(field_list)
    
    contract_fields = load_contract_fields()
    ui_csv_fields = load_ui_fields_csv()
    
    # Compare
    only_in_streamlit = all_streamlit_fields - contract_fields
    only_in_contract = contract_fields - all_streamlit_fields
    in_both = all_streamlit_fields & contract_fields
    
    # Generate report
    report_lines = []
    report_lines.append("# Streamlit UI Fields Analysis")
    report_lines.append("")
    report_lines.append("This document compares the fields actually displayed in the Streamlit UI")
    report_lines.append("with the fields defined in the contract schema (invoice_ui_fields.csv).")
    report_lines.append("")
    
    report_lines.append("## Summary")
    report_lines.append("")
    report_lines.append(f"- **Fields in Streamlit UI**: {len(all_streamlit_fields)}")
    report_lines.append(f"- **Fields in Contract Schema**: {len(contract_fields)}")
    report_lines.append(f"- **Fields in UI CSV**: {len(ui_csv_fields)}")
    report_lines.append(f"- **Fields in Both Streamlit & Contract**: {len(in_both)}")
    report_lines.append(f"- **Only in Streamlit UI (not in contract)**: {len(only_in_streamlit)}")
    report_lines.append(f"- **Only in Contract Schema (not in Streamlit UI)**: {len(only_in_contract)}")
    report_lines.append("")
    
    # Streamlit field groups
    report_lines.append("## Fields Displayed in Streamlit UI")
    report_lines.append("")
    for group_name, fields_list in sorted(streamlit_fields_dict.items()):
        report_lines.append(f"### {group_name.replace('_', ' ').title()}")
        report_lines.append("")
        for field in fields_list:
            in_contract = "✓" if field in contract_fields else "✗"
            report_lines.append(f"- {in_contract} `{field}`")
        report_lines.append("")
    
    # Fields only in Streamlit
    if only_in_streamlit:
        report_lines.append("## Fields in Streamlit UI but NOT in Contract Schema")
        report_lines.append("")
        report_lines.append("These fields are displayed in the UI but are not defined in the contract schema:")
        report_lines.append("")
        for field in sorted(only_in_streamlit):
            report_lines.append(f"- `{field}`")
        report_lines.append("")
    
    # Fields only in contract
    if only_in_contract:
        report_lines.append("## Fields in Contract Schema but NOT in Streamlit UI")
        report_lines.append("")
        report_lines.append("These fields are defined in the contract schema but are NOT displayed in the Streamlit UI:")
        report_lines.append("")
        for field in sorted(only_in_contract):
            report_lines.append(f"- `{field}`")
        report_lines.append("")
    
    # Comparison with UI CSV
    report_lines.append("## Comparison with invoice_ui_fields.csv")
    report_lines.append("")
    only_in_csv = ui_csv_fields - all_streamlit_fields
    only_in_streamlit_vs_csv = all_streamlit_fields - ui_csv_fields
    in_both_csv = all_streamlit_fields & ui_csv_fields
    
    report_lines.append(f"- **Fields in Both**: {len(in_both_csv)}")
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
    print(f"\nStreamlit UI fields: {len(all_streamlit_fields)}")
    print(f"Contract schema fields: {len(contract_fields)}")
    print(f"UI CSV fields: {len(ui_csv_fields)}")
    print(f"\nOnly in Streamlit: {sorted(only_in_streamlit)}")
    print(f"\nOnly in Contract: {sorted(only_in_contract)}")

if __name__ == "__main__":
    generate_analysis()
