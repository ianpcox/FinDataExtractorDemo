#!/usr/bin/env python3
"""Cross-reference canonical fields with UI fields and generate analysis report"""

import csv
from pathlib import Path
from typing import Dict, Set

CANONICAL_CSV = Path(__file__).parent.parent / "invoice_canonical_fields.csv"
UI_CSV = Path(__file__).parent.parent / "invoice_ui_fields.csv"
OUTPUT_FILE = Path(__file__).parent.parent / "invoice_fields_cross_reference.md"

def load_canonical_fields() -> Dict[str, Dict]:
    """Load canonical fields from CSV"""
    fields = {}
    with open(CANONICAL_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            field_name = row["Field Name"]
            fields[field_name] = {
                "type": row["Type"],
                "required": row["Required"],
                "nullable": row["Nullable"],
                "description": row["Description"],
                "category": row.get("Category", "Unknown")
            }
    return fields

def load_ui_fields() -> Set[str]:
    """Load UI field names from CSV"""
    ui_fields = set()
    with open(UI_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ui_fields.add(row["Field Name"])
    return ui_fields

def get_reason_not_in_ui(field_name: str, category: str, ui_fields: Set[str]) -> str:
    """Determine why a canonical field is not in the UI"""
    
    # System fields are intentionally not in UI
    if category == "System":
        return "System/internal field - not exposed in UI (e.g., database IDs, timestamps, processing state)"
    
    # Line items are handled separately in LineItemGrid component
    if field_name == "line_items" or field_name.startswith("line_items[]"):
        return "Line items are displayed in a separate LineItemGrid component, not in the main schema form"
    
    # Address sub-fields are nested within address objects
    if "." in field_name and ("address" in field_name or "bill_to" in field_name or "remit_to" in field_name):
        parent_field = field_name.split(".")[0]
        if parent_field in ui_fields:
            return f"Nested field within '{parent_field}' object - address fields are displayed as structured objects in UI"
        else:
            return f"Nested field - parent object '{parent_field}' not directly editable in UI form"
    
    # Extensions are handled separately
    if field_name == "extensions" or category == "Extensions":
        return "Extension fields are handled separately based on invoice_subtype (shift service, per diem travel)"
    
    # Check if it's a nested field we're not handling
    if "." in field_name:
        parent = field_name.split(".")[0]
        return f"Nested field - parent '{parent}' handled as object in UI"
    
    # Fields that should potentially be in UI but aren't
    if category in ["Invoice Header", "Vendor Information", "Customer Information", 
                    "Remit-To Information", "Tax Registration", "Contract/PO", 
                    "Service Period", "Amounts & Totals"]:
        return "Field not currently exposed in UI schema form - may be captured but not displayed for editing, or handled programmatically"
    
    return "Not currently exposed in UI"

def generate_report():
    """Generate cross-reference report"""
    canonical_fields = load_canonical_fields()
    ui_fields = load_ui_fields()
    
    # Organize by category
    by_category = {}
    for field_name, field_data in canonical_fields.items():
        category = field_data["category"]
        if category not in by_category:
            by_category[category] = []
        by_category[category].append((field_name, field_data))
    
    # Generate markdown report
    report_lines = []
    report_lines.append("# Invoice Fields Cross-Reference Analysis")
    report_lines.append("")
    report_lines.append("This document cross-references the canonical schema fields with the UI fields to identify")
    report_lines.append("which fields are captured/displayed in the UI and which are not, along with reasons.")
    report_lines.append("")
    report_lines.append("## Summary")
    report_lines.append("")
    
    total_fields = len(canonical_fields)
    in_ui_count = sum(1 for fname in canonical_fields.keys() if fname in ui_fields)
    not_in_ui_count = total_fields - in_ui_count
    
    report_lines.append(f"- **Total Canonical Fields**: {total_fields}")
    report_lines.append(f"- **Fields in UI Form**: {in_ui_count}")
    report_lines.append(f"- **Fields Not in UI Form**: {not_in_ui_count}")
    report_lines.append("")
    report_lines.append("## Field Analysis by Category")
    report_lines.append("")
    
    # Process each category
    for category in sorted(by_category.keys()):
        report_lines.append(f"### {category}")
        report_lines.append("")
        report_lines.append("| Field Name | Type | Required | In UI? | Reason/Notes |")
        report_lines.append("|------------|------|----------|--------|--------------|")
        
        for field_name, field_data in sorted(by_category[category]):
            in_ui = "Yes" if field_name in ui_fields else "No"
            type_str = field_data["type"]
            required = field_data["required"]
            
            if field_name in ui_fields:
                reason = "✓ Displayed in UI schema form"
            else:
                reason = get_reason_not_in_ui(field_name, category, ui_fields)
            
            # Escape pipe characters in descriptions/reasons
            reason = reason.replace("|", "\\|")
            
            report_lines.append(f"| `{field_name}` | {type_str} | {required} | {in_ui} | {reason} |")
        
        report_lines.append("")
    
    report_lines.append("## Notes")
    report_lines.append("")
    report_lines.append("### Fields Handled Separately")
    report_lines.append("")
    report_lines.append("1. **Line Items**: The `line_items` array and all sub-fields are displayed in a separate")
    report_lines.append("   `LineItemGrid` component, not in the main schema form. This provides a better")
    report_lines.append("   user experience for tabular data.")
    report_lines.append("")
    report_lines.append("2. **Address Fields**: Address objects (vendor_address, bill_to_address, remit_to_address)")
    report_lines.append("   are displayed as structured objects in the UI. Individual address components")
    report_lines.append("   (street, city, province, postal_code, country) are nested within these objects.")
    report_lines.append("")
    report_lines.append("3. **System Fields**: Fields marked as 'System' are internal to the application and")
    report_lines.append("   are not exposed in the UI for user editing. These include:")
    report_lines.append("   - Database identifiers (id)")
    report_lines.append("   - File metadata (file_path, file_name, upload_date)")
    report_lines.append("   - Processing state (status, processing_state)")
    report_lines.append("   - Extraction metadata (extraction_confidence, field_confidence, extraction_timestamp)")
    report_lines.append("   - Review metadata (review_status, reviewer, review_timestamp, review_notes, review_version)")
    report_lines.append("   - Approval metadata (bv_approver, fa_approver, approval dates/notes)")
    report_lines.append("   - Timestamps (created_at, updated_at)")
    report_lines.append("")
    report_lines.append("4. **Extensions**: The `extensions` field contains subtype-specific data (shift service,")
    report_lines.append("   per diem travel, timesheet data) that is handled dynamically based on the")
    report_lines.append("   invoice_subtype value.")
    report_lines.append("")
    report_lines.append("### Missing UI Fields Analysis")
    report_lines.append("")
    
    # Find fields that should be in UI but aren't
    missing_ui_fields = []
    for field_name, field_data in canonical_fields.items():
        category = field_data["category"]
        if (field_name not in ui_fields and 
            category not in ["System", "Line Items", "Extensions"] and
            "." not in field_name and
            not field_name.startswith("line_items")):
            missing_ui_fields.append((field_name, field_data))
    
    if missing_ui_fields:
        report_lines.append("The following fields from non-system categories are not currently in the UI schema form:")
        report_lines.append("")
        for field_name, field_data in sorted(missing_ui_fields):
            category = field_data["category"]
            description = field_data["description"]
            reason = get_reason_not_in_ui(field_name, category, ui_fields)
            report_lines.append(f"- **{field_name}** ({category}): {description}")
            report_lines.append(f"  - Reason: {reason}")
            report_lines.append("")
    else:
        report_lines.append("All non-system, non-nested fields from the canonical schema are represented in the UI.")
        report_lines.append("")
    
    # Write report
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
    
    print(f"Generated cross-reference report: {OUTPUT_FILE}")
    print(f"Total canonical fields: {total_fields}")
    print(f"Fields in UI: {in_ui_count}")
    print(f"Fields not in UI: {not_in_ui_count}")

if __name__ == "__main__":
    generate_report()
