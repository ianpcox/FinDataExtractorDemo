#!/usr/bin/env python3
"""Analyze the UI field gap for both DEMO and Vanilla projects"""

import json
import csv
from pathlib import Path

DEMO_ROOT = Path(__file__).parent.parent
VANILLA_ROOT = DEMO_ROOT.parent / "FinDataExtractorVanilla"

DEMO_CONTRACT = DEMO_ROOT / "schemas" / "invoice.contract.v1.json"
VANILLA_CONTRACT = VANILLA_ROOT / "schemas" / "invoice.contract.v1.json"
DEMO_UI_CSV = DEMO_ROOT / "invoice_ui_fields.csv"
VANILLA_UI_CSV = VANILLA_ROOT / "invoice_ui_fields.csv"
OUTPUT_FILE = DEMO_ROOT / "ui_fields_gap_analysis.md"

def load_contract_fields(contract_path):
    """Load fields from contract schema"""
    with open(contract_path, "r", encoding="utf-8") as f:
        contract = json.load(f)
    return set(contract.get("fields", {}).keys())

def load_csv_fields(csv_path):
    """Load fields from UI CSV"""
    fields = set()
    if csv_path.exists():
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                fields.add(row["Field Name"])
    return fields

def generate_analysis():
    """Generate gap analysis"""
    demo_contract_fields = load_contract_fields(DEMO_CONTRACT)
    vanilla_contract_fields = load_contract_fields(VANILLA_CONTRACT)
    demo_csv_fields = load_csv_fields(DEMO_UI_CSV)
    vanilla_csv_fields = load_csv_fields(VANILLA_UI_CSV)
    
    # Compare contracts
    contract_common = demo_contract_fields & vanilla_contract_fields
    only_in_demo_contract = demo_contract_fields - vanilla_contract_fields
    only_in_vanilla_contract = vanilla_contract_fields - demo_contract_fields
    
    # Compare CSVs
    csv_common = demo_csv_fields & vanilla_csv_fields
    only_in_demo_csv = demo_csv_fields - vanilla_csv_fields
    only_in_vanilla_csv = vanilla_csv_fields - demo_csv_fields
    
    # Generate report
    report_lines = []
    report_lines.append("# UI Fields Gap Analysis: DEMO vs Vanilla")
    report_lines.append("")
    report_lines.append("This document analyzes the gap between contract schema fields and what should be")
    report_lines.append("displayed in the UI for both DEMO and Vanilla projects.")
    report_lines.append("")
    report_lines.append("## Problem Summary")
    report_lines.append("")
    report_lines.append("**The contract schemas and UI CSV files do NOT match what is actually displayed")
    report_lines.append("in the Streamlit UI.**")
    report_lines.append("")
    report_lines.append("From analysis of the Streamlit UI code:")
    report_lines.append("- **DEMO Streamlit UI displays**: 51 fields")
    report_lines.append("- **DEMO Contract Schema defines**: 24 fields")
    report_lines.append("- **Missing from DEMO Contract**: 27 fields")
    report_lines.append("")
    report_lines.append("This means 27 fields shown in the UI cannot be properly extracted/validated")
    report_lines.append("according to the contract schema.")
    report_lines.append("")
    
    report_lines.append("## Contract Schema Comparison")
    report_lines.append("")
    report_lines.append(f"- **DEMO Contract Fields**: {len(demo_contract_fields)}")
    report_lines.append(f"- **Vanilla Contract Fields**: {len(vanilla_contract_fields)}")
    report_lines.append(f"- **Common Fields**: {len(contract_common)}")
    report_lines.append(f"- **Only in DEMO Contract**: {len(only_in_demo_contract)}")
    report_lines.append(f"- **Only in Vanilla Contract**: {len(only_in_vanilla_contract)}")
    report_lines.append("")
    
    if only_in_demo_contract:
        report_lines.append("### Fields Only in DEMO Contract")
        report_lines.append("")
        for field in sorted(only_in_demo_contract):
            report_lines.append(f"- `{field}`")
        report_lines.append("")
    
    if only_in_vanilla_contract:
        report_lines.append("### Fields Only in Vanilla Contract")
        report_lines.append("")
        for field in sorted(only_in_vanilla_contract):
            report_lines.append(f"- `{field}`")
        report_lines.append("")
    
    report_lines.append("## CSV Comparison")
    report_lines.append("")
    report_lines.append(f"- **DEMO CSV Fields**: {len(demo_csv_fields)}")
    report_lines.append(f"- **Vanilla CSV Fields**: {len(vanilla_csv_fields)}")
    report_lines.append(f"- **Common Fields**: {len(csv_common)}")
    report_lines.append(f"- **Only in DEMO CSV**: {len(only_in_demo_csv)}")
    report_lines.append(f"- **Only in Vanilla CSV**: {len(only_in_vanilla_csv)}")
    report_lines.append("")
    
    report_lines.append("## Recommendations")
    report_lines.append("")
    report_lines.append("1. **Update Contract Schemas**: The contract schemas need to include ALL fields")
    report_lines.append("   that are displayed in the Streamlit UI. Currently missing 27+ fields.")
    report_lines.append("")
    report_lines.append("2. **Update UI CSV Files**: After updating contract schemas, regenerate the")
    report_lines.append("   invoice_ui_fields.csv files to reflect all UI fields.")
    report_lines.append("")
    report_lines.append("3. **Verify Both Projects**: Ensure both DEMO and Vanilla projects have")
    report_lines.append("   consistent field definitions in their contract schemas.")
    report_lines.append("")
    report_lines.append("4. **Field Categories**: The missing fields include:")
    report_lines.append("   - Vendor contact fields (email, fax, website)")
    report_lines.append("   - Customer contact fields (phone, email, fax)")
    report_lines.append("   - Tax registration numbers (business_number, gst_number, qst_number, pst_number)")
    report_lines.append("   - Financial adjustment fields (discount_amount, shipping_amount, handling_fee, deposit_amount)")
    report_lines.append("   - Canadian tax amounts and rates (gst_amount, gst_rate, hst_amount, hst_rate, qst_amount, qst_rate, pst_amount, pst_rate)")
    report_lines.append("   - Payment fields (payment_method, payment_due_upon)")
    report_lines.append("   - Invoice metadata (invoice_type, reference_number, entity)")
    report_lines.append("")
    
    # Write report
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    
    print(f"Generated gap analysis: {OUTPUT_FILE}")
    print(f"\nDEMO Contract: {len(demo_contract_fields)} fields")
    print(f"Vanilla Contract: {len(vanilla_contract_fields)} fields")
    print(f"Common: {len(contract_common)} fields")

if __name__ == "__main__":
    generate_analysis()
