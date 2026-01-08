"""
Demo 2: Invoice Extraction
Demonstrates extracting structured data from invoice PDFs.
"""

import requests
import json
from pathlib import Path
from datetime import datetime

API_BASE_URL = "http://localhost:8000"

def demo_extraction(invoice_id: str = None):
    """Demo: Extract data from an invoice"""
    print("\n" + "="*60)
    print("DEMO 2: Invoice Extraction")
    print("="*60)
    
    # If no invoice_id provided, upload a new invoice first
    if not invoice_id:
        print("\n[UPLOAD] First, uploading a sample invoice...")
        from demo_01_ingestion import demo_single_upload
        result = demo_single_upload()
        if not result:
            print("\n[ERROR] Cannot proceed without an invoice")
            return None
        invoice_id = result
    
    print(f"\n[EXTRACT] Extracting data from invoice: {invoice_id}")
    
    # First, get the invoice file path (in real scenario, this would come from database)
    # For demo, we'll upload and extract in one go
    sample_dir = Path(__file__).parent / "sample_data"
    pdf_files = list(sample_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"\n[ERROR] No PDF files found in {sample_dir}")
        return None
    
    pdf_file = pdf_files[0]
    
    # Upload if needed
    if not invoice_id:
        print("\n[UPLOAD] Uploading invoice first...")
        url = f"{API_BASE_URL}/api/ingestion/upload"
        with open(pdf_file, "rb") as f:
            files = {"file": (pdf_file.name, f, "application/pdf")}
            response = requests.post(url, files=files)
        
        if response.status_code != 201:
            print(f"\n[ERROR] Upload failed: {response.status_code}")
            return None
        
        invoice_id = response.json()["invoice_id"]
        file_path = response.json()["file_path"]
        file_name = response.json()["file_name"]
    else:
        file_path = f"storage/raw/{invoice_id}.pdf"  # Demo path
        file_name = pdf_file.name
    
    # Extract invoice
    print(f"\n[EXTRACT] Extracting data using Azure Document Intelligence...")
    url = f"{API_BASE_URL}/api/extraction/extract/{invoice_id}"
    
    try:
        response = requests.post(
            url,
            params={
                "file_identifier": file_path,
                "file_name": file_name
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            invoice_data = result.get("invoice", {})
            
            print("\n[OK] Extraction Successful!")
            print(f"\n[INFO] Extracted Invoice Data:")
            print(f"  Invoice Number: {invoice_data.get('invoice_number', 'N/A')}")
            print(f"  Invoice Date: {invoice_data.get('invoice_date', 'N/A')}")
            print(f"  Vendor: {invoice_data.get('vendor_name', 'N/A')}")
            print(f"  Customer: {invoice_data.get('customer_name', 'N/A')}")
            print(f"  Subtotal: ${invoice_data.get('subtotal', 0):,.2f}")
            print(f"  Tax: ${invoice_data.get('tax_amount', 0):,.2f}")
            print(f"  Total: ${invoice_data.get('total_amount', 0):,.2f}")
            print(f"  Currency: {invoice_data.get('currency', 'N/A')}")
            
            # Line items
            line_items = invoice_data.get('line_items', [])
            if line_items:
                print(f"\n[INFO] Line Items ({len(line_items)}):")
                for i, item in enumerate(line_items[:5], 1):  # Show first 5
                    print(f"  {i}. {item.get('description', 'N/A')[:50]}")
                    print(f"     Qty: {item.get('quantity', 0)}, "
                          f"Price: ${item.get('unit_price', 0):,.2f}, "
                          f"Total: ${item.get('amount', 0):,.2f}")
            
            # Confidence scores
            field_confidence = invoice_data.get('field_confidence', {})
            if field_confidence:
                print(f"\n[INFO] Field Confidence Scores:")
                important_fields = ['invoice_id', 'invoice_date', 'vendor_name', 'invoice_total']
                for field in important_fields:
                    if field in field_confidence:
                        conf = field_confidence[field]
                        icon = "[OK]" if conf >= 0.9 else "[WARN]" if conf >= 0.7 else "[LOW]"
                        print(f"  {icon} {field}: {conf:.1%}")
                
                overall_conf = result.get('confidence', 0)
                print(f"\n  Overall Confidence: {overall_conf:.1%}")
            
            # Subtype detection
            subtype = invoice_data.get('invoice_subtype')
            if subtype:
                print(f"\n[INFO] Invoice Subtype: {subtype}")
                extensions = invoice_data.get('extensions', {})
                if extensions:
                    print(f"  Extensions detected: {list(extensions.keys())}")
            
            return invoice_id
        else:
            print(f"\n[ERROR] Extraction Failed: {response.status_code}")
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
    print("FIN DATA EXTRACTOR VANILLA - DEMO 2: EXTRACTION")
    print("="*60)
    
    # Create sample_data directory if it doesn't exist
    sample_dir = Path(__file__).parent / "sample_data"
    sample_dir.mkdir(exist_ok=True)
    
    # Run demo
    invoice_id = demo_extraction()
    
    print("\n" + "="*60)
    print("Demo 2 Complete!")
    print("="*60)
    
    if invoice_id:
        print(f"\n[INFO] Next: Use invoice_id '{invoice_id}' for Demo 3 (PO Matching)")

