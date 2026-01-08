"""
Diagnostic script to investigate why DI detects address fields but doesn't extract content.

Tests specific PDFs to inspect raw DI API responses for address fields.
"""

import sys
import os
from pathlib import Path
import json
from typing import Dict, Any, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.extraction.document_intelligence_client import DocumentIntelligenceClient
from src.ingestion.file_handler import FileHandler
from src.config import settings

# Reconfigure stdout for Unicode
sys.stdout.reconfigure(encoding='utf-8')


def inspect_di_address_field(fields: Dict, field_name: str) -> Dict[str, Any]:
    """Inspect a specific address field from DI response"""
    field = fields.get(field_name)
    
    if not field:
        return {"exists": False, "reason": "Field not found in DI response"}
    
    result = {
        "exists": True,
        "has_value": hasattr(field, 'value'),
        "value_type": None,
        "value": None,
        "confidence": getattr(field, 'confidence', None),
        "raw_field": str(field),
    }
    
    if hasattr(field, 'value'):
        value = field.value
        result["value_type"] = type(value).__name__
        
        if value is None:
            result["value"] = None
            result["reason"] = "Field has value attribute but value is None"
        elif isinstance(value, dict):
            result["value"] = value
            result["value_keys"] = list(value.keys())
            result["value_items"] = {k: v for k, v in value.items() if v is not None}
            # Check if dict has any non-empty values
            has_content = any(v for v in value.values() if v is not None and (not isinstance(v, str) or v.strip()))
            result["has_content"] = has_content
            if not has_content:
                result["reason"] = "Address dict exists but all values are None/empty"
        elif isinstance(value, str):
            result["value"] = value
            result["has_content"] = bool(value and value.strip())
            if not result["has_content"]:
                result["reason"] = "Address is string but empty"
        else:
            result["value"] = str(value)
            result["reason"] = f"Address value is unexpected type: {type(value)}"
    else:
        result["reason"] = "Field exists but has no 'value' attribute"
    
    return result


def diagnose_pdf(pdf_path: str) -> Dict[str, Any]:
    """Diagnose address extraction for a single PDF"""
    pdf_name = os.path.basename(pdf_path)
    print(f"\n{'='*100}")
    print(f"DIAGNOSING: {pdf_name}")
    print(f"{'='*100}\n")
    
    result = {
        "pdf_name": pdf_name,
        "pdf_path": pdf_path,
        "address_fields": {},
        "raw_di_response": None,
        "extraction_result": None,
    }
    
    try:
        # Initialize clients
        di_client = DocumentIntelligenceClient()
        file_handler = FileHandler()
        
        # Read PDF
        print(f"Reading PDF: {pdf_path}")
        with open(pdf_path, 'rb') as f:
            file_content = f.read()
        print(f"PDF size: {len(file_content):,} bytes\n")
        
        # Call DI API
        print("Calling Azure Document Intelligence API...")
        di_response = di_client.analyze_invoice(file_content)
        
        if not di_response or di_response.get("error"):
            error_msg = di_response.get("error", "Unknown error") if di_response else "No response"
            print(f"ERROR: DI API failed: {error_msg}")
            result["error"] = error_msg
            return result
        
        print("DI API call successful\n")
        
        # Extract fields using DI client's internal method
        print("Extracting invoice fields from DI response...")
        invoice_data = di_client._extract_invoice_fields(di_response)
        
        # Inspect address fields in raw DI response
        if "documents" in di_response and len(di_response["documents"]) > 0:
            doc = di_response["documents"][0]
            fields = doc.fields if hasattr(doc, 'fields') else {}
            
            print("="*100)
            print("RAW DI RESPONSE - ADDRESS FIELD INSPECTION")
            print("="*100)
            
            address_field_names = ["VendorAddress", "CustomerAddress", "BillToAddress", "RemitToAddress", "RemittanceAddress"]
            
            for addr_field_name in address_field_names:
                print(f"\n--- {addr_field_name} ---")
                inspection = inspect_di_address_field(fields, addr_field_name)
                result["address_fields"][addr_field_name] = inspection
                
                print(f"Exists in DI response: {inspection['exists']}")
                if inspection['exists']:
                    print(f"Has value attribute: {inspection['has_value']}")
                    print(f"Confidence: {inspection.get('confidence', 'N/A')}")
                    print(f"Value type: {inspection.get('value_type', 'N/A')}")
                    
                    if inspection.get('value') is not None:
                        if isinstance(inspection['value'], dict):
                            print(f"Value (dict): {json.dumps(inspection['value'], indent=2, default=str)}")
                            print(f"Dict keys: {inspection.get('value_keys', [])}")
                            print(f"Non-empty items: {json.dumps(inspection.get('value_items', {}), indent=2, default=str)}")
                            print(f"Has content: {inspection.get('has_content', False)}")
                        else:
                            print(f"Value: {inspection['value']}")
                            print(f"Has content: {inspection.get('has_content', False)}")
                    
                    if 'reason' in inspection:
                        print(f"⚠️  Issue: {inspection['reason']}")
        
        # Check what our extraction code extracted
        print("\n" + "="*100)
        print("EXTRACTED DATA - ADDRESS FIELDS")
        print("="*100)
        
        extracted_addresses = {
            "vendor_address": invoice_data.get("vendor_address"),
            "bill_to_address": invoice_data.get("bill_to_address"),
            "remit_to_address": invoice_data.get("remit_to_address"),
        }
        
        for field_name, value in extracted_addresses.items():
            print(f"\n--- {field_name} ---")
            if value is None:
                print("❌ Not extracted (None)")
            elif isinstance(value, dict):
                has_content = any(v for v in value.values() if v is not None and (not isinstance(v, str) or v.strip()))
                print(f"✅ Extracted as dict: {json.dumps(value, indent=2, default=str)}")
                print(f"Has content: {has_content}")
                if not has_content:
                    print("⚠️  Dict exists but all values are None/empty")
            else:
                print(f"✅ Extracted: {value}")
        
        # Check field confidence
        print("\n" + "="*100)
        print("FIELD CONFIDENCE SCORES")
        print("="*100)
        
        field_confidence = invoice_data.get("field_confidence", {})
        for addr_field_name in ["VendorAddress", "CustomerAddress", "BillToAddress", "RemitToAddress", "RemittanceAddress"]:
            conf = field_confidence.get(addr_field_name)
            if conf is not None:
                print(f"{addr_field_name}: {conf}")
        
        result["extraction_result"] = {
            "vendor_address": extracted_addresses["vendor_address"],
            "bill_to_address": extracted_addresses["bill_to_address"],
            "remit_to_address": extracted_addresses["remit_to_address"],
            "field_confidence": {k: v for k, v in field_confidence.items() if "Address" in k},
        }
        
        # Store raw DI response structure (without full content)
        if "documents" in di_response:
            result["raw_di_response"] = {
                "document_count": len(di_response["documents"]),
                "field_names": list(fields.keys()) if hasattr(doc, 'fields') and doc.fields else [],
            }
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        result["error"] = str(e)
    
    return result


