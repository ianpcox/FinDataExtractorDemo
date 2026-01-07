"""
Test real LLM extraction on a specific PDF document.
This script tests the actual Azure OpenAI LLM (not mock) for field extraction.
"""

import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime
import json

# Fix Windows encoding
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.extraction.extraction_service import ExtractionService
from src.extraction.document_intelligence_client import DocumentIntelligenceClient
from src.extraction.field_extractor import FieldExtractor
from src.ingestion.file_handler import FileHandler
from src.config import settings


async def test_real_llm_extraction():
    """Test real LLM extraction on the specified PDF"""
    print("\n" + "="*80)
    print("REAL LLM EXTRACTION TEST")
    print("="*80)
    
    # Target PDF file
    pdf_file = Path("data/sample_invoices/Raw/Raw_Basic/ACC012 4202092525.pdf")
    
    if not pdf_file.exists():
        print(f"[ERROR] File not found: {pdf_file}")
        return
    
    print(f"\n[INFO] Testing file: {pdf_file}")
    print(f"[INFO] File size: {pdf_file.stat().st_size:,} bytes")
    
    # Check LLM configuration
    if not settings.USE_LLM_FALLBACK:
        print(f"\n[WARNING] USE_LLM_FALLBACK is disabled. Enabling for test...")
        settings.USE_LLM_FALLBACK = True
    
    if not settings.AOAI_ENDPOINT or not settings.AOAI_API_KEY or not settings.AOAI_DEPLOYMENT_NAME:
        print(f"\n[ERROR] Azure OpenAI not configured!")
        print(f"  AOAI_ENDPOINT: {'Set' if settings.AOAI_ENDPOINT else 'NOT SET'}")
        print(f"  AOAI_API_KEY: {'Set' if settings.AOAI_API_KEY else 'NOT SET'}")
        print(f"  AOAI_DEPLOYMENT_NAME: {'Set' if settings.AOAI_DEPLOYMENT_NAME else 'NOT SET'}")
        return
    
    print(f"\n[INFO] Using Azure OpenAI:")
    print(f"  Endpoint: {settings.AOAI_ENDPOINT}")
    print(f"  Deployment: {settings.AOAI_DEPLOYMENT_NAME}")
    print(f"  API Version: {settings.AOAI_API_VERSION}")
    
    try:
        # Initialize services
        print(f"\n[PROGRESS] Initializing services...")
        doc_client = DocumentIntelligenceClient()
        file_handler = FileHandler()
        field_extractor = FieldExtractor()
        extraction_service = ExtractionService(
            doc_intelligence_client=doc_client,
            file_handler=file_handler,
            field_extractor=field_extractor
        )
        
        # Verify it's using real LLM (not mock)
        if not extraction_service._has_aoai_config():
            print(f"[ERROR] LLM configuration check failed!")
            return
        
        print(f"[OK] Services initialized (using REAL LLM)")
        
        # Read PDF
        print(f"\n[PROGRESS] Reading PDF file...")
        with open(pdf_file, "rb") as f:
            file_content = f.read()
        print(f"[OK] File read: {len(file_content):,} bytes")
        
        # Upload file
        print(f"\n[PROGRESS] Uploading file...")
        upload_result = file_handler.upload_file(
            file_content=file_content,
            file_name=pdf_file.name
        )
        file_identifier = upload_result["file_path"]
        print(f"[OK] File uploaded: {file_identifier}")
        
        # Extract invoice
        print(f"\n[PROGRESS] Extracting invoice with DI and LLM...")
        print(f"[INFO] This may take 30-60 seconds...")
        
        import uuid
        invoice_id = f"test-llm-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
        
        result = await extraction_service.extract_invoice(
            invoice_id=invoice_id,
            file_identifier=file_identifier,
            file_name=pdf_file.name,
            upload_date=datetime.utcnow()
        )
        
        if result.get("status") != "extracted":
            print(f"\n[ERROR] Extraction failed: {result.get('status')}")
            print(f"  Errors: {result.get('errors', [])}")
            return
        
        print(f"[OK] Extraction complete!")
        
        # Get extracted invoice
        from src.services.db_service import DatabaseService
        invoice = await DatabaseService.get_invoice(invoice_id)
        
        if not invoice:
            print(f"[ERROR] Could not retrieve invoice from database")
            return
        
        # Display results
        print("\n" + "="*80)
        print("EXTRACTION RESULTS")
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
        
        # Show key fields
        print(f"\nKEY FIELDS:")
        print(f"  Invoice Number: {invoice.invoice_number or 'N/A'}")
        print(f"  Invoice Date: {invoice.invoice_date or 'N/A'}")
        print(f"  Due Date: {invoice.due_date or 'N/A'}")
        print(f"  Vendor Name: {invoice.vendor_name or 'N/A'}")
        print(f"  Customer Name: {invoice.customer_name or 'N/A'}")
        print(f"  PO Number: {invoice.po_number or 'N/A'}")
        print(f"  Subtotal: ${invoice.subtotal or 0:,.2f}" if invoice.subtotal else f"  Subtotal: N/A")
        print(f"  Tax Amount: ${invoice.tax_amount or 0:,.2f}" if invoice.tax_amount else f"  Tax Amount: N/A")
        print(f"  Total Amount: ${invoice.total_amount or 0:,.2f}" if invoice.total_amount else f"  Total Amount: N/A")
        print(f"  Currency: {invoice.currency or 'N/A'}")
        print(f"  Payment Terms: {invoice.payment_terms or 'N/A'}")
        
        # Show Canadian tax fields if present
        canadian_tax_fields = []
        if invoice.gst_amount:
            canadian_tax_fields.append(f"GST: ${invoice.gst_amount:,.2f}")
        if invoice.gst_rate:
            canadian_tax_fields.append(f"GST Rate: {invoice.gst_rate*100:.2f}%")
        if invoice.pst_amount:
            canadian_tax_fields.append(f"PST: ${invoice.pst_amount:,.2f}")
        if invoice.pst_rate:
            canadian_tax_fields.append(f"PST Rate: {invoice.pst_rate*100:.2f}%")
        if invoice.hst_amount:
            canadian_tax_fields.append(f"HST: ${invoice.hst_amount:,.2f}")
        if invoice.hst_rate:
            canadian_tax_fields.append(f"HST Rate: {invoice.hst_rate*100:.2f}%")
        if invoice.qst_amount:
            canadian_tax_fields.append(f"QST: ${invoice.qst_amount:,.2f}")
        if invoice.qst_rate:
            canadian_tax_fields.append(f"QST Rate: {invoice.qst_rate*100:.2f}%")
        
        if canadian_tax_fields:
            print(f"\nCANADIAN TAX FIELDS:")
            for field in canadian_tax_fields:
                print(f"   {field}")
        
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
        
        print("\n" + "="*80)
        print("[OK] LLM EXTRACTION TEST COMPLETE")
        print("="*80)
        
        return {
            "invoice_id": invoice_id,
            "extracted_fields": extracted_fields,
            "total_fields": len(all_canonical_fields),
            "coverage": len(extracted_fields)/len(all_canonical_fields)*100,
            "meets_target": len(extracted_fields) >= int(len(all_canonical_fields)*0.75)
        }
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = asyncio.run(test_real_llm_extraction())
    if result:
        print(f"\n[RESULT] Coverage: {result['coverage']:.1f}% ({result['extracted_fields']}/{result['total_fields']} fields)")
        print(f"[RESULT] Meets 75% target: {'YES' if result['meets_target'] else 'NO'}")

