"""
Demo 5: HITL (Human-in-the-Loop) Review
Demonstrates reviewing and validating extracted invoice data.
"""

import requests
import json

API_BASE_URL = "http://localhost:8000"

def demo_hitl_review(invoice_id: str = None):
    """Demo: Review and validate invoice"""
    print("\n" + "="*60)
    print("DEMO 5: HITL Review & Validation")
    print("="*60)
    
    # If no invoice_id, get one
    if not invoice_id:
        print("\n[INFO] Note: This demo requires an extracted invoice.")
        invoice_id = input("\nEnter invoice_id (or press Enter to skip): ").strip()
        if not invoice_id:
            print("Skipping HITL review demo.")
            return None
    
    print(f"\n[REVIEW] Reviewing invoice: {invoice_id}")
    
    # Get invoice for review
    url = f"{API_BASE_URL}/api/hitl/invoice/{invoice_id}"
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            invoice = response.json()
            
            print("\n[OK] Invoice Retrieved for Review")
            print(f"\n[INFO] Invoice Data:")
            print(f"  Invoice Number: {invoice.get('invoice_number', 'N/A')}")
            print(f"  Invoice Date: {invoice.get('invoice_date', 'N/A')}")
            print(f"  Vendor: {invoice.get('vendor_name', 'N/A')}")
            print(f"  Total: ${invoice.get('total_amount', 0):,.2f}")
            print(f"  Status: {invoice.get('status', 'N/A')}")
            
            # Field confidence
            field_confidence = invoice.get('field_confidence', {})
            if field_confidence:
                print(f"\n[INFO] Field Confidence Scores:")
                low_confidence_fields = []
                
                for field, confidence in field_confidence.items():
                    icon = "[OK]" if confidence >= 0.9 else "[WARN]" if confidence >= 0.7 else "[LOW]"
                    print(f"  {icon} {field}: {confidence:.1%}")
                    
                    if confidence < 0.7:
                        low_confidence_fields.append(field)
                
                if low_confidence_fields:
                    print(f"\n[WARN] Fields Requiring Review:")
                    for field in low_confidence_fields:
                        print(f"    - {field} (confidence: {field_confidence[field]:.1%})")
            
            # Line items
            line_items = invoice.get('line_items', [])
            if line_items:
                print(f"\n[INFO] Line Items ({len(line_items)}):")
                for i, item in enumerate(line_items[:5], 1):
                    conf = item.get('confidence', 0)
                    icon = "[OK]" if conf >= 0.9 else "[WARN]" if conf >= 0.7 else "[LOW]"
                    print(f"  {icon} {i}. {item.get('description', 'N/A')[:40]}")
                    print(f"     Amount: ${item.get('amount', 0):,.2f} (confidence: {conf:.1%})")
            
            # Validate invoice (demo)
            print(f"\n[VALIDATE] Validating Invoice...")
            validate_url = f"{API_BASE_URL}/api/hitl/invoice/validate"
            
            # Sample validation update
            validation_data = {
                "invoice_id": invoice_id,
                "validated_fields": {
                    "invoice_number": invoice.get('invoice_number'),
                    "total_amount": invoice.get('total_amount')
                },
                "validation_notes": "Demo validation - all fields confirmed",
                "validator": "demo_user"
            }
            
            validate_response = requests.post(validate_url, json=validation_data)
            
            if validate_response.status_code == 200:
                print("[OK] Invoice Validated Successfully!")
                result = validate_response.json()
                print(f"  Validated By: {result.get('validator', 'N/A')}")
                print(f"  Validation Date: {result.get('validation_date', 'N/A')}")
            else:
                print(f"[WARN] Validation response: {validate_response.status_code}")
            
            return invoice_id
        else:
            print(f"\n[ERROR] Failed to retrieve invoice: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print(f"\n[ERROR] Cannot connect to API at {API_BASE_URL}")
        print("   Make sure the API server is running.")
        return None
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        return None


if __name__ == "__main__":
    print("\n" + "="*60)
    print("FIN DATA EXTRACTOR VANILLA - DEMO 5: HITL REVIEW")
    print("="*60)
    
    # Run demo
    invoice_id = demo_hitl_review()
    
    print("\n" + "="*60)
    print("Demo 5 Complete!")
    print("="*60)
    
    if invoice_id:
        print(f"\n[INFO] Next: Use invoice_id '{invoice_id}' for Demo 6 (ERP Staging)")

