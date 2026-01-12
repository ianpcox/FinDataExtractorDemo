#!/usr/bin/env python3
"""
Test DI OCR extraction on sample invoice (IRO001 KTXW934.pdf) against all 51 UI fields.

This script evaluates which of the 51 UI fields are successfully extracted by DI OCR
from the sample invoice, providing a baseline for performance evaluation.
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import csv
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.extraction.document_intelligence_client import DocumentIntelligenceClient
from src.extraction.field_extractor import FieldExtractor
from src.config import settings


def load_ui_fields() -> set:
    """Load the 51 UI fields from invoice_ui_fields.csv"""
    csv_path = Path(__file__).parent.parent.parent.parent / "invoice_ui_fields.csv"
    ui_fields = set()
    
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ui_fields.add(row["Field Name"])
    
    return ui_fields


def test_sample_invoice_51_fields():
    """Test DI OCR extraction on sample invoice against all 51 UI fields"""
    print("\n" + "="*80)
    print("DI OCR FIELD EXTRACTION EVALUATION - 51 UI FIELDS")
    print("="*80)
    
    # Sample invoice
    pdf_file = Path("data/sample_invoices/Raw/Raw_Basic/IRO001 KTXW934.pdf")
    
    if not pdf_file.exists():
        print(f"\n[ERROR] File not found: {pdf_file}")
        print(f"[INFO] Current directory: {Path.cwd()}")
        return
    
    print(f"\n[INFO] Testing file: {pdf_file}")
    print(f"[INFO] File size: {pdf_file.stat().st_size:,} bytes")
    
    # Load 51 UI fields
    ui_fields = load_ui_fields()
    print(f"\n[INFO] Evaluating extraction against {len(ui_fields)} UI fields")
    
    # Check DI configuration
    if not settings.AZURE_FORM_RECOGNIZER_ENDPOINT or not settings.AZURE_FORM_RECOGNIZER_KEY:
        print(f"\n[ERROR] Azure Document Intelligence not configured!")
        return
    
    try:
        # Read PDF
        print(f"\n[PROGRESS] Reading PDF file...")
        with open(pdf_file, "rb") as f:
            file_content = f.read()
        print(f"[OK] File read: {len(file_content):,} bytes")
        
        # Initialize Document Intelligence client
        print(f"\n[PROGRESS] Initializing Document Intelligence client...")
        doc_client = DocumentIntelligenceClient()
        print(f"[OK] Client initialized")
        
        # Analyze with Document Intelligence
        print(f"\n[PROGRESS] Analyzing invoice with Azure Document Intelligence...")
        print(f"[INFO] This is a REAL API call - may take 10-30 seconds...")
        di_data = doc_client.analyze_invoice(file_content)
        
        if not di_data or di_data.get("error"):
            print(f"[ERROR] Document Intelligence failed: {di_data.get('error', 'Unknown error')}")
            return
        
        print(f"[OK] Document Intelligence analysis complete!")
        
        # Extract fields using FieldExtractor
        print(f"\n[PROGRESS] Extracting fields using FieldExtractor...")
        field_extractor = FieldExtractor()
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=di_data,
            file_path=str(pdf_file),
            file_name=pdf_file.name,
            upload_date=datetime.utcnow()
        )
        print(f"[OK] Fields extracted")
        
        # Evaluate field extraction
        print("\n" + "="*80)
        print("FIELD EXTRACTION EVALUATION RESULTS")
        print("="*80)
        
        extracted_fields = set()
        missing_fields = set()
        field_values = {}
        
        # Check each UI field
        for field_name in sorted(ui_fields):
            # Get field value from invoice
            value = getattr(invoice, field_name, None)
            field_values[field_name] = value
            
            # Check if field was extracted (has a non-null, non-empty value)
            if value is not None and value != "":
                # Handle address objects
                if field_name.endswith("_address") and isinstance(value, dict):
                    # Check if address has any non-empty subfields
                    if any(v for v in value.values() if v):
                        extracted_fields.add(field_name)
                    else:
                        missing_fields.add(field_name)
                else:
                    extracted_fields.add(field_name)
            else:
                missing_fields.add(field_name)
        
        # Display results
        print(f"\n[RESULTS] Field Extraction Summary:")
        print(f"  Total UI fields: {len(ui_fields)}")
        print(f"  Fields extracted: {len(extracted_fields)} ({len(extracted_fields)/len(ui_fields)*100:.1f}%)")
        print(f"  Fields missing: {len(missing_fields)} ({len(missing_fields)/len(ui_fields)*100:.1f}%)")
        
        print(f"\n[EXTRACTED FIELDS] ({len(extracted_fields)} fields):")
        for field in sorted(extracted_fields):
            value = field_values[field]
            if field.endswith("_address") and isinstance(value, dict):
                print(f"  ✓ {field}: {json.dumps(value, default=str)[:80]}")
            elif isinstance(value, (int, float)) or (isinstance(value, str) and len(value) < 50):
                print(f"  ✓ {field}: {value}")
            else:
                print(f"  ✓ {field}: {str(value)[:50]}...")
        
        print(f"\n[MISSING FIELDS] ({len(missing_fields)} fields):")
        for field in sorted(missing_fields):
            print(f"  ✗ {field}")
        
        # Field confidence scores
        if invoice.field_confidence:
            print(f"\n[FIELD CONFIDENCE] (from DI OCR):")
            for field in sorted(extracted_fields):
                if field in invoice.field_confidence:
                    conf = invoice.field_confidence[field]
                    print(f"  {field}: {conf:.2f}")
        
        print("\n" + "="*80)
        print("EVALUATION COMPLETE")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_sample_invoice_51_fields()
