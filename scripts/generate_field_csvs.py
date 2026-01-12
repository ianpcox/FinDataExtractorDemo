#!/usr/bin/env python3
"""Generate CSV files for canonical schema fields and UI fields from invoice schemas"""

import json
import csv
from pathlib import Path

# Paths
SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"
CANONICAL_SCHEMA = SCHEMAS_DIR / "invoice.canonical.v1.schema.json"
CONTRACT_SCHEMA = SCHEMAS_DIR / "invoice.contract.v1.json"
OUTPUT_DIR = Path(__file__).parent.parent

def get_field_type(schema_prop):
    """Extract field type from JSON schema property"""
    if "anyOf" in schema_prop:
        # Check for $ref to determine type
        for item in schema_prop["anyOf"]:
            if "$ref" in item:
                ref = item["$ref"]
                if "decimalString" in ref:
                    return "decimal_string"
                elif "isoDate" in ref:
                    return "date"
                elif "isoDateTime" in ref:
                    return "datetime"
                elif "Address" in ref:
                    return "address_object"
            elif "type" in item:
                return item["type"]
    elif "$ref" in schema_prop:
        ref = schema_prop["$ref"]
        if "decimalString" in ref:
            return "decimal_string"
        elif "isoDate" in ref:
            return "date"
        elif "isoDateTime" in ref:
            return "datetime"
        elif "Address" in ref:
            return "address_object"
    elif "type" in schema_prop:
        if isinstance(schema_prop["type"], list):
            return ", ".join(schema_prop["type"])
        return schema_prop["type"]
    return "unknown"

def is_required(field_name, required_list):
    """Check if field is in required list"""
    return field_name in required_list if required_list else False

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

def generate_canonical_csv():
    """Generate CSV for canonical schema fields"""
    with open(CANONICAL_SCHEMA, "r", encoding="utf-8") as f:
        schema = json.load(f)
    
    properties = schema.get("properties", {})
    required_fields = schema.get("required", [])
    defs = schema.get("$defs", {})
    
    rows = []
    for field_name, field_spec in sorted(properties.items()):
        field_type = get_field_type(field_spec)
        description = field_spec.get("description", "")
        required = is_required(field_name, required_fields)
        nullable = "anyOf" in field_spec or field_spec.get("type") == ["string", "null"] or "null" in str(field_spec.get("type", ""))
        
        rows.append({
            "Field Name": field_name,
            "Type": field_type,
            "Required": "Yes" if required else "No",
            "Nullable": "Yes" if nullable else "No",
            "Description": description,
            "Category": get_category(field_name)
        })
    
    # Add line item fields (nested) - extract from schema
    line_item_def = defs.get("LineItem", {})
    line_item_props = line_item_def.get("properties", {})
    line_item_required = line_item_def.get("required", [])
    
    for li_field_name, li_field_spec in sorted(line_item_props.items()):
        li_field_type = get_field_type(li_field_spec)
        li_description = li_field_spec.get("description", "")
        li_required = li_field_name in line_item_required if line_item_required else False
        li_nullable = "anyOf" in li_field_spec or li_field_spec.get("type") == ["string", "null"] or "null" in str(li_field_spec.get("type", ""))
        
        if not li_description:
            # Provide default descriptions
            descriptions = {
                "line_number": "Line item number (1-based)",
                "description": "Line item description",
                "quantity": "Quantity",
                "unit_price": "Unit price",
                "amount": "Line item total amount",
                "confidence": "Extraction confidence (0-1)",
                "unit_of_measure": "Unit of measure (e.g., 'each', 'hours')",
                "tax_rate": "Tax rate for this line item",
                "tax_amount": "Tax amount for this line item",
                "gst_amount": "GST amount for this line item",
                "pst_amount": "PST amount for this line item",
                "qst_amount": "QST amount for this line item",
                "combined_tax": "Combined tax amount",
                "project_code": "Project code",
                "region_code": "Region code",
                "airport_code": "Airport code",
                "cost_centre_code": "Cost centre code",
            }
            li_description = descriptions.get(li_field_name, "")
        
        rows.append({
            "Field Name": f"line_items[].{li_field_name}",
            "Type": li_field_type,
            "Required": "Yes" if li_required else "No",
            "Nullable": "Yes" if li_nullable else "No",
            "Description": li_description,
            "Category": "Line Items"
        })
    
    # Add address fields (nested)
    address_def = defs.get("Address", {})
    address_props = address_def.get("properties", {})
    
    for addr_field_name, addr_field_spec in sorted(address_props.items()):
        addr_field_type = get_field_type(addr_field_spec)
        addr_description = addr_field_spec.get("description", "")
        if not addr_description:
            descriptions = {
                "street": "Street address",
                "city": "City",
                "province": "Province/State",
                "postal_code": "Postal/ZIP code",
                "country": "Country",
            }
            addr_description = descriptions.get(addr_field_name, "")
        
        for addr_field in ["vendor_address", "bill_to_address", "remit_to_address"]:
            category = get_category(addr_field)
            rows.append({
                "Field Name": f"{addr_field}.{addr_field_name}",
                "Type": addr_field_type,
                "Required": "No",  # Address sub-fields are not directly required
                "Nullable": "Yes",
                "Description": f"{addr_description} (for {addr_field.replace('_', ' ').title()})",
                "Category": category
            })
    
    output_file = OUTPUT_DIR / "invoice_canonical_fields.csv"
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Field Name", "Type", "Required", "Nullable", "Description", "Category"])
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Generated {output_file} with {len(rows)} fields")
    return output_file

