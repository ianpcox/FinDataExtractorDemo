"""
Demo 6: ERP Staging
Demonstrates formatting approved invoices for ERP systems.
"""

import requests
import json
from pathlib import Path

API_BASE_URL = "http://localhost:8000"

def demo_erp_staging(invoice_id: str = None):
    """Demo: Stage invoice for ERP"""
    print("\n" + "="*60)
    print("DEMO 6: ERP Staging")
    print("="*60)
    
    # If no invoice_id, get one
    if not invoice_id:
        print("\n[INFO] Note: This demo requires an extracted invoice.")
        invoice_id = input("\nEnter invoice_id (or press Enter to skip): ").strip()
        if not invoice_id:
            print("Skipping ERP staging demo.")
            return None
    
    print(f"\n[STAGE] Staging invoice {invoice_id} for ERP...")
    
    # Stage invoice
    url = f"{API_BASE_URL}/api/staging/stage"
    
    try:
        payload = {
            "invoice_id": invoice_id,
            "erp_format": "json"  # Options: json, csv, xml, dynamics_gp
        }
        
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            
            print("\n[OK] Invoice Staged Successfully!")
            print(f"\n[INFO] Staging Results:")
            print(f"  Format: {result.get('format', 'N/A')}")
            print(f"  Invoice ID: {result.get('invoice_id', 'N/A')}")
            print(f"  Status: {result.get('status', 'N/A')}")
            
            # Save payload
            output_dir = Path(__file__).parent / "output"
            output_dir.mkdir(exist_ok=True)
            
            payload_data = result.get('payload', '')
            if payload_data:
                if result.get('format') == 'json':
                    output_file = output_dir / f"erp_payload_{invoice_id}.json"
                    with open(output_file, "w") as f:
                        json.dump(json.loads(payload_data), f, indent=2)
                else:
                    output_file = output_dir / f"erp_payload_{invoice_id}.{result.get('format', 'txt')}"
                    with open(output_file, "w") as f:
                        f.write(payload_data)
                
                print(f"\n[INFO] ERP Payload Saved: {output_file}")
                print(f"   File Size: {len(payload_data):,} bytes")
            
            # Show preview
            preview_url = f"{API_BASE_URL}/api/staging/invoice/{invoice_id}/preview"
            preview_response = requests.get(preview_url)
            
            if preview_response.status_code == 200:
                preview = preview_response.json()
                print(f"\n[PREVIEW] Preview:")
                print(f"  Voucher Type: {preview.get('voucher_type', 'N/A')}")
                print(f"  Vendor: {preview.get('vendor_name', 'N/A')}")
                print(f"  Invoice Number: {preview.get('invoice_number', 'N/A')}")
                print(f"  Total Amount: ${preview.get('total_amount', 0):,.2f}")
                print(f"  Line Items: {len(preview.get('line_items', []))}")
                
                if preview.get('approved_by'):
                    print(f"  Approved By: {preview.get('approved_by', {}).get('business_verifier', 'N/A')}")
            
            # Show different formats
            print(f"\n[INFO] Available Formats:")
            formats = ["json", "csv", "xml", "dynamics_gp"]
            for fmt in formats:
                print(f"  - {fmt.upper()}")
            
            return invoice_id
        else:
            print(f"\n[ERROR] Staging Failed: {response.status_code}")
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
    print("FIN DATA EXTRACTOR VANILLA - DEMO 6: ERP STAGING")
    print("="*60)
    
    # Run demo
    invoice_id = demo_erp_staging()
    
    print("\n" + "="*60)
    print("Demo 6 Complete!")
    print("="*60)
    
    print("\n[OK] All demos complete!")

