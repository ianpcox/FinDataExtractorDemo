"""
Demo 1: Invoice Ingestion
Demonstrates uploading invoice PDFs to the system.
"""

import requests
import json
from pathlib import Path

API_BASE_URL = "http://localhost:8000"

def demo_single_upload():
    """Demo: Upload a single invoice PDF"""
    print("\n" + "="*60)
    print("DEMO 1: Invoice Ingestion - Single Upload")
    print("="*60)
    
    # Find sample PDF
    sample_dir = Path(__file__).parent / "sample_data"
    pdf_files = list(sample_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"\n[ERROR] No PDF files found in {sample_dir}")
        print("   Please place a sample invoice PDF in that directory.")
        return None
    
    pdf_file = pdf_files[0]
    print(f"\n[UPLOAD] Uploading: {pdf_file.name}")
    
    # Upload file
    url = f"{API_BASE_URL}/api/ingestion/upload"
    
    try:
        with open(pdf_file, "rb") as f:
            files = {"file": (pdf_file.name, f, "application/pdf")}
            response = requests.post(url, files=files)
        
        if response.status_code == 201:
            result = response.json()
            print("\n[OK] Upload Successful!")
            print(f"\nInvoice ID: {result['invoice_id']}")
            print(f"Status: {result['status']}")
            print(f"File Name: {result['file_name']}")
            print(f"File Size: {result['file_size']:,} bytes")
            print(f"Page Count: {result['page_count']}")
            print(f"Upload Date: {result['upload_date']}")
            
            return result['invoice_id']
        else:
            print(f"\n[ERROR] Upload Failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print(f"\n[ERROR] Cannot connect to API at {API_BASE_URL}")
        print("   Make sure the API server is running:")
        print("   uvicorn api.main:app --reload")
        return None
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        return None


def demo_batch_upload():
    """Demo: Upload multiple invoice PDFs"""
    print("\n" + "="*60)
    print("DEMO 1: Invoice Ingestion - Batch Upload")
    print("="*60)
    
    # Find sample PDFs
    sample_dir = Path(__file__).parent / "sample_data"
    pdf_files = list(sample_dir.glob("*.pdf"))[:3]  # Limit to 3 for demo
    
    if not pdf_files:
        print(f"\n[ERROR] No PDF files found in {sample_dir}")
        return
    
    print(f"\n[UPLOAD] Uploading {len(pdf_files)} files...")
    
    # Upload files
    url = f"{API_BASE_URL}/api/ingestion/batch-upload"
    
    try:
        files = []
        for pdf_file in pdf_files:
            files.append(("files", (pdf_file.name, open(pdf_file, "rb"), "application/pdf")))
        
        response = requests.post(url, files=files)
        
        # Close files
        for _, (_, file_obj, _) in files:
            file_obj.close()
        
        if response.status_code == 200:
            result = response.json()
            print("\n[OK] Batch Upload Complete!")
            print(f"\nTotal Files: {len(pdf_files)}")
            print(f"Successful: {result['successful']}")
            print(f"Failed: {result['failed']}")
            
            print("\nResults:")
            for r in result['results']:
                status_icon = "[OK]" if r['status'] == "uploaded" else "[ERROR]"
                print(f"  {status_icon} {r['file_name']}: {r['status']}")
                if r.get('invoice_id'):
                    print(f"     Invoice ID: {r['invoice_id']}")
            
            if result['errors']:
                print("\nErrors:")
                for e in result['errors']:
                    print(f"  [ERROR] {e['file_name']}: {e['error']}")
        else:
            print(f"\n[ERROR] Batch Upload Failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print(f"\n[ERROR] Cannot connect to API at {API_BASE_URL}")
        print("   Make sure the API server is running.")
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("FIN DATA EXTRACTOR VANILLA - DEMO 1: INGESTION")
    print("="*60)
    
    # Create sample_data directory if it doesn't exist
    sample_dir = Path(__file__).parent / "sample_data"
    sample_dir.mkdir(exist_ok=True)
    
    # Run demos
    invoice_id = demo_single_upload()
    demo_batch_upload()
    
    print("\n" + "="*60)
    print("Demo 1 Complete!")
    print("="*60)
    
    if invoice_id:
        print(f"\n[INFO] Next: Use invoice_id '{invoice_id}' for Demo 2 (Extraction)")

