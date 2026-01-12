#!/usr/bin/env python3
"""Compare invoice fields between DEMO and Vanilla projects"""

import csv
from pathlib import Path
from typing import Dict, Set, List, Tuple

VANILLA_ROOT = Path(__file__).parent.parent.parent / "FinDataExtractorVanilla"
DEMO_ROOT = Path(__file__).parent.parent

def load_fields_csv(csv_path: Path, key_col: str = "Field Name") -> Dict[str, Dict]:
    """Load fields from CSV file"""
    fields = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            field_name = row[key_col]
            fields[field_name] = row
    return fields

def compare_fields(demo_fields: Dict, vanilla_fields: Dict, field_type: str) -> Dict:
    """Compare two field dictionaries"""
    demo_names = set(demo_fields.keys())
    vanilla_names = set(vanilla_fields.keys())
    
    only_demo = demo_names - vanilla_names
    only_vanilla = vanilla_names - demo_names
    common = demo_names & vanilla_names
    
    # Find differences in common fields
    differences = []
    for field_name in sorted(common):
        demo_field = demo_fields[field_name]
        vanilla_field = vanilla_fields[field_name]
        
        diff = {}
        for key in demo_field.keys():
            if key in vanilla_field and demo_field[key] != vanilla_field[key]:
                diff[key] = {
                    "demo": demo_field[key],
                    "vanilla": vanilla_field[key]
                }
        if diff:
            differences.append((field_name, diff))
    
    return {
        "only_demo": sorted(only_demo),
        "only_vanilla": sorted(only_vanilla),
        "common": sorted(common),
        "differences": differences,
        "demo_count": len(demo_names),
        "vanilla_count": len(vanilla_names),
        "common_count": len(common)
    }

