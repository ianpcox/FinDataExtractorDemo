"""
Script to process invoices from Azure Blob Storage
Downloads invoices from a specific path and runs them through the end-to-end workflow
"""

import asyncio
import sys
import os
from pathlib import Path

# Fix Windows encoding
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')  # Set UTF-8
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.azure_blob_utils import AzureBlobBrowser
from src.ingestion.ingestion_service import IngestionService
from src.ingestion.file_handler import FileHandler
from src.ingestion.pdf_processor import PDFProcessor
from src.extraction.extraction_service import ExtractionService
from src.extraction.document_intelligence_client import DocumentIntelligenceClient
from src.extraction.field_extractor import FieldExtractor
from src.services.db_service import DatabaseService
from src.models.database import get_db
import logging
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def process_invoice_from_azure(
    container_name: str,
    blob_path: str,
    run_extraction: bool = True
):
    """
    Process a single invoice from Azure Blob Storage
    
    Args:
        container_name: Azure container name
        blob_path: Path to the blob (e.g., "RAW Basic/invoice.pdf")
        run_extraction: Whether to run extraction after ingestion
    """
    try:
        print(f"\n{'='*60}")
        print(f"Processing Invoice from Azure")
        print(f"{'='*60}")
        print(f"Container: {container_name}")
        print(f"Blob Path: {blob_path}")
        print(f"{'='*60}\n")
        
        # Step 1: Download from Azure
        browser = AzureBlobBrowser()
        print(f"[DOWNLOAD] Downloading blob from Azure...")
        file_content = browser.download_blob(container_name, blob_path)
        file_name = blob_path.split("/")[-1]
        print(f"[OK] Downloaded: {file_name} ({len(file_content):,} bytes)")
        
        # Step 2: Ingest invoice
        print(f"\n[INGEST] Ingesting invoice...")
        ingestion_service = IngestionService(
            file_handler=FileHandler(use_azure=True),
            pdf_processor=PDFProcessor()
        )
        
        ingest_result = await ingestion_service.ingest_invoice(
            file_content=file_content,
            file_name=file_name
        )
        
        if ingest_result["status"] != "uploaded":
            print(f"[ERROR] Ingestion failed: {ingest_result.get('errors', [])}")
            return None
        
        invoice_id = ingest_result["invoice_id"]
        print(f"[OK] Invoice ingested: {invoice_id}")
        print(f"   File Size: {ingest_result['file_size']:,} bytes")
        print(f"   Pages: {ingest_result['page_count']}")
        
        # Step 3: Extract invoice
        # Helper to safely convert to float for printing
        def to_number(val, default=0.0):
            try:
                if val is None:
                    return default
                if isinstance(val, (int, float)):
                    return float(val)
                return float(str(val).replace(",", ""))
            except Exception:
                return default

        if run_extraction:
            print(f"\n[EXTRACT] Extracting invoice data...")
            extraction_service = ExtractionService(
                doc_intelligence_client=DocumentIntelligenceClient(),
                file_handler=FileHandler(use_azure=True),
                field_extractor=FieldExtractor()
            )
            
            extraction_result = await extraction_service.extract_invoice(
                invoice_id=invoice_id,
                file_identifier=ingest_result["file_path"],
                file_name=file_name,
                upload_date=ingest_result["upload_date"]
            )
            
            if extraction_result["status"] == "extracted":
                invoice = extraction_result.get("invoice", {})
                print(f"[OK] Extraction completed!")
                print(f"   Invoice Number: {invoice.get('invoice_number', 'N/A')}")
                print(f"   Vendor: {invoice.get('vendor_name', 'N/A')}")
                print(f"   Total: ${to_number(invoice.get('total_amount')):,.2f}")
                print(f"   Confidence: {extraction_result.get('confidence', 0):.1%}")
            else:
                print(f"[WARNING] Extraction completed with warnings: {extraction_result.get('errors', [])}")
        
        print(f"\n{'='*60}")
        print(f"[OK] Processing Complete!")
        print(f"{'='*60}")
        print(f"Invoice ID: {invoice_id}")
        print(f"\nNext steps:")
        print(f"   - Review in Streamlit: streamlit run streamlit_app.py")
        print(f"   - View in API: http://localhost:8000/api/hitl/invoice/{invoice_id}")
        
        return invoice_id
        
    except Exception as e:
        logger.error(f"Error processing invoice: {e}", exc_info=True)
        print(f"\n[ERROR] Error: {e}")
        return None


