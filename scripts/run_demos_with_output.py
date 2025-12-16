"""
Run demos and capture/show actual output
This script executes each demo and displays what was actually produced
"""

import sys
import os
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime
import requests

# Fix Windows encoding
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

API_BASE_URL = "http://localhost:8000"


def check_prerequisites():
    """Check if prerequisites are met"""
    print("\n" + "="*80)
    print("CHECKING PREREQUISITES")
    print("="*80)
    
    issues = []
    
    # Check API server
    try:
        response = requests.get(f'{API_BASE_URL}/docs', timeout=2)
        if response.status_code == 200:
            print("[OK] API server is running")
        else:
            issues.append("API server returned non-200 status")
    except:
        print("[FAIL] API server is NOT running")
        print("       Start with: uvicorn api.main:app --reload")
        issues.append("API server not running")
    
    # Check sample PDFs
    sample_dir = Path(__file__).parent.parent / "demos" / "sample_data"
    pdf_files = list(sample_dir.glob("*.pdf"))
    if pdf_files:
        print(f"[OK] Found {len(pdf_files)} sample PDF(s)")
        for pdf in pdf_files[:3]:
            print(f"      - {pdf.name} ({pdf.stat().st_size:,} bytes)")
    else:
        print("[FAIL] No sample PDFs found")
        print("       Run: python scripts/create_sample_data.py")
        issues.append("No sample PDFs")
    
    # Check Streamlit
    try:
        import streamlit
        print("[OK] Streamlit is installed")
    except ImportError:
        print("[WARN] Streamlit not installed (Demo 5 web interface won't work)")
        print("       Install with: pip install streamlit")
    
    print("="*80)
    
    if issues:
        print(f"\n[WARN] {len(issues)} issue(s) found. Some demos may fail.")
        return False
    return True


def run_demo_1_ingestion():
    """Run Demo 1: Ingestion and show output"""
    print("\n" + "="*80)
    print("DEMO 1: INVOICE INGESTION")
    print("="*80)
    
    sample_dir = Path(__file__).parent.parent / "demos" / "sample_data"
    pdf_files = list(sample_dir.glob("*.pdf"))
    
    if not pdf_files:
        print("[ERROR] No PDF files found")
        return None
    
    pdf_file = pdf_files[0]
    print(f"\n[UPLOAD] Uploading: {pdf_file.name}")
    
    try:
        with open(pdf_file, "rb") as f:
            files = {"file": (pdf_file.name, f, "application/pdf")}
            response = requests.post(f"{API_BASE_URL}/api/ingestion/upload", files=files)
        
        if response.status_code == 201:
            result = response.json()
            print("\n[OK] Upload Successful!")
            print(f"\nACTUAL OUTPUT:")
            print(f"  Invoice ID: {result['invoice_id']}")
            print(f"  Status: {result['status']}")
            print(f"  File Name: {result['file_name']}")
            print(f"  File Size: {result['file_size']:,} bytes")
            print(f"  Page Count: {result['page_count']}")
            print(f"  Upload Date: {result['upload_date']}")
            print(f"  File Path: {result.get('file_path', 'N/A')}")
            return result['invoice_id'], result.get('file_path')
        else:
            print(f"\n[ERROR] Upload Failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"\n[ERROR] {e}")
        return None


def run_demo_2_extraction(invoice_id, file_path=None):
    """Run Demo 2: Extraction and show extracted data"""
    print("\n" + "="*80)
    print("DEMO 2: DATA EXTRACTION")
    print("="*80)
    
    if not invoice_id:
        print("[ERROR] No invoice ID provided")
        return None
    
    print(f"\n[EXTRACT] Extracting data from invoice: {invoice_id}")
    
    # Get file path from database if not provided
    if not file_path:
        try:
            invoice_response = requests.get(f"{API_BASE_URL}/api/hitl/invoice/{invoice_id}")
            if invoice_response.status_code == 200:
                invoice_data = invoice_response.json()
                file_path = invoice_data.get('file_path')
        except:
            pass
    
    if not file_path:
        file_path = f"storage/raw/{invoice_id}.pdf"
    
    print(f"[INFO] Using file path: {file_path}")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/extraction/extract/{invoice_id}",
            params={
                "file_identifier": file_path,
                "file_name": "sample_invoice_001.pdf"
            }
        )
        
        if response.status_code == 200:
            result = response.json()
            invoice_data = result.get("invoice", {})
            
            print("\n[OK] Extraction Successful!")
            print(f"\nACTUAL EXTRACTED DATA:")
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
                print(f"\n  Line Items ({len(line_items)}):")
                for i, item in enumerate(line_items[:5], 1):
                    print(f"    {i}. {item.get('description', 'N/A')[:50]}")
                    print(f"       Qty: {item.get('quantity', 0)}, "
                          f"Price: ${item.get('unit_price', 0):,.2f}, "
                          f"Total: ${item.get('amount', 0):,.2f}")
            
            # Confidence scores
            field_confidence = invoice_data.get('field_confidence', {})
            if field_confidence:
                print(f"\n  Field Confidence Scores:")
                for field, conf in list(field_confidence.items())[:5]:
                    icon = "[OK]" if conf >= 0.9 else "[WARN]" if conf >= 0.7 else "[LOW]"
                    print(f"    {icon} {field}: {conf:.1%}")
                
                overall_conf = result.get('confidence', 0)
                print(f"\n  Overall Confidence: {overall_conf:.1%}")
            
            return invoice_id
        else:
            print(f"\n[ERROR] Extraction Failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    except Exception as e:
        print(f"\n[ERROR] {e}")
        return None


def run_demo_3_po_matching(invoice_id):
    """Run Demo 3: PO Matching"""
    print("\n" + "="*80)
    print("DEMO 3: PO MATCHING")
    print("="*80)
    
    if not invoice_id:
        print("[SKIP] No invoice ID")
        return None
    
    print(f"\n[MATCH] Matching invoice {invoice_id} to PO...")
    
    # Sample PO data
    po_data = {
        "po_number": "PO-12345",
        "po_date": "2024-01-05",
        "vendor_name": "Acme Corporation",
        "vendor_code": "ACME001",
        "total_amount": 1500.00,
        "line_items": []
    }
    
    print(f"\n[INFO] Purchase Order Data:")
    print(f"  PO Number: {po_data['po_number']}")
    print(f"  Vendor: {po_data['vendor_name']}")
    print(f"  Amount: ${po_data['total_amount']:,.2f}")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/matching/match",
            json={"invoice_id": invoice_id, "po_data": po_data}
        )
        
        if response.status_code == 200:
            result = response.json()
            match = result.get("match", {})
            
            print("\n[OK] Matching Complete!")
            print(f"\nACTUAL MATCH RESULTS:")
            print(f"  Matched: {'Yes' if match.get('matched') else 'No'}")
            print(f"  Confidence: {match.get('confidence', 0):.1%}")
            print(f"  Strategy: {match.get('match_strategy', 'N/A')}")
            print(f"  PO Number: {match.get('matched_document_number', 'N/A')}")
            
            details = match.get('match_details', {})
            if details:
                print(f"\n  Match Details:")
                for key, value in details.items():
                    print(f"    {key}: {value}")
            
            return invoice_id
        else:
            print(f"\n[WARN] Matching returned: {response.status_code}")
            print(f"Response: {response.text}")
            return invoice_id  # Continue even if matching fails
    except Exception as e:
        print(f"\n[WARN] Matching error: {e}")
        return invoice_id


