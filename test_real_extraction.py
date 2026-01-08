"""Test script to verify real DI OCR and LLM are being used (not mocks)"""

import requests
import json
import time
import sys
from pathlib import Path

API_BASE = "http://localhost:8000"
TEST_PDF = "data/sample_invoices/Raw/Raw_Basic/ACC012 4202092525.pdf"

def test_extraction():
    """Test extraction with a real PDF"""
    print("=" * 60)
    print("Testing Real DI OCR and LLM Extraction")
    print("=" * 60)
    print()
    
    # Check if PDF exists
    pdf_path = Path(TEST_PDF)
    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {TEST_PDF}")
        return False
    
    print(f"1. Using PDF: {TEST_PDF}")
    print()
    
    # Upload PDF
    print("2. Uploading PDF...")
    try:
        with open(pdf_path, "rb") as f:
            files = {"file": (pdf_path.name, f, "application/pdf")}
            response = requests.post(
                f"{API_BASE}/api/ingestion/upload",
                files=files,
                timeout=30
            )
            response.raise_for_status()
            upload_result = response.json()
            invoice_id = upload_result.get("invoice_id")
            print(f"   [OK] Upload successful. Invoice ID: {invoice_id}")
    except Exception as e:
        print(f"   [ERROR] Upload failed: {e}")
        return False
    
    print()
    
    # Check extraction status
    print("3. Starting extraction...")
    try:
        response = requests.post(
            f"{API_BASE}/api/extraction/extract/{invoice_id}",
            timeout=600  # 10 minutes for LLM
        )
        response.raise_for_status()
        extract_result = response.json()
        print(f"   [OK] Extraction initiated")
        print(f"   Status: {extract_result.get('status', 'unknown')}")
    except Exception as e:
        print(f"   [ERROR] Extraction failed: {e}")
        return False
    
    print()
    
    # Poll for progress
    print("4. Monitoring extraction progress...")
    max_wait = 300  # 5 minutes
    start_time = time.time()
    last_progress = 0
    
    while time.time() - start_time < max_wait:
        try:
            response = requests.get(
                f"{API_BASE}/api/extraction/progress/{invoice_id}",
                timeout=10
            )
            if response.status_code == 200:
                progress = response.json()
                current_progress = progress.get("progress_percentage", 0)
                message = progress.get("message", "")
                step = progress.get("current_step", "")
                
                if current_progress != last_progress:
                    print(f"   Progress: {current_progress}% - {message} (Step: {step})")
                    last_progress = current_progress
                
                if current_progress >= 100:
                    print(f"   [OK] Extraction complete!")
                    break
            time.sleep(2)
        except Exception as e:
            print(f"   Error checking progress: {e}")
            time.sleep(2)
    
    print()
    
    # Get final invoice data
    print("5. Retrieving extracted invoice data...")
    try:
        response = requests.get(
            f"{API_BASE}/api/hitl/invoice/{invoice_id}",
            timeout=10
        )
        response.raise_for_status()
        invoice_data = response.json()
        
        # Check for evidence of real DI and LLM
        print()
        print("6. Verifying real services were used...")
        
        # Check extraction metadata
        extraction_metadata = invoice_data.get("extraction_metadata", {})
        di_endpoint = extraction_metadata.get("di_endpoint", "")
        llm_endpoint = extraction_metadata.get("llm_endpoint", "")
        
        print(f"   DI Endpoint: {di_endpoint}")
        print(f"   LLM Endpoint: {llm_endpoint}")
        
        # Check if mock was used
        is_mock_di = "mock" in di_endpoint.lower() if di_endpoint else False
        is_mock_llm = "mock" in llm_endpoint.lower() if llm_endpoint else False
        
        if is_mock_di:
            print("   [WARNING] Mock Document Intelligence was used!")
        else:
            print("   [OK] Real Document Intelligence was used")
        
        if is_mock_llm:
            print("   [WARNING] Mock LLM was used!")
        else:
            print("   [OK] Real LLM was used")
        
        # Check extracted fields
        fields = invoice_data.get("fields", {})
        print()
        print("7. Sample extracted fields:")
        sample_fields = ["invoice_number", "vendor_name", "total_amount", "invoice_date"]
        for field in sample_fields:
            field_data = fields.get(field, {})
            value = field_data.get("value", "N/A")
            confidence = field_data.get("confidence", "N/A")
            print(f"   {field}: {value} (confidence: {confidence})")
        
        print()
        print("=" * 60)
        if not is_mock_di and not is_mock_llm:
            print("[SUCCESS] Real DI OCR and LLM were used!")
        else:
            print("[WARNING] Mock services may have been used")
        print("=" * 60)
        
        return not is_mock_di and not is_mock_llm
        
    except Exception as e:
        print(f"   ✗ Failed to retrieve invoice: {e}")
        return False

if __name__ == "__main__":
    success = test_extraction()
    sys.exit(0 if success else 1)

