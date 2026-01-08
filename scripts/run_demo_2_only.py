"""
Run Demo 2: Extraction - Show what's being extracted
"""

import sys
import os
import requests
from pathlib import Path

# Fix Windows encoding
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

API_BASE_URL = "http://localhost:8000"

def upload_and_extract():
    """Upload a sample invoice and extract data"""
    print("\n" + "="*80)
    print("DEMO 2: DATA EXTRACTION - SHOWING EXTRACTED DATA")
    print("="*80)
    
    # Check API server first (use simple endpoint)
    print("\n[CHECK] Checking API server...")
    try:
        # Try a simple endpoint instead of /docs which might be slow
        response = requests.get(f"{API_BASE_URL}/", timeout=3)
        print("[OK] API server is running")
    except requests.exceptions.ConnectionError:
        print(f"[WARN] Cannot connect to API - will try anyway")
    except requests.exceptions.Timeout:
        print(f"[WARN] API check timed out - server might be slow, continuing anyway")
    except Exception:
        print(f"[WARN] API check failed - will try anyway")
    
    # Step 1: Upload invoice
    print("\n[STEP 1] Uploading sample invoice...")
    
    # Try multiple path resolution methods
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    sample_dir = project_root / "demos" / "sample_data"
    
    # Fallback: try current working directory
    if not sample_dir.exists():
        cwd_sample_dir = Path.cwd() / "demos" / "sample_data"
        if cwd_sample_dir.exists():
            sample_dir = cwd_sample_dir
    
    print(f"[INFO] Looking for PDFs in: {sample_dir}")
    print(f"[INFO] Directory exists: {sample_dir.exists()}")
    
    pdf_files = list(sample_dir.glob("*.pdf")) if sample_dir.exists() else []
    
    if not pdf_files:
        print(f"[ERROR] No PDF files found in {sample_dir}")
        print(f"[INFO] Current working directory: {Path.cwd()}")
        print(f"[INFO] Script location: {Path(__file__).resolve()}")
        return
    
    pdf_file = pdf_files[0]
    print(f"[OK] Found PDF: {pdf_file.name} ({pdf_file.stat().st_size:,} bytes)")
    print(f"[INFO] Full path: {pdf_file.resolve()}")
    
    try:
        # Upload
        print(f"[PROGRESS] Reading PDF file...")
        with open(pdf_file, "rb") as f:
            file_content = f.read()
            print(f"[PROGRESS] File read: {len(file_content):,} bytes")
        
        print(f"[PROGRESS] Uploading to API server...")
        with open(pdf_file, "rb") as f:
            files = {"file": (pdf_file.name, f, "application/pdf")}
            upload_response = requests.post(
                f"{API_BASE_URL}/api/ingestion/upload", 
                files=files,
                timeout=120  # Allow extra time in case server is slow
            )
        
        print(f"[PROGRESS] Upload response received: {upload_response.status_code}")
        
        if upload_response.status_code != 201:
            print(f"[ERROR] Upload failed: {upload_response.status_code}")
            print(f"Response: {upload_response.text}")
            return
        
        upload_result = upload_response.json()
        invoice_id = upload_result['invoice_id']
        file_path = upload_result.get('file_path')
        file_name = upload_result.get('file_name', pdf_file.name)
        
        print(f"[OK] Upload successful!")
        print(f"  Invoice ID: {invoice_id}")
        print(f"  File Path: {file_path}")
        
        # Step 2: Extract
        print(f"\n[STEP 2] Extracting data from invoice...")
        print(f"[INFO] Invoice ID: {invoice_id}")
        print(f"[INFO] File Path: {file_path}")
        print(f"[PROGRESS] Sending extraction request to API...")
        
        extract_response = requests.post(
            f"{API_BASE_URL}/api/extraction/extract/{invoice_id}",
            params={
                "file_identifier": file_path,
                "file_name": file_name
            },
            timeout=180  # Extraction can take a while with Azure Document Intelligence
        )
        
        print(f"[PROGRESS] Extraction response received: {extract_response.status_code}")
        
        if extract_response.status_code == 200:
            print(f"[PROGRESS] Parsing extraction results...")
            result = extract_response.json()
            invoice_data = result.get("invoice", {})
            
            print("\n" + "="*80)
            print("[OK] EXTRACTION SUCCESSFUL!")
            print("="*80)
            print(f"[PROGRESS] Displaying extracted data...")
            
            # Helper to safely convert to float
            def to_number(val, default=0.0):
                try:
                    if val is None:
                        return default
                    if isinstance(val, (int, float)):
                        return float(val)
                    return float(str(val).replace(",", ""))
                except Exception:
                    return default

            print(f"\nEXTRACTED INVOICE DATA:")
            print(f"  Invoice ID: {invoice_data.get('id', 'N/A')}")
            print(f"  Invoice Number: {invoice_data.get('invoice_number', 'N/A')}")
            print(f"  Invoice Date: {invoice_data.get('invoice_date', 'N/A')}")
            print(f"  Vendor Name: {invoice_data.get('vendor_name', 'N/A')}")
            print(f"  Vendor Address: {invoice_data.get('vendor_address', {}).get('street_address', 'N/A') if isinstance(invoice_data.get('vendor_address'), dict) else 'N/A'}")
            print(f"  Customer Name: {invoice_data.get('customer_name', 'N/A')}")
            print(f"  Customer Address: {invoice_data.get('customer_address', {}).get('street_address', 'N/A') if isinstance(invoice_data.get('customer_address'), dict) else 'N/A'}")
            print(f"  Subtotal: ${ to_number(invoice_data.get('subtotal')):,.2f}")
            print(f"  Tax Amount: ${ to_number(invoice_data.get('tax_amount')):,.2f}")
            print(f"  Total Amount: ${ to_number(invoice_data.get('total_amount')):,.2f}")
            print(f"  Currency: {invoice_data.get('currency', 'N/A')}")
            print(f"  Status: {invoice_data.get('status', 'N/A')}")
            
            # Line items
            line_items = invoice_data.get('line_items', [])
            if line_items:
                print(f"\nLINE ITEMS ({len(line_items)}):")
                for i, item in enumerate(line_items, 1):
                    print(f"\n  Item {i}:")
                    print(f"    Description: {item.get('description', 'N/A')}")
                    print(f"    Quantity: {item.get('quantity', 0)}")
                    print(f"    Unit Price: ${ to_number(item.get('unit_price')):,.2f}")
                    print(f"    Amount: ${ to_number(item.get('amount')):,.2f}")
                    if item.get('tax_rate'):
                        print(f"    Tax Rate: {item.get('tax_rate', 0):.1%}")
                    if item.get('tax_amount'):
                        print(f"    Tax Amount: ${ to_number(item.get('tax_amount')):,.2f}")
            else:
                print("\n  No line items extracted")
            
            # Field confidence scores
            field_confidence = invoice_data.get('field_confidence', {})
            if field_confidence:
                print(f"\nFIELD CONFIDENCE SCORES:")
                for field, confidence in sorted(field_confidence.items(), key=lambda x: x[1], reverse=True):
                    icon = "[OK]" if confidence >= 0.9 else "[WARN]" if confidence >= 0.7 else "[LOW]"
                    print(f"  {icon} {field}: {confidence:.1%}")
                
                # Overall confidence
                overall_conf = result.get('confidence', 0)
                print(f"\n  Overall Confidence: {overall_conf:.1%}")
            else:
                print("\n  No confidence scores available")
            
            # Invoice subtype
            subtype = invoice_data.get('invoice_subtype')
            if subtype:
                print(f"\nINVOICE SUBTYPE: {subtype}")
                extensions = invoice_data.get('extensions', {})
                if extensions:
                    print(f"  Extensions: {list(extensions.keys())}")
            
            # Extraction metadata
            print(f"\nEXTRACTION METADATA:")
            print(f"  Status: {result.get('status', 'N/A')}")
            print(f"  Timestamp: {result.get('extraction_timestamp', 'N/A')}")
            
            print("\n" + "="*80)
            print("[OK] EXTRACTION COMPLETE")
            print("="*80)
            print(f"\n[SUMMARY] Successfully extracted data from invoice:")
            print(f"  - Invoice ID: {invoice_id}")
            print(f"  - Fields extracted: {len([k for k, v in invoice_data.items() if v and k not in ['line_items', 'extensions', 'field_confidence']])}")
            print(f"  - Line items: {len(line_items)}")
            print(f"  - Confidence scores: {len(field_confidence)} fields")
            if overall_conf:
                print(f"  - Overall confidence: {overall_conf:.1%}")
            
        else:
            print(f"\n[ERROR] Extraction Failed: {extract_response.status_code}")
            print(f"[PROGRESS] Parsing error response...")
            print(f"Response: {extract_response.text}")
            try:
                error_detail = extract_response.json()
                if 'detail' in error_detail:
                    if isinstance(error_detail['detail'], dict):
                        print(f"\n[ERROR DETAILS]")
                        print(f"  Message: {error_detail['detail'].get('message', 'N/A')}")
                        errors = error_detail['detail'].get('errors', [])
                        if errors:
                            print(f"  Errors:")
                            for err in errors:
                                print(f"    - {err}")
                    else:
                        print(f"Detail: {error_detail['detail']}")
            except Exception as e:
                print(f"[WARN] Could not parse error response: {e}")
            
    except requests.exceptions.ConnectionError as e:
        print(f"\n[ERROR] Cannot connect to API at {API_BASE_URL}")
        print(f"   Error: {e}")
        print("   Make sure the API server is running:")
        print("   uvicorn api.main:app --reload")
    except requests.exceptions.Timeout as e:
        print(f"\n[ERROR] Request timed out: {e}")
        print("   The API server may be slow or overloaded.")
        print("   Try increasing the timeout or check server logs.")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    try:
        upload_and_extract()
    except KeyboardInterrupt:
        print("\n\n[INFO] Interrupted by user")
    except Exception as e:
        print(f"\n[FATAL ERROR] Script crashed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