def run_demo_4_pdf_overlay(invoice_id):
    """Run Demo 4: PDF Overlay"""
    print("\n" + "="*80)
    print("DEMO 4: PDF OVERLAY")
    print("="*80)
    
    if not invoice_id:
        print("[SKIP] No invoice ID")
        return None
    
    print(f"\n[OVERLAY] Generating PDF overlay for invoice: {invoice_id}")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/overlay/{invoice_id}")
        
        if response.status_code == 200:
            output_dir = Path(__file__).parent.parent / "demos" / "output"
            output_dir.mkdir(exist_ok=True)
            
            output_file = output_dir / f"overlay_{invoice_id}.pdf"
            with open(output_file, "wb") as f:
                f.write(response.content)
            
            print("\n[OK] Overlay Generated Successfully!")
            print(f"\nACTUAL OUTPUT:")
            print(f"  Output File: {output_file.name}")
            print(f"  File Size: {len(response.content):,} bytes")
            print(f"  Full Path: {output_file.absolute()}")
            
            return invoice_id
        else:
            print(f"\n[WARN] Overlay generation returned: {response.status_code}")
            return invoice_id
    except Exception as e:
        print(f"\n[WARN] Overlay error: {e}")
        return invoice_id


def run_demo_5_hitl_review(invoice_id):
    """Run Demo 5: HITL Review"""
    print("\n" + "="*80)
    print("DEMO 5: HITL REVIEW")
    print("="*80)
    
    if not invoice_id:
        print("[SKIP] No invoice ID")
        return None
    
    print(f"\n[REVIEW] Reviewing invoice: {invoice_id}")
    
    try:
        response = requests.get(f"{API_BASE_URL}/api/hitl/invoice/{invoice_id}")
        
        if response.status_code == 200:
            invoice = response.json()
            
            print("\n[OK] Invoice Retrieved for Review")
            print(f"\nACTUAL INVOICE DATA:")
            print(f"  Invoice Number: {invoice.get('invoice_number', 'N/A')}")
            print(f"  Invoice Date: {invoice.get('invoice_date', 'N/A')}")
            print(f"  Vendor: {invoice.get('vendor_name', 'N/A')}")
            print(f"  Total: ${invoice.get('total_amount', 0):,.2f}")
            print(f"  Status: {invoice.get('status', 'N/A')}")
            
            # Field confidence
            field_confidence = invoice.get('field_confidence', {})
            if field_confidence:
                print(f"\n  Field Confidence Scores:")
                low_conf_fields = []
                for field, conf in list(field_confidence.items())[:10]:
                    icon = "[OK]" if conf >= 0.9 else "[WARN]" if conf >= 0.7 else "[LOW]"
                    print(f"    {icon} {field}: {conf:.1%}")
                    if conf < 0.7:
                        low_conf_fields.append(field)
                
                if low_conf_fields:
                    print(f"\n  Fields Requiring Review:")
                    for field in low_conf_fields:
                        print(f"      - {field} ({field_confidence[field]:.1%})")
            
            # Streamlit check
            try:
                import streamlit
                print(f"\n[INFO] Streamlit is installed")
                print(f"       To view web interface, run: streamlit run streamlit_app.py")
                print(f"       Then open: http://localhost:8501")
            except ImportError:
                print(f"\n[WARN] Streamlit not installed - web interface unavailable")
            
            return invoice_id
        else:
            print(f"\n[WARN] Review returned: {response.status_code}")
            return invoice_id
    except Exception as e:
        print(f"\n[WARN] Review error: {e}")
        return invoice_id


