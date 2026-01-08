"""
Diagnose address extraction for a single PDF to inspect raw DI API response.

This will call the DI API once and show the exact structure of address fields.
"""

import sys
import os
from pathlib import Path
import json
from typing import Dict, Any

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.extraction.document_intelligence_client import DocumentIntelligenceClient
from src.config import settings

sys.stdout.reconfigure(encoding='utf-8')

# Test with one PDF first
pdf_path = Path("data/sample_invoices/Raw/Raw_Basic/ANA005 90443097.pdf")

if not pdf_path.exists():
    print(f"PDF not found: {pdf_path}")
    sys.exit(1)

print("="*100)
print(f"DIAGNOSING ADDRESS EXTRACTION: {pdf_path.name}")
print("="*100)

# Initialize DI client
di_client = DocumentIntelligenceClient()

# Read PDF
print(f"\nReading PDF: {pdf_path}")
with open(pdf_path, 'rb') as f:
    file_content = f.read()
print(f"PDF size: {len(file_content):,} bytes")

# Call DI API directly to get raw result
print("\nCalling Azure Document Intelligence API...")
print("(This may take 10-30 seconds...)")

try:
    # Get raw DI result (before processing)
    from azure.core.exceptions import HttpResponseError, AzureError
    
    poller = di_client.client.begin_analyze_document(
        model_id=di_client.model_id,
        document=file_content
    )
    raw_result = poller.result()
    
    print("✅ DI API call successful\n")
    
    # Inspect raw response structure
    if not hasattr(raw_result, 'documents') or not raw_result.documents:
        print("❌ No documents in DI response")
        sys.exit(1)
    
    print(f"Found {len(raw_result.documents)} document(s)\n")
    
    doc = raw_result.documents[0]
    fields = doc.fields if hasattr(doc, 'fields') else {}
    
    print("="*100)
    print("RAW DI RESPONSE - ADDRESS FIELD DETAILS")
    print("="*100)
    print(f"\nTotal fields in DI response: {len(fields)}")
    print(f"Field names containing 'Address': {[k for k in fields.keys() if 'Address' in k]}")
    print(f"All field names: {list(fields.keys())[:20]}...")  # Show first 20
    
    address_field_names = ["VendorAddress", "CustomerAddress", "BillToAddress", "RemitToAddress", "RemittanceAddress"]
    
    for addr_field_name in address_field_names:
        field = fields.get(addr_field_name)
        
        print(f"\n{'─'*100}")
        print(f"FIELD: {addr_field_name}")
        print(f"{'─'*100}")
        
        if not field:
            print("❌ Field not found in DI response")
            continue
        
        print(f"✅ Field exists in DI response")
        print(f"   Field type: {type(field).__name__}")
        print(f"   Has 'value' attribute: {hasattr(field, 'value')}")
        print(f"   Has 'confidence' attribute: {hasattr(field, 'confidence')}")
        
        if hasattr(field, 'confidence'):
            conf = field.confidence
            print(f"   Confidence: {conf}")
        
        if hasattr(field, 'value'):
            value = field.value
            print(f"   Value type: {type(value).__name__}")
            print(f"   Value is None: {value is None}")
            
            if value is None:
                print("   ⚠️  Value is None - DI detected field but has no value")
            elif isinstance(value, dict):
                print(f"   Value (dict):")
                print(f"     Keys: {list(value.keys())}")
                
                # Show all key-value pairs
                has_any_content = False
                for key, val in value.items():
                    is_empty = val is None or (isinstance(val, str) and not val.strip())
                    status = "✅" if not is_empty else "❌"
                    print(f"     {status} {key}: {repr(val)}")
                    if not is_empty:
                        has_any_content = True
                
                if not has_any_content:
                    print("   ⚠️  Dict exists but all values are None/empty")
                else:
                    print("   ✅ Dict has at least one non-empty value")
                
                # Show JSON representation
                print(f"\n   Full dict (JSON):")
                print(json.dumps(value, indent=6, default=str))
                
            elif isinstance(value, str):
                print(f"   Value (string): {repr(value)}")
                if not value.strip():
                    print("   ⚠️  String is empty")
                else:
                    print("   ✅ String has content")
            else:
                print(f"   Value: {repr(value)}")
                print(f"   ⚠️  Unexpected value type")
        else:
            print("   ⚠️  Field has no 'value' attribute")
    
    # Test our extraction method
    print("\n" + "="*100)
    print("OUR EXTRACTION METHOD RESULTS")
    print("="*100)
    
    invoice_data = di_client._extract_invoice_fields(raw_result)
    
    for field_name in ["vendor_address", "bill_to_address", "remit_to_address"]:
        value = invoice_data.get(field_name)
        print(f"\n{field_name}:")
        if value is None:
            print("  ❌ Not extracted (returned None)")
        elif isinstance(value, dict):
            has_content = any(v for v in value.values() if v is not None and (not isinstance(v, str) or v.strip()))
            if has_content:
                print(f"  ✅ Extracted: {json.dumps(value, indent=4, default=str)}")
            else:
                print(f"  ⚠️  Extracted but empty: {json.dumps(value, indent=4, default=str)}")
        else:
            print(f"  ✅ Extracted: {value}")
    
    # Check field confidence extraction
    print("\n" + "="*100)
    print("FIELD CONFIDENCE EXTRACTION")
    print("="*100)
    
    field_confidence = invoice_data.get("field_confidence", {})
    for addr_field_name in ["VendorAddress", "CustomerAddress", "BillToAddress", "RemitToAddress", "RemittanceAddress"]:
        conf = field_confidence.get(addr_field_name)
        raw_field = fields.get(addr_field_name)
        raw_conf = getattr(raw_field, 'confidence', None) if raw_field else None
        
        print(f"\n{addr_field_name}:")
        print(f"  Raw DI confidence: {raw_conf}")
        print(f"  Extracted confidence: {conf}")
        
        if raw_conf is not None and conf is None:
            print("  ⚠️  Confidence exists in DI but not extracted")
        elif raw_conf is None and conf is not None:
            print("  ⚠️  Confidence extracted but not in DI (unexpected)")
        elif raw_conf == conf:
            print("  ✅ Confidence matches")
        else:
            print("  ⚠️  Confidence mismatch")
    
    # Save raw response for inspection
    output_file = "di_raw_response_sample.json"
    # Convert to serializable format
    serializable_response = {}
    if hasattr(raw_result, 'documents') and raw_result.documents:
        doc = raw_result.documents[0]
        serializable_response["document_confidence"] = getattr(doc, 'confidence', None)
        if hasattr(doc, 'fields'):
            serializable_response["all_fields"] = list(doc.fields.keys())
            serializable_response["address_fields"] = {}
            for field_name, field in doc.fields.items():
                if "Address" in field_name or "address" in field_name.lower():
                    field_data = {
                        "has_value": hasattr(field, 'value'),
                        "has_confidence": hasattr(field, 'confidence'),
                    }
                    if hasattr(field, 'value'):
                        val = field.value
                        field_data["value"] = val
                        field_data["value_type"] = type(val).__name__
                        if isinstance(val, dict):
                            field_data["value_keys"] = list(val.keys())
                            field_data["value_items"] = {k: v for k, v in val.items()}
                    if hasattr(field, 'confidence'):
                        field_data["confidence"] = field.confidence
                    serializable_response["address_fields"][field_name] = field_data
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(serializable_response, f, indent=2, default=str)
    
    print(f"\n\nRaw DI response (address fields only) saved to: {output_file}")
    
    # Also print summary
    if serializable_response.get("address_fields"):
        print("\n" + "="*100)
        print("SUMMARY OF ADDRESS FIELDS IN DI RESPONSE")
        print("="*100)
        for field_name, field_data in serializable_response["address_fields"].items():
            print(f"\n{field_name}:")
            print(f"  Has value: {field_data.get('has_value')}")
            print(f"  Has confidence: {field_data.get('has_confidence')}")
            if field_data.get('value') is not None:
                print(f"  Value type: {field_data.get('value_type')}")
                if isinstance(field_data.get('value'), dict):
                    value_dict = field_data.get('value', {})
                    print(f"  Value keys: {list(value_dict.keys())}")
                    non_empty = {k: v for k, v in value_dict.items() if v is not None and (not isinstance(v, str) or v.strip())}
                    if non_empty:
                        print(f"  ✅ Has content: {non_empty}")
                    else:
                        print(f"  ❌ All values empty: {value_dict}")
            else:
                print(f"  ❌ Value is None")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
