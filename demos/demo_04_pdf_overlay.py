"""
Demo 4: PDF Overlay
Demonstrates adding visual overlay to invoice PDFs.
"""

import requests
from pathlib import Path

API_BASE_URL = "http://localhost:8000"

def demo_pdf_overlay(invoice_id: str = None):
    """Demo: Generate PDF with overlay"""
    print("\n" + "="*60)
    print("DEMO 4: PDF Overlay")
    print("="*60)
    
    # If no invoice_id, get one
    if not invoice_id:
        print("\n[INFO] Note: This demo requires an extracted invoice.")
        invoice_id = input("\nEnter invoice_id (or press Enter to skip): ").strip()
        if not invoice_id:
            print("Skipping PDF overlay demo.")
            return None
    
    print(f"\n[OVERLAY] Generating PDF overlay for invoice: {invoice_id}")
    
    # Get overlay PDF
    url = f"{API_BASE_URL}/api/overlay/{invoice_id}"
    
    try:
        response = requests.get(url)
        
        if response.status_code == 200:
            # Save PDF
            output_dir = Path(__file__).parent / "output"
            output_dir.mkdir(exist_ok=True)
            
            output_file = output_dir / f"overlay_{invoice_id}.pdf"
            
            with open(output_file, "wb") as f:
                f.write(response.content)
            
            print("\n[OK] Overlay Generated Successfully!")
            print(f"\n[INFO] Output File: {output_file}")
            print(f"   File Size: {len(response.content):,} bytes")
            
            print("\n[INFO] Overlay Includes:")
            print("  - Invoice header information")
            print("  - Financial coding (red box)")
            print("  - Approval status")
            print("  - Extracted data summary")
            
            print(f"\n[INFO] Open the PDF to see the overlay:")
            print(f"   {output_file.absolute()}")
            
            return invoice_id
        else:
            print(f"\n[ERROR] Overlay Generation Failed: {response.status_code}")
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
    print("FIN DATA EXTRACTOR VANILLA - DEMO 4: PDF OVERLAY")
    print("="*60)
    
    # Run demo
    invoice_id = demo_pdf_overlay()
    
    print("\n" + "="*60)
    print("Demo 4 Complete!")
    print("="*60)
    
    if invoice_id:
        print(f"\n[INFO] Next: Use invoice_id '{invoice_id}' for Demo 5 (HITL Review)")