def generate_comparison_report():
    """Generate comparison report"""
    
    # Load canonical fields
    demo_canonical = load_fields_csv(DEMO_ROOT / "invoice_canonical_fields.csv")
    vanilla_canonical = load_fields_csv(VANILLA_ROOT / "invoice_canonical_fields.csv")
    
    # Load UI fields
    demo_ui = load_fields_csv(DEMO_ROOT / "invoice_ui_fields.csv")
    vanilla_ui = load_fields_csv(VANILLA_ROOT / "invoice_ui_fields.csv")
    
    # Compare canonical fields
    canonical_comp = compare_fields(demo_canonical, vanilla_canonical, "Canonical")
    
    # Compare UI fields
    ui_comp = compare_fields(demo_ui, vanilla_ui, "UI")
    
    # Generate report
    report_lines = []
    report_lines.append("# Invoice Fields Comparison: DEMO vs Vanilla")
    report_lines.append("")
    report_lines.append("This document compares the invoice fields between the FinDataExtractorDEMO")
    report_lines.append("and FinDataExtractorVanilla projects.")
    report_lines.append("")
    
    # Canonical Fields Comparison
    report_lines.append("## Canonical Fields Comparison")
    report_lines.append("")
    report_lines.append(f"- **DEMO Fields**: {canonical_comp['demo_count']}")
    report_lines.append(f"- **Vanilla Fields**: {canonical_comp['vanilla_count']}")
    report_lines.append(f"- **Common Fields**: {canonical_comp['common_count']}")
    report_lines.append(f"- **Only in DEMO**: {len(canonical_comp['only_demo'])}")
    report_lines.append(f"- **Only in Vanilla**: {len(canonical_comp['only_vanilla'])}")
    report_lines.append("")
    
    if canonical_comp['only_demo']:
        report_lines.append("### Fields Only in DEMO")
        report_lines.append("")
        for field_name in canonical_comp['only_demo']:
            field = demo_canonical[field_name]
            report_lines.append(f"- **{field_name}**: {field.get('Type', 'N/A')} - {field.get('Description', 'No description')}")
        report_lines.append("")
    
    if canonical_comp['only_vanilla']:
        report_lines.append("### Fields Only in Vanilla")
        report_lines.append("")
        for field_name in canonical_comp['only_vanilla']:
            field = vanilla_canonical[field_name]
            report_lines.append(f"- **{field_name}**: {field.get('Type', 'N/A')} - {field.get('Description', 'No description')}")
        report_lines.append("")
    
    if canonical_comp['differences']:
        report_lines.append("### Field Differences (Common Fields with Different Values)")
        report_lines.append("")
        for field_name, diff in canonical_comp['differences'][:20]:  # Limit to first 20
            report_lines.append(f"#### {field_name}")
            for key, values in diff.items():
                report_lines.append(f"- **{key}**:")
                report_lines.append(f"  - DEMO: `{values['demo']}`")
                report_lines.append(f"  - Vanilla: `{values['vanilla']}`")
            report_lines.append("")
        if len(canonical_comp['differences']) > 20:
            report_lines.append(f"*... and {len(canonical_comp['differences']) - 20} more differences*")
            report_lines.append("")
    
    # UI Fields Comparison
    report_lines.append("## UI Fields Comparison")
    report_lines.append("")
    report_lines.append(f"- **DEMO Fields**: {ui_comp['demo_count']}")
    report_lines.append(f"- **Vanilla Fields**: {ui_comp['vanilla_count']}")
    report_lines.append(f"- **Common Fields**: {ui_comp['common_count']}")
    report_lines.append(f"- **Only in DEMO**: {len(ui_comp['only_demo'])}")
    report_lines.append(f"- **Only in Vanilla**: {len(ui_comp['only_vanilla'])}")
    report_lines.append("")
    
    if ui_comp['only_demo']:
        report_lines.append("### Fields Only in DEMO")
        report_lines.append("")
        for field_name in ui_comp['only_demo']:
            field = demo_ui[field_name]
            report_lines.append(f"- **{field_name}**: {field.get('Type', 'N/A')} - {field.get('Description', 'No description')}")
        report_lines.append("")
    
    if ui_comp['only_vanilla']:
        report_lines.append("### Fields Only in Vanilla")
        report_lines.append("")
        for field_name in ui_comp['only_vanilla']:
            field = vanilla_ui[field_name]
            report_lines.append(f"- **{field_name}**: {field.get('Type', 'N/A')} - {field.get('Description', 'No description')}")
        report_lines.append("")
    
    if ui_comp['differences']:
        report_lines.append("### Field Differences (Common Fields with Different Values)")
        report_lines.append("")
        for field_name, diff in ui_comp['differences'][:20]:  # Limit to first 20
            report_lines.append(f"#### {field_name}")
            for key, values in diff.items():
                report_lines.append(f"- **{key}**:")
                report_lines.append(f"  - DEMO: `{values['demo']}`")
                report_lines.append(f"  - Vanilla: `{values['vanilla']}`")
            report_lines.append("")
        if len(ui_comp['differences']) > 20:
            report_lines.append(f"*... and {len(ui_comp['differences']) - 20} more differences*")
            report_lines.append("")
    else:
        report_lines.append("### Field Differences")
        report_lines.append("")
        report_lines.append("✓ **No differences found**: All UI fields are identical between DEMO and Vanilla projects.")
        report_lines.append("")
    
    # Summary
    report_lines.append("## Summary")
    report_lines.append("")
    report_lines.append("### Canonical Fields")
    report_lines.append("")
    if canonical_comp['demo_count'] == canonical_comp['vanilla_count'] and not canonical_comp['only_demo'] and not canonical_comp['only_vanilla']:
        report_lines.append("✓ **Identical**: Both projects have the same canonical fields.")
    else:
        report_lines.append("⚠ **Different**: The projects have different canonical fields.")
        if canonical_comp['only_demo']:
            report_lines.append(f"  - {len(canonical_comp['only_demo'])} fields only in DEMO")
        if canonical_comp['only_vanilla']:
            report_lines.append(f"  - {len(canonical_comp['only_vanilla'])} fields only in Vanilla")
    report_lines.append("")
    
    report_lines.append("### UI Fields")
    report_lines.append("")
    if ui_comp['demo_count'] == ui_comp['vanilla_count'] and not ui_comp['only_demo'] and not ui_comp['only_vanilla']:
        report_lines.append("✓ **Identical**: Both projects have the same UI fields.")
    else:
        report_lines.append("⚠ **Different**: The projects have different UI fields.")
        if ui_comp['only_demo']:
            report_lines.append(f"  - {len(ui_comp['only_demo'])} fields only in DEMO")
        if ui_comp['only_vanilla']:
            report_lines.append(f"  - {len(ui_comp['only_vanilla'])} fields only in Vanilla")
    report_lines.append("")
    
    # Write report
    output_file = DEMO_ROOT / "invoice_fields_project_comparison.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    
    print(f"Generated comparison report: {output_file}")
    print(f"\nCanonical Fields:")
    print(f"  DEMO: {canonical_comp['demo_count']}, Vanilla: {canonical_comp['vanilla_count']}, Common: {canonical_comp['common_count']}")
    print(f"  Only in DEMO: {len(canonical_comp['only_demo'])}, Only in Vanilla: {len(canonical_comp['only_vanilla'])}")
    print(f"\nUI Fields:")
    print(f"  DEMO: {ui_comp['demo_count']}, Vanilla: {ui_comp['vanilla_count']}, Common: {ui_comp['common_count']}")
    print(f"  Only in DEMO: {len(ui_comp['only_demo'])}, Only in Vanilla: {len(ui_comp['only_vanilla'])}")

if __name__ == "__main__":
    generate_comparison_report()
