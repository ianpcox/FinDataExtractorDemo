"""
Test text-based LLM extraction on a specific PDF document
"""

import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime
from decimal import Decimal

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
from src.models.invoice import Invoice


async def test_llm_extraction():
    """Test LLM extraction on the specified PDF"""
    print("\n" + "="*80)
    print("TEXT-BASED LLM EXTRACTION TEST")
    print("="*80)
    
    # Target PDF file
    pdf_file = Path("data/sample_invoices/Raw/Raw_Basic/ACC012 4202092525.pdf")
    
    if not pdf_file.exists():
        print(f"[ERROR] File not found: {pdf_file}")
        return
    
    print(f"\n[INFO] Testing file: {pdf_file}")
    print(f"[INFO] File size: {pdf_file.stat().st_size:,} bytes")
    
    try:
        # Read PDF
        print(f"\n[PROGRESS] Reading PDF file...")
        with open(pdf_file, "rb") as f:
            file_content = f.read()
        print(f"[OK] File read: {len(file_content):,} bytes")
        
        # Initialize services
        print(f"\n[PROGRESS] Initializing services...")
        try:
            doc_client = DocumentIntelligenceClient()
            print(f"[OK] Document Intelligence client initialized")
        except ValueError as e:
            print(f"[ERROR] Failed to initialize Document Intelligence client: {e}")
            return
        
        file_handler = FileHandler()
        field_extractor = FieldExtractor()
        extraction_service = ExtractionService(
            doc_intelligence_client=doc_client,
            file_handler=file_handler,
            field_extractor=field_extractor
        )
        
        # Analyze with Document Intelligence
        print(f"\n[PROGRESS] Analyzing invoice with Azure Document Intelligence...")
        print(f"[INFO] This may take 10-30 seconds...")
        doc_data = doc_client.analyze_invoice(file_content)
        
        if not doc_data or doc_data.get("error"):
            print(f"[ERROR] Document Intelligence failed: {doc_data.get('error', 'Unknown error')}")
            return
        
        print(f"[OK] Document Intelligence analysis complete!")
        
        # Extract invoice using FieldExtractor
        print(f"\n[PROGRESS] Extracting invoice fields...")
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=doc_data,
            file_path=str(pdf_file),
            file_name=pdf_file.name,
            upload_date=datetime.utcnow(),
            invoice_text=doc_data.get("content")
        )
        
        print(f"[OK] Initial extraction complete!")
        
        # Identify low-confidence fields
        fc = invoice.field_confidence or {}
        low_conf_threshold = 0.75
        low_conf_fields = []
        
        # Check all canonical fields
        canonical_fields = [
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
            "acceptance_percentage", "tax_registration_number",
        ]
        
        for field in canonical_fields:
            val = getattr(invoice, field, None)
            conf = fc.get(field)
            if val in (None, "", {}) or conf is None or conf < low_conf_threshold:
                low_conf_fields.append(field)
        
        print(f"\n[INFO] Found {len(low_conf_fields)} low-confidence fields:")
        print(f"  {', '.join(low_conf_fields[:10])}{'...' if len(low_conf_fields) > 10 else ''}")
        
        if not low_conf_fields:
            print(f"\n[INFO] No low-confidence fields found. All fields have sufficient confidence.")
            return
        
        # Test LLM extraction
        print(f"\n[PROGRESS] Testing LLM extraction for {len(low_conf_fields)} fields...")
        print(f"[INFO] This may take 30-60 seconds...")
        
        di_data = {
            "content": doc_data.get("content") or "",
            "invoice_number": invoice.invoice_number,
            "vendor_name": invoice.vendor_name,
            "total_amount": str(invoice.total_amount) if invoice.total_amount else None,
        }
        
        # Run LLM fallback
        llm_result = await extraction_service._run_low_confidence_fallback(
            invoice,
            low_conf_fields,
            di_data,
            fc,
            invoice_id="test-invoice-llm"
        )
        
        print(f"\n[OK] LLM extraction complete!")
        print(f"\n[RESULTS]")
        print(f"  Success: {llm_result.get('success', False)}")
        print(f"  Groups Processed: {llm_result.get('groups_processed', 0)}")
        print(f"  Groups Succeeded: {llm_result.get('groups_succeeded', 0)}")
        print(f"  Groups Failed: {llm_result.get('groups_failed', 0)}")
        
        # Show field improvements
        print(f"\n[FIELD IMPROVEMENTS]")
        improved_fields = []
        for field in low_conf_fields:
            before_val = getattr(invoice, field, None)
            if before_val not in (None, "", {}):
                improved_fields.append(field)
        
        if improved_fields:
            print(f"  Fields improved: {len(improved_fields)}")
            for field in improved_fields[:10]:
                val = getattr(invoice, field, None)
                conf = invoice.field_confidence.get(field, 0.0) if invoice.field_confidence else 0.0
                print(f"    - {field}: {val} (confidence: {conf:.1%})")
        else:
            print(f"  No fields were improved by LLM")
        
        # Show extracted values
        print(f"\n[EXTRACTED VALUES]")
        key_fields = [
            "invoice_number", "invoice_date", "due_date",
            "vendor_name", "customer_name",
            "subtotal", "tax_amount", "total_amount", "currency",
            "payment_terms", "po_number",
        ]
        for field in key_fields:
            val = getattr(invoice, field, None)
            conf = invoice.field_confidence.get(field, 0.0) if invoice.field_confidence else 0.0
            if val not in (None, "", {}):
                print(f"  {field}: {val} (confidence: {conf:.1%})")
        
        print("\n" + "="*80)
        print("[OK] LLM EXTRACTION TEST COMPLETE")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_llm_extraction())

