"""
Test REAL multimodal LLM extraction directly (bypassing database).
This script tests the actual Azure OpenAI multimodal LLM (not mock) for field extraction.
"""

import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime
import uuid

# Fix Windows encoding
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.extraction.extraction_service import ExtractionService
from src.extraction.document_intelligence_client import DocumentIntelligenceClient
from src.extraction.field_extractor import FieldExtractor
from src.ingestion.file_handler import FileHandler
from src.config import settings


async def test_real_multimodal_llm_direct():
    """Test real multimodal LLM extraction directly (bypassing database)"""
    print("\n" + "="*80)
    print("REAL MULTIMODAL LLM EXTRACTION TEST (DIRECT)")
    print("="*80)
    
    # Target PDF file
    pdf_file = Path("data/sample_invoices/Raw/Raw_Basic/ACC012 4202092525.pdf")
    
    if not pdf_file.exists():
        print(f"[ERROR] File not found: {pdf_file}")
        return
    
    print(f"\n[INFO] Testing file: {pdf_file}")
    print(f"[INFO] File size: {pdf_file.stat().st_size:,} bytes")
    
    # Check multimodal LLM configuration
    if not settings.USE_MULTIMODAL_LLM_FALLBACK:
        print(f"\n[WARNING] USE_MULTIMODAL_LLM_FALLBACK is disabled. Enabling for test...")
        settings.USE_MULTIMODAL_LLM_FALLBACK = True
    
    if not settings.AOAI_ENDPOINT or not settings.AOAI_API_KEY:
        print(f"\n[ERROR] Azure OpenAI not configured!")
        print(f"  AOAI_ENDPOINT: {'Set' if settings.AOAI_ENDPOINT else 'NOT SET'}")
        print(f"  AOAI_API_KEY: {'Set' if settings.AOAI_API_KEY else 'NOT SET'}")
        return
    
    multimodal_deployment = settings.AOAI_MULTIMODAL_DEPLOYMENT_NAME or settings.AOAI_DEPLOYMENT_NAME
    if not multimodal_deployment:
        print(f"\n[ERROR] Multimodal deployment not configured!")
        return
    
    print(f"\n[INFO] Using Azure OpenAI Multimodal:")
    print(f"  Endpoint: {settings.AOAI_ENDPOINT}")
    print(f"  Deployment: {multimodal_deployment}")
    print(f"  API Version: {settings.AOAI_API_VERSION}")
    print(f"  Max Pages: {settings.MULTIMODAL_MAX_PAGES}")
    print(f"  Image Scale: {settings.MULTIMODAL_IMAGE_SCALE}")
    
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
        
        # Verify it's using real multimodal LLM (not mock)
        if not extraction_service._has_multimodal_config():
            print(f"[ERROR] Multimodal LLM configuration check failed!")
            return
        
        print(f"[OK] Services initialized (using REAL MULTIMODAL LLM)")
        
        # Read PDF
        print(f"\n[PROGRESS] Reading PDF file...")
        with open(pdf_file, "rb") as f:
            file_content = f.read()
        print(f"[OK] File read: {len(file_content):,} bytes")
        
        # Check if PDF is scanned
        is_scanned = extraction_service._is_scanned_pdf(file_content)
        print(f"[INFO] PDF is scanned/image-based: {is_scanned}")
        
        # Test image rendering
        print(f"\n[PROGRESS] Testing PDF page rendering...")
        images = extraction_service._render_multimodal_images(file_content)
        print(f"[OK] Rendered {len(images)} page(s) as base64 PNG images")
        if images:
            print(f"[INFO] First image size: {len(images[0]):,} base64 characters")
        
        # Step 1: Analyze with Document Intelligence
        print(f"\n[PROGRESS] Analyzing invoice with Document Intelligence...")
        print(f"[INFO] This may take 10-30 seconds...")
        doc_data = await asyncio.to_thread(doc_client.analyze_invoice, file_content)
        
        if not doc_data or doc_data.get("error"):
            print(f"[ERROR] Document Intelligence failed: {doc_data.get('error', 'Unknown error')}")
            return
        
        print(f"[OK] Document Intelligence analysis complete!")
        
        # Step 2: Extract fields using FieldExtractor
        print(f"\n[PROGRESS] Extracting fields using FieldExtractor...")
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=doc_data,
            file_path=str(pdf_file),
            file_name=pdf_file.name,
            upload_date=datetime.utcnow(),
            invoice_text=doc_data.get("content")
        )
        print(f"[OK] Fields extracted")
        
        # Step 3: Identify low-confidence fields
        print(f"\n[PROGRESS] Identifying low-confidence fields...")
        low_conf_threshold = getattr(settings, "LLM_LOW_CONF_THRESHOLD", 0.75)
        low_conf_fields = []
        fc = invoice.field_confidence or {}
        
        def _is_blank(value):
            if value is None:
                return True
            if isinstance(value, str):
                return value.strip() == "" or value.strip().lower() == "not extracted"
            if isinstance(value, (list, dict)):
                return len(value) == 0
            return False
        
        # Check all canonical fields
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
        
        for field in all_canonical_fields:
            val = getattr(invoice, field, None)
            conf = fc.get(field)
            if _is_blank(val) or conf is None or conf < low_conf_threshold:
                low_conf_fields.append(field)
        
        print(f"[INFO] Found {len(low_conf_fields)} low-confidence fields")
        if low_conf_fields:
            print(f"[INFO] Low-confidence fields: {low_conf_fields[:10]}{'...' if len(low_conf_fields) > 10 else ''}")
        
        # Step 4: Run multimodal LLM fallback
        if low_conf_fields and extraction_service._has_multimodal_config():
            print(f"\n[PROGRESS] Running multimodal LLM fallback...")
            print(f"[INFO] This is a REAL multimodal LLM API call - may take 30-60 seconds...")
            print(f"[INFO] Processing {len(low_conf_fields)} low-confidence fields with multimodal LLM...")
            
            multimodal_result = await extraction_service._run_multimodal_fallback(
                invoice=invoice,
                low_conf_fields=low_conf_fields,
                di_data=doc_data,
                di_field_confidence=fc,
                file_content=file_content,
                invoice_id=None
            )
            
            if multimodal_result.get("success"):
                print(f"[OK] Multimodal LLM fallback completed successfully!")
                print(f"[INFO] Groups succeeded: {multimodal_result.get('groups_succeeded', 0)}")
                print(f"[INFO] Groups failed: {multimodal_result.get('groups_failed', 0)}")
            else:
                print(f"[WARNING] Multimodal LLM fallback did not succeed")
                print(f"[INFO] Groups succeeded: {multimodal_result.get('groups_succeeded', 0)}")
                print(f"[INFO] Groups failed: {multimodal_result.get('groups_failed', 0)}")
        else:
            print(f"\n[INFO] Skipping multimodal LLM fallback:")
            if not low_conf_fields:
                print(f"  - No low-confidence fields found")
            if not extraction_service._has_multimodal_config():
                print(f"  - Multimodal LLM not configured")
        
        # Display results
        print("\n" + "="*80)
        print("MULTIMODAL LLM EXTRACTION RESULTS")
        print("="*80)
        
        # Count extracted fields
        extracted_fields = []
        for field in all_canonical_fields:
            value = getattr(invoice, field, None)
            if value is not None and value != "" and value != {}:
                extracted_fields.append(field)
        
        print(f"\nEXTRACTED FIELDS ({len(extracted_fields)}/{len(all_canonical_fields)}):")
        for field in extracted_fields[:20]:  # Show first 20
            value = getattr(invoice, field, None)
            confidence = invoice.field_confidence.get(field, 0.0) if invoice.field_confidence else 0.0
            icon = "" if confidence >= 0.9 else "" if confidence >= 0.75 else ""
            print(f"  {icon} {field}: {value} (confidence: {confidence:.1%})")
        if len(extracted_fields) > 20:
            print(f"  ... and {len(extracted_fields) - 20} more fields")
        
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
        else:
            print(f"\nCANADIAN TAX FIELDS: None extracted")
        
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
        print("[OK] REAL MULTIMODAL LLM EXTRACTION TEST COMPLETE")
        print("="*80)
        
        return {
            "extracted_fields": extracted_fields,
            "total_fields": len(all_canonical_fields),
            "coverage": len(extracted_fields)/len(all_canonical_fields)*100,
            "meets_target": len(extracted_fields) >= int(len(all_canonical_fields)*0.75),
            "is_scanned": is_scanned,
            "images_rendered": len(images),
            "multimodal_success": multimodal_result.get("success", False) if low_conf_fields else None
        }
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = asyncio.run(test_real_multimodal_llm_direct())
    if result:
        print(f"\n[RESULT] Coverage: {result['coverage']:.1f}% ({len(result['extracted_fields'])}/{result['total_fields']} fields)")
        print(f"[RESULT] Meets 75% target: {'YES' if result['meets_target'] else 'NO'}")
        print(f"[RESULT] PDF is scanned: {'YES' if result['is_scanned'] else 'NO'}")
        print(f"[RESULT] Images rendered: {result['images_rendered']} page(s)")
        if result['multimodal_success'] is not None:
            print(f"[RESULT] Multimodal LLM success: {'YES' if result['multimodal_success'] else 'NO'}")

