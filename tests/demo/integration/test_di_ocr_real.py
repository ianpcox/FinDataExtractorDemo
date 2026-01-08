"""
Test REAL Document Intelligence OCR extraction on a specific PDF document.
This script tests the actual Azure Document Intelligence service (not mock).
"""

import sys
import os
from pathlib import Path
import json

# Fix Windows encoding
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.extraction.document_intelligence_client import DocumentIntelligenceClient
from src.extraction.field_extractor import FieldExtractor
from src.config import settings
from datetime import datetime


def test_real_di_ocr():
    """Test REAL DI OCR extraction on the specified PDF"""
    print("\n" + "="*80)
    print("REAL DOCUMENT INTELLIGENCE OCR EXTRACTION TEST")
    print("="*80)
    
    # Target PDF file
    pdf_file = Path("data/sample_invoices/Raw/Raw_Basic/ACC012 4202092525.pdf")
    
    if not pdf_file.exists():
        print(f"[ERROR] File not found: {pdf_file}")
        print(f"[INFO] Current directory: {Path.cwd()}")
        return
    
    print(f"\n[INFO] Testing file: {pdf_file}")
    print(f"[INFO] File size: {pdf_file.stat().st_size:,} bytes")
    
    # Check DI configuration
    if not settings.AZURE_FORM_RECOGNIZER_ENDPOINT or not settings.AZURE_FORM_RECOGNIZER_KEY:
        print(f"\n[ERROR] Azure Document Intelligence not configured!")
        print(f"  AZURE_FORM_RECOGNIZER_ENDPOINT: {'Set' if settings.AZURE_FORM_RECOGNIZER_ENDPOINT else 'NOT SET'}")
        print(f"  AZURE_FORM_RECOGNIZER_KEY: {'Set' if settings.AZURE_FORM_RECOGNIZER_KEY else 'NOT SET'}")
        return
    
    print(f"\n[INFO] Using Azure Document Intelligence:")
    print(f"  Endpoint: {settings.AZURE_FORM_RECOGNIZER_ENDPOINT}")
    print(f"  Model: {settings.AZURE_FORM_RECOGNIZER_MODEL}")
    
    try:
        # Read PDF
        print(f"\n[PROGRESS] Reading PDF file...")
        with open(pdf_file, "rb") as f:
            file_content = f.read()
        print(f"[OK] File read: {len(file_content):,} bytes")
        
        # Initialize Document Intelligence client (REAL, not mock)
        print(f"\n[PROGRESS] Initializing Document Intelligence client...")
        try:
            doc_client = DocumentIntelligenceClient()
            print(f"[OK] Client initialized (REAL DI SERVICE)")
        except ValueError as e:
            print(f"[ERROR] Failed to initialize Document Intelligence client: {e}")
            print(f"[INFO] Make sure AZURE_FORM_RECOGNIZER_ENDPOINT and AZURE_FORM_RECOGNIZER_KEY are set")
            return
        
        # Analyze with Document Intelligence (REAL API CALL)
        print(f"\n[PROGRESS] Analyzing invoice with Azure Document Intelligence...")
        print(f"[INFO] This is a REAL API call - may take 10-30 seconds...")
        doc_data = doc_client.analyze_invoice(file_content)
        
        if not doc_data:
            print(f"[ERROR] Document Intelligence returned no data")
            return
        
        if doc_data.get("error"):
            print(f"[ERROR] Document Intelligence failed: {doc_data.get('error', 'Unknown error')}")
            return
        
        print(f"[OK] Document Intelligence analysis complete (REAL API CALL SUCCESSFUL)!")
        
        # Extract fields using FieldExtractor
        print(f"\n[PROGRESS] Extracting fields using FieldExtractor...")
        field_extractor = FieldExtractor()
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=doc_data,
            file_path=str(pdf_file),
            file_name=pdf_file.name,
            upload_date=datetime.utcnow(),
            invoice_text=doc_data.get("content")
        )
        print(f"[OK] Fields extracted")
        
        # Display results
        print("\n" + "="*80)
        print("REAL DI OCR EXTRACTION RESULTS")
        print("="*80)
        
        # Count extracted fields
        extracted_fields = []
        all_canonical_fields = [
            "invoice_number", "invoice_date", "due_date", "invoice_type", "reference_number",
            "vendor_name", "vendor_id", "vendor_phone", "vendor_fax", "vendor_email", 
            "vendor_website", "vendor_address",
            "gst_number", "qst_number", "pst_number", "business_number",
            "customer_name", "customer_id", "customer_phone", "customer_email", 
            "customer_fax", "bill_to_address",
            "remit_to_address", "remit_to_name",
            "entity", "contract_id", "standing_offer_number", "po_number",
            "period_start", "period_end", "shipping_date", "delivery_date",
            "subtotal", "discount_amount", "shipping_amount", "handling_fee", "deposit_amount",
            "gst_amount", "gst_rate", "hst_amount", "hst_rate", 
            "qst_amount", "qst_rate", "pst_amount", "pst_rate",
            "tax_amount", "total_amount", "currency", "tax_breakdown",
            "payment_terms", "payment_method", "payment_due_upon", 
            "acceptance_percentage", "tax_registration_number"
        ]
        
        print(f"\nEXTRACTED FIELDS:")
        for field in all_canonical_fields:
            value = getattr(invoice, field, None)
            if value is not None and value != "" and value != {}:
                extracted_fields.append(field)
                confidence = invoice.field_confidence.get(field, 0.0) if invoice.field_confidence else 0.0
                icon = "" if confidence >= 0.9 else "" if confidence >= 0.75 else ""
                print(f"  {icon} {field}: {value} (confidence: {confidence:.1%})")
        
        print(f"\nFIELD EXTRACTION SUMMARY:")
        print(f"  Total canonical fields: {len(all_canonical_fields)}")
        print(f"  Fields extracted: {len(extracted_fields)}")
        print(f"  Coverage: {len(extracted_fields)/len(all_canonical_fields)*100:.1f}%")
        print(f"  Target: 75% ({int(len(all_canonical_fields)*0.75)} fields)")
        
        if len(extracted_fields) >= int(len(all_canonical_fields)*0.75):
            print(f"  Status:  MEETS TARGET")
        else:
            print(f"  Status:  BELOW TARGET (needs {int(len(all_canonical_fields)*0.75) - len(extracted_fields)} more fields)")
        
        # Basic fields
        print(f"\nBASIC FIELDS:")
        print(f"  Invoice Number: {invoice.invoice_number or 'N/A'}")
        print(f"  Invoice Date: {invoice.invoice_date or 'N/A'}")
        print(f"  Due Date: {invoice.due_date or 'N/A'}")
        print(f"  Vendor Name: {invoice.vendor_name or 'N/A'}")
        print(f"  Customer Name: {invoice.customer_name or 'N/A'}")
        print(f"  Subtotal: ${invoice.subtotal or 0:,.2f}" if invoice.subtotal else f"  Subtotal: N/A")
        print(f"  Tax Amount: ${invoice.tax_amount or 0:,.2f}" if invoice.tax_amount else f"  Tax Amount: N/A")
        print(f"  Total Amount: ${invoice.total_amount or 0:,.2f}" if invoice.total_amount else f"  Total Amount: N/A")
        print(f"  Currency: {invoice.currency or 'N/A'}")
        print(f"  Payment Terms: {invoice.payment_terms or 'N/A'}")
        print(f"  PO Number: {invoice.po_number or 'N/A'}")
        
        # Addresses
        print(f"\nADDRESSES:")
        if invoice.vendor_address:
            print(f"  Vendor Address: {invoice.vendor_address.street or 'N/A'}, {invoice.vendor_address.city or 'N/A'}, {invoice.vendor_address.province or 'N/A'} {invoice.vendor_address.postal_code or 'N/A'}")
        else:
            print(f"  Vendor Address: N/A")
        
        if invoice.bill_to_address:
            print(f"  Bill To Address: {invoice.bill_to_address.street or 'N/A'}, {invoice.bill_to_address.city or 'N/A'}, {invoice.bill_to_address.province or 'N/A'} {invoice.bill_to_address.postal_code or 'N/A'}")
        else:
            print(f"  Bill To Address: N/A")
        
        if invoice.remit_to_address:
            print(f"  Remit To Address: {invoice.remit_to_address.street or 'N/A'}, {invoice.remit_to_address.city or 'N/A'}, {invoice.remit_to_address.province or 'N/A'} {invoice.remit_to_address.postal_code or 'N/A'}")
        else:
            print(f"  Remit To Address: N/A")
        
        # Canadian tax fields
        canadian_tax_fields = []
        if invoice.gst_amount:
            canadian_tax_fields.append(f"GST Amount: ${invoice.gst_amount:,.2f}")
        if invoice.gst_rate:
            canadian_tax_fields.append(f"GST Rate: {invoice.gst_rate*100:.2f}%")
        if invoice.pst_amount:
            canadian_tax_fields.append(f"PST Amount: ${invoice.pst_amount:,.2f}")
        if invoice.pst_rate:
            canadian_tax_fields.append(f"PST Rate: {invoice.pst_rate*100:.2f}%")
        if invoice.hst_amount:
            canadian_tax_fields.append(f"HST Amount: ${invoice.hst_amount:,.2f}")
        if invoice.hst_rate:
            canadian_tax_fields.append(f"HST Rate: {invoice.hst_rate*100:.2f}%")
        if invoice.qst_amount:
            canadian_tax_fields.append(f"QST Amount: ${invoice.qst_amount:,.2f}")
        if invoice.qst_rate:
            canadian_tax_fields.append(f"QST Rate: {invoice.qst_rate*100:.2f}%")
        
        if canadian_tax_fields:
            print(f"\nCANADIAN TAX FIELDS:")
            for field in canadian_tax_fields:
                print(f"   {field}")
        else:
            print(f"\nCANADIAN TAX FIELDS: None extracted")
        
        # Tax registration numbers
        tax_reg_fields = []
        if invoice.gst_number:
            tax_reg_fields.append(f"GST Number: {invoice.gst_number}")
        if invoice.qst_number:
            tax_reg_fields.append(f"QST Number: {invoice.qst_number}")
        if invoice.pst_number:
            tax_reg_fields.append(f"PST Number: {invoice.pst_number}")
        if invoice.business_number:
            tax_reg_fields.append(f"Business Number: {invoice.business_number}")
        if invoice.tax_registration_number:
            tax_reg_fields.append(f"Tax Registration Number: {invoice.tax_registration_number}")
        
        if tax_reg_fields:
            print(f"\nTAX REGISTRATION NUMBERS:")
            for field in tax_reg_fields:
                print(f"   {field}")
        
        # Line items
        if invoice.line_items:
            print(f"\nLINE ITEMS ({len(invoice.line_items)}):")
            for i, item in enumerate(invoice.line_items[:5], 1):  # Show first 5
                print(f"\n  Item {i}:")
                print(f"    Description: {item.description or 'N/A'}")
                print(f"    Quantity: {item.quantity or 0}")
                print(f"    Unit Price: ${item.unit_price or 0:,.2f}" if item.unit_price else f"    Unit Price: N/A")
                print(f"    Amount: ${item.amount or 0:,.2f}")
                print(f"    Confidence: {item.confidence:.1%}")
            if len(invoice.line_items) > 5:
                print(f"  ... and {len(invoice.line_items) - 5} more items")
        else:
            print(f"\nLINE ITEMS: None extracted")
        
        # OCR Content snippet
        content = doc_data.get('content', '')
        if content:
            print(f"\nOCR CONTENT (first 500 chars):")
            print(f"  {content[:500]}...")
            print(f"  Total content length: {len(content):,} characters")
        
        # Confidence summary
        if invoice.field_confidence:
            print(f"\nCONFIDENCE SUMMARY:")
            high_conf = sum(1 for v in invoice.field_confidence.values() if v >= 0.9)
            med_conf = sum(1 for v in invoice.field_confidence.values() if 0.75 <= v < 0.9)
            low_conf = sum(1 for v in invoice.field_confidence.values() if v < 0.75)
            print(f"  High confidence (≥90%): {high_conf} fields")
            print(f"  Medium confidence (75-89%): {med_conf} fields")
            print(f"  Low confidence (<75%): {low_conf} fields")
            print(f"  Overall confidence: {invoice.extraction_confidence:.1%}")
        
        # Field confidence details
        if invoice.field_confidence:
            print(f"\nFIELD CONFIDENCE SCORES (top 20):")
            sorted_fields = sorted(invoice.field_confidence.items(), key=lambda x: x[1], reverse=True)[:20]
            for field, conf in sorted_fields:
                icon = "" if conf >= 0.9 else "" if conf >= 0.75 else ""
                print(f"  {icon} {field}: {conf:.1%}")
        
        # Raw DI data summary
        print(f"\nRAW DI DATA SUMMARY:")
        print(f"  Keys in DI response: {list(doc_data.keys())}")
        if 'field_confidence' in doc_data:
            print(f"  DI field confidence keys: {list(doc_data['field_confidence'].keys())[:10]}...")
        
        print("\n" + "="*80)
        print("[OK] REAL DI OCR EXTRACTION TEST COMPLETE")
        print("="*80)
        
        return {
            "extracted_fields": extracted_fields,
            "total_fields": len(all_canonical_fields),
            "coverage": len(extracted_fields)/len(all_canonical_fields)*100,
            "meets_target": len(extracted_fields) >= int(len(all_canonical_fields)*0.75),
            "overall_confidence": invoice.extraction_confidence,
            "field_count": len(extracted_fields)
        }
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = test_real_di_ocr()
    if result:
        print(f"\n[RESULT] Coverage: {result['coverage']:.1f}% ({result['field_count']}/{result['total_fields']} fields)")
        print(f"[RESULT] Meets 75% target: {'YES' if result['meets_target'] else 'NO'}")
        print(f"[RESULT] Overall confidence: {result['overall_confidence']:.1%}")