async def process_batch_from_azure(
    container_name: str,
    prefix: str = None,
    file_extension: str = "pdf",
    max_files: int = 10,
    run_extraction: bool = True
):
    """
    Process multiple invoices from Azure Blob Storage
    
    Args:
        container_name: Azure container name
        prefix: Path prefix (e.g., "RAW Basic/" or "Raw_Basic/")
        file_extension: File extension to filter (default: "pdf")
        max_files: Maximum number of files to process
        run_extraction: Whether to run extraction after ingestion
    """
    try:
        print(f"\n{'='*60}")
        print(f"Batch Processing Invoices from Azure")
        print(f"{'='*60}")
        print(f"Container: {container_name}")
        print(f"Prefix: {prefix or '(all files)'}")
        print(f"Extension: .{file_extension}")
        print(f"Max Files: {max_files}")
        print(f"{'='*60}\n")
        
        # List blobs
        browser = AzureBlobBrowser()
        print(f"[LIST] Listing blobs...")
        blobs = browser.list_blobs(container_name=container_name, prefix=prefix)
        
        # Filter by extension
        if file_extension:
            blobs = [
                blob for blob in blobs
                if blob["name"].lower().endswith(f".{file_extension.lower()}")
            ]
        
        # Limit number of files
        blobs = blobs[:max_files]
        
        print(f"[OK] Found {len(blobs)} files to process\n")
        
        results = []
        errors = []
        
        for i, blob in enumerate(blobs, 1):
            print(f"\n[{i}/{len(blobs)}] Processing: {blob['name']}")
            print("-" * 60)
            
            invoice_id = await process_invoice_from_azure(
                container_name=container_name,
                blob_path=blob["name"],
                run_extraction=run_extraction
            )
            
            if invoice_id:
                results.append({
                    "blob_name": blob["name"],
                    "invoice_id": invoice_id
                })
            else:
                errors.append({
                    "blob_name": blob["name"],
                    "error": "Processing failed"
                })
        
        # Summary
        print(f"\n{'='*60}")
        print(f"Batch Processing Complete")
        print(f"{'='*60}")
        print(f"Total: {len(blobs)}")
        print(f"[OK] Successful: {len(results)}")
        print(f"[ERROR] Failed: {len(errors)}")
        
        if errors:
            print(f"\nErrors:")
            for error in errors:
                print(f"  - {error['blob_name']}: {error['error']}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error processing batch: {e}", exc_info=True)
        print(f"\n[ERROR] Error: {e}")
        return []


async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Process invoices from Azure Blob Storage")
    parser.add_argument("--container", required=True, help="Azure container name")
    parser.add_argument("--blob-path", help="Specific blob path (e.g., 'RAW Basic/invoice.pdf')")
    parser.add_argument("--prefix", help="Path prefix for batch processing (e.g., 'RAW Basic/')")
    parser.add_argument("--extension", default="pdf", help="File extension filter (default: pdf)")
    parser.add_argument("--max-files", type=int, default=10, help="Max files for batch (default: 10)")
    parser.add_argument("--no-extraction", action="store_true", help="Skip extraction step")
    
    args = parser.parse_args()
    
    if args.blob_path:
        # Process single file
        await process_invoice_from_azure(
            container_name=args.container,
            blob_path=args.blob_path,
            run_extraction=not args.no_extraction
        )
    else:
        # Process batch
        await process_batch_from_azure(
            container_name=args.container,
            prefix=args.prefix,
            file_extension=args.extension,
            max_files=args.max_files,
            run_extraction=not args.no_extraction
        )


if __name__ == "__main__":
    asyncio.run(main())

