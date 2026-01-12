#!/usr/bin/env python3
"""Fill in descriptions for canonical fields CSV from the schema JSON file"""

import json
import csv
from pathlib import Path

SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"
CANONICAL_SCHEMA = SCHEMAS_DIR / "invoice.canonical.v1.schema.json"
CSV_FILE = Path(__file__).parent.parent / "invoice_canonical_fields.csv"

def get_schema_descriptions():
    """Load descriptions from the canonical schema"""
    with open(CANONICAL_SCHEMA, "r", encoding="utf-8") as f:
        schema = json.load(f)
    
    descriptions = {}
    properties = schema.get("properties", {})
    defs = schema.get("$defs", {})
    
    # Get descriptions from top-level properties
    for field_name, field_spec in properties.items():
        desc = field_spec.get("description", "")
        if desc:
            descriptions[field_name] = desc
    
    # Get descriptions from LineItem definition
    line_item_def = defs.get("LineItem", {})
    line_item_props = line_item_def.get("properties", {})
    for li_field_name, li_field_spec in line_item_props.items():
        desc = li_field_spec.get("description", "")
        if desc:
            descriptions[f"line_items[].{li_field_name}"] = desc
    
    # Get descriptions from Address definition
    address_def = defs.get("Address", {})
    address_props = address_def.get("properties", {})
    for addr_field_name, addr_field_spec in address_props.items():
        desc = addr_field_spec.get("description", "")
        if desc:
            # Store for all address types
            for addr_type in ["vendor_address", "bill_to_address", "remit_to_address"]:
                descriptions[f"{addr_type}.{addr_field_name}"] = desc
    
    return descriptions

def fill_descriptions():
    """Fill in descriptions from schema, with fallback defaults"""
    
    schema_descriptions = get_schema_descriptions()
    
    # Default descriptions for common fields
    default_descriptions = {
        "acceptance_percentage": "Acceptance percentage for partial payment",
        "bill_to_address": "Bill-to address (structured object with street, city, province, postal_code, country)",
        "bv_approval_date": "Business validation approval date",
        "bv_approval_notes": "Business validation approval notes",
        "bv_approver": "Business validation approver",
        "contract_id": "Contract identifier",
        "currency": "Currency code (e.g., CAD, USD)",
        "customer_id": "Customer identifier or account number",
        "customer_name": "Name of the customer/bill-to entity",
        "due_date": "Date payment is due",
        "entity": "Entity or organization name",
        "extensions": "Extended data for invoice subtypes (shift service, per diem travel, timesheet data)",
        "extraction_confidence": "Overall extraction confidence score (0.0 to 1.0)",
        "extraction_timestamp": "Timestamp when extraction was performed",
        "fa_approval_date": "Financial approval date",
        "fa_approval_notes": "Financial approval notes",
        "fa_approver": "Financial approval approver",
        "field_confidence": "Map of canonical_field_name -> confidence [0..1]",
        "file_name": "Original filename of the uploaded invoice",
        "file_path": "Path to the invoice file (local or Azure blob URL)",
        "id": "Database unique identifier",
        "invoice_date": "Date the invoice was issued",
        "invoice_number": "Vendor invoice identifier (not database id)",
        "invoice_subtype": "Invoice subtype (STANDARD_INVOICE, SHIFT_SERVICE_INVOICE, PER_DIEM_TRAVEL_INVOICE)",
        "line_items": "Array of line items (products/services) on the invoice",
        "payment_terms": "Payment terms (e.g., Net 30, Net 60)",
        "period_end": "End date of service period",
        "period_start": "Start date of service period",
        "po_number": "Purchase order number",
        "processing_state": "State machine status for extraction and validation workflow",
        "remit_to_name": "Name or entity for remittance",
        "standing_offer_number": "Standing offer number",
        "subtotal": "Subtotal amount before taxes and adjustments",
        "tax_amount": "Total tax amount",
        "tax_registration_number": "General tax registration number",
        "total_amount": "Final invoice total amount",
        "remit_to_address": "Remit-to address for payments (structured object with street, city, province, postal_code, country)",
        "remit_to_name": "Name or entity for remittance",
        "review_notes": "Notes from the reviewer",
        "review_status": "Human review status",
        "review_timestamp": "Timestamp when review was completed",
        "review_version": "Optimistic locking version for concurrent edit protection",
        "reviewer": "User who reviewed the invoice",
        "status": "Invoice status (processing, extracted, validated, in_review, approved, rejected)",
        "subtotal": "Subtotal amount before taxes and adjustments",
        "tax_amount": "Total tax amount",
        "tax_breakdown": "Detailed breakdown of tax amounts by type",
        "tax_registration_number": "General tax registration number",
        "total_amount": "Final invoice total amount",
        "updated_at": "Last update timestamp (auto-updated)",
        "upload_date": "Date and time when the invoice was uploaded",
        "vendor_address": "Vendor/supplier address (structured object with street, city, province, postal_code, country)",
        "vendor_id": "Vendor identifier or account number",
        "vendor_name": "Name of the vendor/supplier",
        "vendor_phone": "Vendor phone number",
        # Line item fields
        "line_items[].line_number": "Line item number (1-based)",
        "line_items[].description": "Line item description",
        "line_items[].quantity": "Quantity",
        "line_items[].unit_price": "Unit price",
        "line_items[].amount": "Line item total amount",
        "line_items[].confidence": "Extraction confidence (0-1)",
        "line_items[].unit_of_measure": "Unit of measure (e.g., 'each', 'hours')",
        "line_items[].tax_rate": "Tax rate for this line item",
        "line_items[].tax_amount": "Tax amount for this line item",
        "line_items[].gst_amount": "GST amount for this line item",
        "line_items[].pst_amount": "PST amount for this line item",
        "line_items[].qst_amount": "QST amount for this line item",
        "line_items[].combined_tax": "Combined tax amount",
        "line_items[].project_code": "Project code",
        "line_items[].region_code": "Region code",
        "line_items[].airport_code": "Airport code",
        "line_items[].cost_centre_code": "Cost centre code",
    }
    
    # Address sub-field descriptions
    address_field_descriptions = {
        "street": "Street address",
        "city": "City",
        "province": "Province/State",
        "postal_code": "Postal/ZIP code",
        "country": "Country",
    }
    
    for addr_type in ["vendor_address", "bill_to_address", "remit_to_address"]:
        for addr_field, desc in address_field_descriptions.items():
            default_descriptions[f"{addr_type}.{addr_field}"] = f"{desc} (for {addr_type.replace('_', ' ').title()})"
    
    # Read CSV
    rows = []
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            field_name = row["Field Name"]
            current_desc = row.get("Description", "").strip()
            
            # Fill in description if empty
            if not current_desc:
                # Try schema first, then defaults
                if field_name in schema_descriptions:
                    row["Description"] = schema_descriptions[field_name]
                elif field_name in default_descriptions:
                    row["Description"] = default_descriptions[field_name]
                else:
                    # Keep empty if no description available
                    row["Description"] = ""
            
            rows.append(row)
    
    # Write updated CSV
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    # Count filled descriptions
    filled_count = sum(1 for row in rows if row.get("Description", "").strip())
    total_count = len(rows)
    
    print(f"Updated {CSV_FILE}")
    print(f"Fields with descriptions: {filled_count} / {total_count}")
    print(f"Fields still missing descriptions: {total_count - filled_count}")

if __name__ == "__main__":
    fill_descriptions()
