"""Comprehensive demo script for FinDataExtractorVanilla - showcases all features"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Helper functions for output (defined early)
def print_info(msg): print(f"[INFO] {msg}")
def print_success(msg): print(f"[OK] {msg}")
def print_warning(msg): print(f"[WARN] {msg}")
def print_error(msg): print(f"[ERROR] {msg}")

# Fetch credentials from Key Vault first
def fetch_credentials_from_keyvault():
    """Fetch Document Intelligence credentials from Key Vault"""
    try:
        from azure.keyvault.secrets import SecretClient
        from azure.identity import DefaultAzureCredential
        from dotenv import load_dotenv, set_key
        
        env_file = project_root / ".env"
        load_dotenv(env_file)
        
        # Get Key Vault URL
        kv_url = os.getenv("AZURE_KEY_VAULT_URL")
        if not kv_url:
            kv_name = os.getenv("AZURE_KEY_VAULT_NAME", "kvdiofindataextractor")
            kv_url = f"https://{kv_name}.vault.azure.net/"
        
        print_info(f"Fetching credentials from Key Vault: {kv_url}")
        
        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=kv_url, credential=credential)
        
        # Fetch secrets
        secrets = {
            "document-intelligence-endpoint": "AZURE_FORM_RECOGNIZER_ENDPOINT",
            "document-intelligence-key": "AZURE_FORM_RECOGNIZER_KEY"
        }
        
        updated = False
        for secret_name, env_var in secrets.items():
            try:
                secret = client.get_secret(secret_name)
                value = secret.value
                
                # Ensure endpoint has proper format (ends with /)
                if env_var == "AZURE_FORM_RECOGNIZER_ENDPOINT" and value and not value.endswith('/'):
                    value = value.rstrip('/') + '/'
                
                set_key(env_file, env_var, value)
                print_success(f"Retrieved {secret_name}")
                updated = True
            except Exception as e:
                print_warning(f"Could not fetch {secret_name}: {e}")
        
        if updated:
            # Reload environment
            load_dotenv(env_file, override=True)
            print_success("Credentials loaded from Key Vault")
        else:
            print_warning("Could not fetch credentials from Key Vault - using existing .env values")
            
    except Exception as e:
        print_warning(f"Key Vault access failed: {e}")
        print_info("Will use existing .env values if available")

# Fetch credentials before importing settings
fetch_credentials_from_keyvault()

from src.config import settings
from src.ingestion.file_handler import FileHandler
from src.ingestion.pdf_processor import PDFProcessor
from src.ingestion.ingestion_service import IngestionService
from src.extraction.document_intelligence_client import DocumentIntelligenceClient
from src.extraction.field_extractor import FieldExtractor
from src.extraction.extraction_service import ExtractionService
from src.matching.matching_service import MatchingService, MatchStrategy
from src.erp.pdf_overlay_renderer import PDFOverlayRenderer
from src.erp.staging_service import ERPStagingService, ERPPayloadFormat, ERPPayloadGenerator
from src.models.database import AsyncSessionLocal, Base
from src.services.db_service import DatabaseService
from src.models.invoice import Invoice
from sqlalchemy.ext.asyncio import create_async_engine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def print_step(step_num: int, title: str):
    """Print a formatted step header"""
    print(f"\n{'-'*80}")
    print(f"STEP {step_num}: {title}")
    print(f"{'-'*80}\n")


# Helper functions already defined above


async def demo_ingestion(file_content: bytes, file_name: str, db_session) -> Optional[str]:
    """Demo: Invoice Ingestion"""
    print_step(1, "INVOICE INGESTION")
    print_info("Uploading and validating invoice PDF...")
    
    file_handler = FileHandler(use_azure=True)
    pdf_processor = PDFProcessor()
    ingestion_service = IngestionService(
        file_handler=file_handler,
        pdf_processor=pdf_processor
    )
    
    result = await ingestion_service.ingest_invoice(
        file_content=file_content,
        file_name=file_name,
        db=db_session
    )
    
    if result["status"] == "uploaded":
        print_success(f"Invoice ingested successfully!")
        print(f"  • Invoice ID: {result['invoice_id']}")
        print(f"  • File Size: {result['file_size']:,} bytes")
        print(f"  • Pages: {result['page_count']}")
        print(f"  • Upload Date: {result['upload_date']}")
        return result["invoice_id"]
    else:
        print_error(f"Ingestion failed: {result.get('errors', [])}")
        return None


async def demo_extraction(invoice_id: str, file_path: str, file_name: str, upload_date: datetime, db_session):
    """Demo: Data Extraction"""
    print_step(2, "DATA EXTRACTION")
    print_info("Extracting structured data from invoice using Azure Document Intelligence...")
    
    if not settings.AZURE_FORM_RECOGNIZER_ENDPOINT or not settings.AZURE_FORM_RECOGNIZER_KEY:
        print_warning("Azure Document Intelligence not configured - skipping extraction demo")
        print_info("To enable: Set AZURE_FORM_RECOGNIZER_ENDPOINT and AZURE_FORM_RECOGNIZER_KEY in .env")
        return None
    
    doc_intelligence_client = DocumentIntelligenceClient()
    field_extractor = FieldExtractor()
    file_handler = FileHandler(use_azure=True)
    
    extraction_service = ExtractionService(
        doc_intelligence_client=doc_intelligence_client,
        file_handler=file_handler,
        field_extractor=field_extractor
    )
    
    result = await extraction_service.extract_invoice(
        invoice_id=invoice_id,
        file_identifier=file_path,
        file_name=file_name,
        upload_date=upload_date
    )
    
    if result["status"] == "extracted":
        invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
        if invoice:
            print_success("Data extraction completed!")
            print(f"  • Invoice Number: {invoice.invoice_number}")
            print(f"  • Invoice Date: {invoice.invoice_date}")
            print(f"  • Vendor: {invoice.vendor_name}")
            print(f"  • Customer: {invoice.customer_name}")
            print(f"  • Total Amount: {invoice.total_amount} {invoice.currency}")
            print(f"  • Line Items: {len(invoice.line_items)}")
            print(f"  • Overall Confidence: {invoice.extraction_confidence:.1%}")
            print(f"  • Field Confidence Scores:")
            if invoice.field_confidence:
                for field, conf in list(invoice.field_confidence.items())[:5]:
                    print(f"    - {field}: {conf:.1%}")
            return invoice
    else:
        print_error(f"Extraction failed: {result.get('errors', [])}")
        return None


async def demo_po_matching(invoice: Invoice, db_session):
    """Demo: PO Matching"""
    print_step(3, "PO MATCHING")
    print_info("Matching invoice to purchase orders...")
    
    matching_service = MatchingService(db=db_session)
    
    # Sample PO data (in real scenario, this would come from external system)
    sample_pos = [
        {
            "id": "po-001",
            "po_number": invoice.po_number or "PO-12345",
            "po_date": "2024-01-05",
            "vendor_name": invoice.vendor_name or "Acme Corp",
            "vendor_code": "ACME001",
            "total_amount": float(invoice.total_amount) if invoice.total_amount else 1500.00,
            "line_items": []
        }
    ]
    
    match_results = await matching_service.match_invoice_to_po(
        invoice_id=invoice.id,
        po_data=sample_pos[0] if sample_pos else None
    )
    
    if match_results and len(match_results) > 0:
        match_result = match_results[0]
        print_success("PO Match found!")
        print(f"  • Matched PO: {match_result.matched_document_number}")
        print(f"  • Match Confidence: {match_result.confidence:.1%}")
        print(f"  • Match Strategy: {match_result.match_strategy}")
        print(f"  • Match Details:")
        for key, value in match_result.match_details.items():
            print(f"    - {key}: {value}")
    else:
        print_warning("No PO match found")
        print_info("This is normal if no matching PO exists in the system")


async def demo_pdf_overlay(invoice: Invoice, file_path: str):
    """Demo: PDF Overlay with Coding and Approvals"""
    print_step(4, "PDF OVERLAY RENDERING")
    print_info("Generating PDF with financial coding and approval information overlay...")
    
    file_handler = FileHandler(use_azure=True)
    renderer = PDFOverlayRenderer(file_handler=file_handler)
    
    # Add sample approval data
    invoice.bv_approver = "John Smith"
    invoice.bv_approval_date = date.today()
    invoice.fa_approver = "Jane Doe"
    invoice.fa_approval_date = date.today()
    
    try:
        # Download original PDF
        file_content = file_handler.download_file(file_path)
        overlay_pdf = renderer.render_overlay(
            invoice=invoice,
            original_pdf_content=file_content
        )
        
        print_success("PDF overlay generated!")
        print(f"  • Overlay includes:")
        print(f"    - Invoice header information")
        print(f"    - Financial coding (red box)")
        print(f"    - Line item details")
        print(f"    - Approval information")
        print(f"  • Output size: {len(overlay_pdf):,} bytes")
        
        # Save for demo
        output_path = Path("demo_overlay_output.pdf")
        output_path.write_bytes(overlay_pdf)
        print(f"  • Saved to: {output_path}")
        
    except Exception as e:
        print_error(f"Overlay generation failed: {e}")


async def demo_hitl(invoice: Invoice):
    """Demo: Human-in-the-Loop (HITL) Validation"""
    print_step(5, "HUMAN-IN-THE-LOOP (HITL) VALIDATION")
    print_info("Displaying extracted data with confidence scores for validation...")
    
    print("\nExtracted Invoice Data:")
    if invoice.field_confidence:
        print(f"  Invoice Number: {invoice.invoice_number} (Confidence: {invoice.field_confidence.get('invoice_id', 0):.1%})")
        print(f"  Invoice Date: {invoice.invoice_date} (Confidence: {invoice.field_confidence.get('invoice_date', 0):.1%})")
        print(f"  Vendor: {invoice.vendor_name} (Confidence: {invoice.field_confidence.get('vendor_name', 0):.1%})")
        print(f"  Total Amount: {invoice.total_amount} {invoice.currency} (Confidence: {invoice.field_confidence.get('invoice_total', 0):.1%})")
    else:
        print(f"  Invoice Number: {invoice.invoice_number}")
        print(f"  Invoice Date: {invoice.invoice_date}")
        print(f"  Vendor: {invoice.vendor_name}")
        print(f"  Total Amount: {invoice.total_amount} {invoice.currency}")
    
    print("\nField Confidence Scores:")
    if invoice.field_confidence:
        for field, conf in sorted(invoice.field_confidence.items(), key=lambda x: x[1]):
            if conf >= 0.85:
                status = "[OK]"
            elif conf >= 0.70:
                status = "[WARN]"
            else:
                status = "[LOW]"
            print(f"  {status} {field}: {conf:.1%}")
    
    print("\nLine Items:")
    for item in invoice.line_items[:3]:  # Show first 3
        print(f"  • {item.description}: {item.amount} (Confidence: {item.confidence:.1%})")
    
    print_success("HITL data ready for review")
    print_info("Users can validate and correct low-confidence fields via API")


async def demo_erp_staging(invoice: Invoice):
    """Demo: ERP Staging"""
    print_step(6, "ERP STAGING")
    print_info("Staging invoice data for ERP export (MS Dynamics Great Plains)...")
    
    staging_service = ERPStagingService()
    
    # Stage invoice
    staged = await staging_service.stage_invoice(
        invoice_id=invoice.id,
        generate_overlay=False,
        require_approval=False
    )
    
    if staged:
        print_success("Invoice staged for ERP export!")
        
        # Generate previews in different formats
        formats = [
            (ERPPayloadFormat.JSON, "JSON"),
            (ERPPayloadFormat.CSV, "CSV"),
            (ERPPayloadFormat.XML, "XML"),
            (ERPPayloadFormat.DYNAMICS_GP, "Dynamics GP")
        ]
        
        print("\nAvailable Export Formats:")
        for fmt, name in formats:
            try:
                generator = ERPPayloadGenerator(erp_format=fmt)
                payload_result = generator.generate_payload(
                    invoice=invoice,
                    include_overlay_pdf=False
                )
                payload_str = payload_result.get("payload", "")
                print(f"  • {name}: {len(payload_str):,} bytes")
            except Exception as e:
                print(f"  • {name}: Error - {e}")
        
        print_info("Staged data ready for batch export or direct integration")


async def get_sample_file_from_azure() -> Optional[tuple]:
    """Get a sample file from Azure Blob Storage"""
    try:
        from azure.storage.blob import BlobServiceClient
        
        connection_string = settings.AZURE_STORAGE_CONNECTION_STRING
        if not connection_string:
            return None
        
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(
            settings.AZURE_STORAGE_CONTAINER_RAW
        )
        
        # Get first PDF
        blobs = container_client.list_blobs()
        for blob in blobs:
            if blob.name.lower().endswith('.pdf'):
                file_content = container_client.get_blob_client(blob.name).download_blob().readall()
                return (file_content, blob.name)
        
        return None
    except Exception as e:
        logger.error(f"Error getting file from Azure: {e}")
        return None


async def main():
    """Main demo function"""
    print_section("FinDataExtractorVanilla - Complete Feature Demo")
    print("This demo showcases all major features of the invoice processing system.\n")
    
    # Create database tables
    print_info("Initializing database...")
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print_success("Database ready\n")
    
    # Get sample file
    print_info("Fetching sample invoice from Azure Blob Storage...")
    file_data = await get_sample_file_from_azure()
    
    if not file_data:
        print_error("No files found in Azure storage or connection failed")
        print_info("Please ensure:")
        print("  1. Azure Blob Storage is configured in .env")
        print("  2. Container 'invoices-raw' contains PDF files")
        return
    
    file_content, file_name = file_data
    print_success(f"Found sample file: {file_name} ({len(file_content):,} bytes)\n")
    
    # Run demos
    async with AsyncSessionLocal() as db_session:
        # 1. Ingestion
        invoice_id = await demo_ingestion(file_content, file_name, db_session)
        if not invoice_id:
            print_error("Demo stopped: Ingestion failed")
            return
        
        # Get invoice record
        invoice_record = await DatabaseService.get_invoice(invoice_id, db=db_session)
        if not invoice_record:
            print_error("Demo stopped: Could not retrieve invoice")
            return
        
        # 2. Extraction
        invoice = await demo_extraction(
            invoice_id,
            invoice_record.file_path,
            invoice_record.file_name,
            invoice_record.upload_date,
            db_session
        )
        
        if not invoice:
            print_warning("Extraction demo skipped - using basic invoice data")
            # Convert DB model to Pydantic model for demos
            from src.models.db_utils import db_to_pydantic_invoice
            invoice = db_to_pydantic_invoice(invoice_record)
        
        # 3. PO Matching
        await demo_po_matching(invoice, db_session)
        
        # 4. PDF Overlay
        await demo_pdf_overlay(invoice, invoice_record.file_path)
        
        # 5. HITL
        await demo_hitl(invoice)
        
        # 6. ERP Staging
        await demo_erp_staging(invoice)
    
    # Summary
    print_section("Demo Complete")
    print_success("All features demonstrated successfully!")
    print("\nNext Steps:")
    print("  1. Review the generated overlay PDF: demo_overlay_output.pdf")
    print("  2. Check the database for the processed invoice")
    print("  3. Use the API endpoints for production workflows")
    print("  4. Configure Azure Document Intelligence for full extraction capabilities")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\n\nDemo error: {e}")
        import traceback
        traceback.print_exc()

