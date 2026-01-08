"""
Demo 3: PO Matching
Demonstrates matching invoices to purchase orders.
"""

import requests
import json

API_BASE_URL = "http://localhost:8000"

def demo_po_matching(invoice_id: str = None):
    """Demo: Match invoice to purchase order"""
    print("\n" + "="*60)
    print("DEMO 3: PO Matching")
    print("="*60)
    
    # If no invoice_id, get one from extraction demo
    if not invoice_id:
        print("\n[INFO] Note: This demo requires an extracted invoice.")
        print("   Run Demo 2 (Extraction) first, or provide invoice_id as argument.")
        invoice_id = input("\nEnter invoice_id (or press Enter to skip): ").strip()
        if not invoice_id:
            print("Skipping PO matching demo.")
            return None
    
    # Sample PO data (in real scenario, this would come from PO database)
    po_data = {
        "po_number": "PO-12345",
        "po_date": "2024-01-05",
        "vendor_name": "Acme Corp",
        "vendor_code": "ACME001",
        "total_amount": 1500.00,
        "line_items": []
    }
    
    print(f"\n[MATCH] Matching invoice {invoice_id} to PO...")
    print(f"\n[INFO] Purchase Order Data:")
    print(f"  PO Number: {po_data['po_number']}")
    print(f"  Vendor: {po_data['vendor_name']}")
    print(f"  Amount: ${po_data['total_amount']:,.2f}")
    
    # Match invoice to PO
    url = f"{API_BASE_URL}/api/matching/match"
    
    try:
        payload = {
            "invoice_id": invoice_id,
            "po_data": po_data
        }
        
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            match = result.get("match", {})
            
            print("\n[OK] Matching Complete!")
            print(f"\n[INFO] Match Results:")
            print(f"  Matched: {'Yes' if match.get('matched') else 'No'}")
            print(f"  Confidence: {match.get('confidence', 0):.1%}")
            print(f"  Strategy: {match.get('match_strategy', 'N/A')}")
            print(f"  PO Number: {match.get('matched_document_number', 'N/A')}")
            
            # Match details
            details = match.get('match_details', {})
            if details:
                print(f"\n[INFO] Match Details:")
                if 'vendor_match' in details:
                    print(f"  Vendor Match: {details['vendor_match']}")
                if 'amount_match' in details:
                    print(f"  Amount Match: {details['amount_match']}")
                if 'amount_diff' in details:
                    print(f"  Amount Difference: ${details['amount_diff']:,.2f}")
                if 'date_diff_days' in details:
                    print(f"  Date Difference: {details['date_diff_days']} days")
            
            # Validation results
            validation = result.get("validation", {})
            if validation:
                print(f"\n[OK] Validation Results:")
                print(f"  Amount Valid: {validation.get('amount_valid', 'N/A')}")
                print(f"  Date Valid: {validation.get('date_valid', 'N/A')}")
                if validation.get('warnings'):
                    print(f"  Warnings: {len(validation['warnings'])}")
                    for warning in validation['warnings'][:3]:
                        print(f"    - {warning}")
            
            return invoice_id
        else:
            print(f"\n[ERROR] Matching Failed: {response.status_code}")
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
    print("FIN DATA EXTRACTOR VANILLA - DEMO 3: PO MATCHING")
    print("="*60)
    
    # Run demo
    invoice_id = demo_po_matching()
    
    print("\n" + "="*60)
    print("Demo 3 Complete!")
    print("="*60)
    
    if invoice_id:
        print(f"\n[INFO] Next: Use invoice_id '{invoice_id}' for Demo 4 (PDF Overlay)")

