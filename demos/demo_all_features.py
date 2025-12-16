"""
Demo: Complete Workflow
Runs all demos in sequence to demonstrate the complete workflow.
"""

import time
from pathlib import Path

# Import all demo functions
from demo_01_ingestion import demo_single_upload
from demo_02_extraction import demo_extraction
from demo_03_po_matching import demo_po_matching
from demo_04_pdf_overlay import demo_pdf_overlay
from demo_05_hitl_review import demo_hitl_review
from demo_06_erp_staging import demo_erp_staging


def run_complete_demo():
    """Run all demos in sequence"""
    print("\n" + "="*70)
    print("FIN DATA EXTRACTOR VANILLA - COMPLETE WORKFLOW DEMO")
    print("="*70)
    print("\nThis demo will walk through the complete invoice processing workflow:")
    print("  1. Upload invoice PDF")
    print("  2. Extract structured data")
    print("  3. Match to purchase order")
    print("  4. Generate PDF overlay")
    print("  5. Review and validate")
    print("  6. Stage for ERP")
    print("\n" + "="*70)
    
    input("\nPress Enter to start the demo...")
    
    invoice_id = None
    
    # Step 1: Ingestion
    print("\n" + "="*70)
    print("STEP 1: INVOICE INGESTION")
    print("="*70)
    invoice_id = demo_single_upload()
    if not invoice_id:
        print("\n[ERROR] Demo stopped: Ingestion failed")
        return
    time.sleep(2)
    
    # Step 2: Extraction
    print("\n" + "="*70)
    print("STEP 2: DATA EXTRACTION")
    print("="*70)
    invoice_id = demo_extraction(invoice_id)
    if not invoice_id:
        print("\n[ERROR] Demo stopped: Extraction failed")
        return
    time.sleep(2)
    
    # Step 3: PO Matching
    print("\n" + "="*70)
    print("STEP 3: PO MATCHING")
    print("="*70)
    invoice_id = demo_po_matching(invoice_id)
    if not invoice_id:
        print("\n[WARN] PO Matching skipped or failed, continuing...")
    time.sleep(2)
    
    # Step 4: PDF Overlay
    print("\n" + "="*70)
    print("STEP 4: PDF OVERLAY")
    print("="*70)
    invoice_id = demo_pdf_overlay(invoice_id)
    if not invoice_id:
        print("\n[WARN] PDF Overlay skipped or failed, continuing...")
    time.sleep(2)
    
    # Step 5: HITL Review
    print("\n" + "="*70)
    print("STEP 5: HITL REVIEW")
    print("="*70)
    invoice_id = demo_hitl_review(invoice_id)
    if not invoice_id:
        print("\n[WARN] HITL Review skipped or failed, continuing...")
    time.sleep(2)
    
    # Step 6: ERP Staging
    print("\n" + "="*70)
    print("STEP 6: ERP STAGING")
    print("="*70)
    invoice_id = demo_erp_staging(invoice_id)
    if not invoice_id:
        print("\n[WARN] ERP Staging skipped or failed")
    
    # Summary
    print("\n" + "="*70)
    print("DEMO COMPLETE!")
    print("="*70)
    print("\n[OK] Complete workflow demonstrated:")
    print("  - Invoice uploaded and stored")
    print("  - Data extracted using AI")
    print("  - Matched to purchase order")
    print("  - PDF overlay generated")
    print("  - Reviewed and validated")
    print("  - Staged for ERP integration")
    print("\n[INFO] Check the 'demos/output' directory for generated files:")
    print("   - PDF overlay files")
    print("   - ERP payload files")
    print("\n" + "="*70)


if __name__ == "__main__":
    # Create necessary directories
    sample_dir = Path(__file__).parent / "sample_data"
    output_dir = Path(__file__).parent / "output"
    sample_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    
    run_complete_demo()

