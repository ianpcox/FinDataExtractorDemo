"""
Direct extraction test - bypasses API to show what gets extracted
"""

import sys
import os
import asyncio
from pathlib import Path
from datetime import datetime

# Fix Windows encoding
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.extraction.document_intelligence_client import DocumentIntelligenceClient
from src.extraction.field_extractor import FieldExtractor
from src.ingestion.file_handler import FileHandler


async def test_extraction():
    """Test extraction directly"""
    print("\n" + "="*80)
    print("DIRECT EXTRACTION TEST - BYPASSING API")
    print("="*80)
    
    # Find sample PDF
    sample_dir = Path(__file__).parent.parent / "demos" / "sample_data"
    pdf_files = list(sample_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"[ERROR] No PDF files found in {sample_dir}")
        return
    
    pdf_file = pdf_files[0]
    print(f"\n[INFO] Using file: {pdf_file.name} ({pdf_file.stat().st_size:,} bytes)")
    
    try:
        # Read PDF
        print(f"\n[PROGRESS] Reading PDF file...")
        with open(pdf_file, "rb") as f:
            file_content = f.read()
        print(f"[OK] File read: {len(file_content):,} bytes")
        
        # Initialize clients
        print(f"\n[PROGRESS] Initializing Document Intelligence client...")
        doc_client = DocumentIntelligenceClient()
        field_extractor = FieldExtractor()
        
        # Analyze with Document Intelligence
        print(f"\n[PROGRESS] Analyzing invoice with Azure Document Intelligence...")
        print(f"[INFO] This may take 10-30 seconds...")
        doc_data = doc_client.analyze_invoice(file_content)
        
        if not doc_data or doc_data.get("error"):
            print(f"[ERROR] Document Intelligence failed: {doc_data.get('error', 'Unknown error')}")
            return
        
        print(f"[OK] Document Intelligence analysis complete!")
        
        # Extract fields
        print(f"\n[PROGRESS] Extracting fields...")
        invoice = field_extractor.extract_invoice(
            doc_intelligence_data=doc_data,
            file_path=str(pdf_file),
            file_name=pdf_file.name,
            upload_date=datetime.utcnow(),
            invoice_text=None
        )
        
        print("\n" + "="*80)
        print("[OK] EXTRACTION SUCCESSFUL!")
        print("="*80)
        
        print(f"\nEXTRACTED INVOICE DATA:")
        print(f"  Invoice Number: {invoice.invoice_number or 'N/A'}")
        print(f"  Invoice Date: {invoice.invoice_date or 'N/A'}")
        print(f"  Vendor Name: {invoice.vendor_name or 'N/A'}")
        print(f"  Customer Name: {invoice.customer_name or 'N/A'}")
        print(f"  Subtotal: ${invoice.subtotal or 0:,.2f}")
        print(f"  Tax Amount: ${invoice.tax_amount or 0:,.2f}")
        print(f"  Total Amount: ${invoice.total_amount or 0:,.2f}")
        print(f"  Currency: {invoice.currency or 'N/A'}")
        
        # Line items
        if invoice.line_items:
            print(f"\nLINE ITEMS ({len(invoice.line_items)}):")
            for i, item in enumerate(invoice.line_items, 1):
                print(f"\n  Item {i}:")
                print(f"    Description: {item.description or 'N/A'}")
                print(f"    Quantity: {item.quantity or 0}")
                print(f"    Unit Price: ${item.unit_price or 0:,.2f}")
                print(f"    Amount: ${item.amount or 0:,.2f}")
        else:
            print("\n  No line items extracted")
        
        # Confidence scores
        if invoice.field_confidence:
            print(f"\nFIELD CONFIDENCE SCORES:")
            for field, confidence in sorted(invoice.field_confidence.items(), key=lambda x: x[1], reverse=True)[:10]:
                icon = "[OK]" if confidence >= 0.9 else "[WARN]" if confidence >= 0.7 else "[LOW]"
                print(f"  {icon} {field}: {confidence:.1%}")
            
            print(f"\n  Overall Confidence: {invoice.extraction_confidence:.1%}")
        
        # Subtype
        if invoice.invoice_subtype:
            print(f"\nINVOICE SUBTYPE: {invoice.invoice_subtype}")
            if invoice.extensions:
                print(f"  Extensions: {list(invoice.extensions.keys())}")
        
        print("\n" + "="*80)
        print("[OK] EXTRACTION TEST COMPLETE")
        print("="*80)
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_extraction())