def main():
    """Main entry point"""
    # PDF paths
    pdf_base_path = Path("data/sample_invoices/Raw/Raw_Basic")
    
    pdfs_to_test = [
        "ACC012 4202092525.pdf",
        "ANA005 90443097.pdf",
        "HYD001 5160530790NOV2025.pdf",
        "TEL006 4222600.pdf",
        "ENB001 166574659065NOV2025.pdf",
    ]
    
    results = []
    
    for pdf_name in pdfs_to_test:
        pdf_path = pdf_base_path / pdf_name
        
        if not pdf_path.exists():
            print(f"⚠️  PDF not found: {pdf_path}")
            continue
        
        result = diagnose_pdf(str(pdf_path))
        results.append(result)
    
    # Summary
    print("\n" + "="*100)
    print("SUMMARY")
    print("="*100)
    
    for result in results:
        if "error" in result:
            print(f"\n{result['pdf_name']}: ERROR - {result['error']}")
            continue
        
        print(f"\n{result['pdf_name']}:")
        
        # Check each address field
        for addr_field_name, inspection in result.get("address_fields", {}).items():
            if inspection.get("exists"):
                has_content = inspection.get("has_content", False)
                status = "✅ Has content" if has_content else "❌ No content"
                print(f"  {addr_field_name}: {status}")
                if not has_content and "reason" in inspection:
                    print(f"    Reason: {inspection['reason']}")
        
        # Check extracted addresses
        extracted = result.get("extraction_result", {})
        for field_name in ["vendor_address", "bill_to_address", "remit_to_address"]:
            value = extracted.get(field_name)
            if value is None:
                print(f"  {field_name}: ❌ Not extracted")
            elif isinstance(value, dict):
                has_content = any(v for v in value.values() if v is not None and (not isinstance(v, str) or v.strip()))
                status = "✅ Extracted with content" if has_content else "⚠️  Extracted but empty"
                print(f"  {field_name}: {status}")
    
    # Save detailed results
    output_file = "address_extraction_diagnosis.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n\nDetailed results saved to: {output_file}")


if __name__ == "__main__":
    main()