def generate_ui_fields_csv():
    """Generate CSV for UI fields (from contract schema)"""
    with open(CONTRACT_SCHEMA, "r", encoding="utf-8") as f:
        contract = json.load(f)
    
    fields = contract.get("fields", {})
    confidence_policy = contract.get("confidence_policy", {})
    required_fields = confidence_policy.get("required_fields", [])
    important_fields = confidence_policy.get("important_fields", [])
    
    rows = []
    for field_name, field_spec in sorted(fields.items()):
        field_type = field_spec.get("type", "")
        required = field_spec.get("required", False)
        nullable = field_spec.get("nullable", True)
        description = field_spec.get("description", "")
        parsers = ", ".join(field_spec.get("parsers", []))
        di_fields = ", ".join(field_spec.get("di_fields", []))
        legacy_fields = ", ".join(field_spec.get("legacy_fields", []))
        match_role = field_spec.get("match_role", "")
        overlay_role = field_spec.get("overlay_role", "")
        confidence_required = field_spec.get("confidence_required", False)
        is_important = field_name in important_fields
        
        rows.append({
            "Field Name": field_name,
            "Type": field_type,
            "Required": "Yes" if required else "No",
            "Nullable": "Yes" if nullable else "No",
            "Description": description,
            "DI Field Names": di_fields,
            "Legacy Field Names": legacy_fields,
            "Parsers": parsers,
            "Match Role": match_role,
            "Overlay Role": overlay_role,
            "Confidence Required": "Yes" if confidence_required else "No",
            "Important Field": "Yes" if is_important else "No"
        })
    
    output_file = OUTPUT_DIR / "invoice_ui_fields.csv"
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "Field Name", "Type", "Required", "Nullable", "Description",
            "DI Field Names", "Legacy Field Names", "Parsers",
            "Match Role", "Overlay Role", "Confidence Required", "Important Field"
        ])
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Generated {output_file} with {len(rows)} fields")
    return output_file

if __name__ == "__main__":
    print("Generating CSV files for invoice fields...")
    canonical_file = generate_canonical_csv()
    ui_file = generate_ui_fields_csv()
    print(f"\nGenerated files:")
    print(f"  - {canonical_file}")
    print(f"  - {ui_file}")