def run_demo_6_erp_staging(invoice_id):
    """Run Demo 6: ERP Staging"""
    print("\n" + "="*80)
    print("DEMO 6: ERP STAGING")
    print("="*80)
    
    if not invoice_id:
        print("[SKIP] No invoice ID")
        return None
    
    print(f"\n[STAGE] Staging invoice {invoice_id} for ERP...")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/staging/stage",
            json={"invoice_id": invoice_id, "erp_format": "json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            
            print("\n[OK] Invoice Staged Successfully!")
            print(f"\nACTUAL STAGING RESULTS:")
            print(f"  Format: {result.get('format', 'N/A')}")
            print(f"  Invoice ID: {result.get('invoice_id', 'N/A')}")
            print(f"  Status: {result.get('status', 'N/A')}")
            
            # Save and show payload
            payload_data = result.get('payload', '')
            if payload_data:
                output_dir = Path(__file__).parent.parent / "demos" / "output"
                output_dir.mkdir(exist_ok=True)
                
                output_file = output_dir / f"erp_payload_{invoice_id}.json"
                try:
                    payload_json = json.loads(payload_data)
                    with open(output_file, "w") as f:
                        json.dump(payload_json, f, indent=2)
                    
                    print(f"\n  ERP Payload Saved: {output_file.name}")
                    print(f"  File Size: {len(payload_data):,} bytes")
                    
                    # Show preview of payload structure
                    print(f"\n  PAYLOAD STRUCTURE:")
                    print(f"    voucher_type: {payload_json.get('voucher_type', 'N/A')}")
                    print(f"    vendor_name: {payload_json.get('vendor_name', 'N/A')}")
                    print(f"    invoice_number: {payload_json.get('invoice_number', 'N/A')}")
                    print(f"    total_amount: ${payload_json.get('total_amount', 0):,.2f}")
                    print(f"    line_items: {len(payload_json.get('line_items', []))} items")
                    
                    # Show first few lines of actual JSON
                    print(f"\n  FIRST 20 LINES OF JSON:")
                    with open(output_file, "r") as f:
                        lines = f.readlines()[:20]
                        for line in lines:
                            print(f"    {line.rstrip()}")
                    if len(payload_json) > 20:
                        print(f"    ... (truncated)")
                        
                except json.JSONDecodeError:
                    # Not JSON, save as text
                    with open(output_file, "w") as f:
                        f.write(payload_data)
                    print(f"\n  Payload saved (non-JSON format)")
            
            return invoice_id
        else:
            print(f"\n[WARN] Staging returned: {response.status_code}")
            return invoice_id
    except Exception as e:
        print(f"\n[WARN] Staging error: {e}")
        return invoice_id


def main():
    """Run all demos and show actual output"""
    print("\n" + "="*80)
    print("DEMO RUNNER - SHOWING ACTUAL OUTPUT")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check prerequisites
    prereqs_ok = check_prerequisites()
    if not prereqs_ok:
        print("\n[WARN] Prerequisites not met. Some demos may fail.")
        print("[INFO] Continuing anyway to show what happens...")
    
    invoice_id = None
    file_path = None
    
    # Run demos in sequence
    result = run_demo_1_ingestion()
    if result:
        invoice_id, file_path = result if isinstance(result, tuple) else (result, None)
    
    if invoice_id:
        invoice_id = run_demo_2_extraction(invoice_id, file_path)
        invoice_id = run_demo_3_po_matching(invoice_id)
        invoice_id = run_demo_4_pdf_overlay(invoice_id)
        invoice_id = run_demo_5_hitl_review(invoice_id)
        invoice_id = run_demo_6_erp_staging(invoice_id)
    
    # Summary
    print("\n" + "="*80)
    print("DEMO RUN COMPLETE")
    print("="*80)
    print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if invoice_id:
        print(f"\n[INFO] Final Invoice ID: {invoice_id}")
        print(f"\n[INFO] Generated files in: demos/output/")
        output_dir = Path(__file__).parent.parent / "demos" / "output"
        if output_dir.exists():
            for file in output_dir.glob("*"):
                print(f"      - {file.name}")
    
    print("="*80)


if __name__ == "__main__":
    main()

