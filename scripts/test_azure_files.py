"""Test script to process sample files from Azure Blob Storage"""

import asyncio
import sys
from pathlib import Path
from typing import List, Optional
import logging

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import settings
from src.ingestion.file_handler import FileHandler
from src.ingestion.pdf_processor import PDFProcessor
from src.ingestion.ingestion_service import IngestionService
from src.extraction.document_intelligence_client import DocumentIntelligenceClient
from src.extraction.field_extractor import FieldExtractor
from src.extraction.extraction_service import ExtractionService
from src.models.database import AsyncSessionLocal, Base
from src.services.db_service import DatabaseService
from sqlalchemy.ext.asyncio import create_async_engine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def list_azure_files(container_name: str, max_files: int = 10) -> List[str]:
    """List files in Azure Blob Storage container"""
    try:
        from azure.storage.blob import BlobServiceClient
        
        connection_string = settings.AZURE_STORAGE_CONNECTION_STRING
        if not connection_string:
            logger.error("AZURE_STORAGE_CONNECTION_STRING not set in .env")
            return []
        
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service_client.get_container_client(container_name)
        
        logger.info(f"Listing files in container: {container_name}")
        blobs = container_client.list_blobs()
        
        file_list = []
        count = 0
        for blob in blobs:
            if blob.name.lower().endswith('.pdf'):
                file_list.append(blob.name)
                logger.info(f"  Found: {blob.name} ({blob.size} bytes)")
                count += 1
                if count >= max_files:
                    break
        
        return file_list
        
    except Exception as e:
        logger.error(f"Error listing Azure files: {e}", exc_info=True)
        return []


async def test_file_processing(blob_name: str, container_name: str):
    """Test processing a single file from Azure"""
    logger.info(f"\n{'='*70}")
    logger.info(f"Testing file: {blob_name}")
    logger.info(f"{'='*70}\n")
    
    try:
        # Initialize services
        file_handler = FileHandler(use_azure=True)
        pdf_processor = PDFProcessor()
        ingestion_service = IngestionService(
            file_handler=file_handler,
            pdf_processor=pdf_processor
        )
        
        # Download file from Azure
        logger.info("Downloading file from Azure...")
        file_content = file_handler.download_file(blob_name)
        logger.info(f"Downloaded {len(file_content)} bytes")
        
        # Extract filename from blob name
        file_name = Path(blob_name).name
        
        # Test ingestion
        logger.info("\n--- Testing Ingestion ---")
        async with AsyncSessionLocal() as db_session:
            ingest_result = await ingestion_service.ingest_invoice(
                file_content=file_content,
                file_name=file_name,
                db=db_session
            )
            
            logger.info(f"Ingestion status: {ingest_result['status']}")
            if ingest_result['status'] == 'uploaded':
                logger.info(f"  Invoice ID: {ingest_result['invoice_id']}")
                logger.info(f"  File size: {ingest_result['file_size']} bytes")
                logger.info(f"  Page count: {ingest_result['page_count']}")
            else:
                logger.error(f"  Errors: {ingest_result.get('errors', [])}")
                return
        
        # Test extraction (if Azure Document Intelligence is configured)
        if settings.AZURE_FORM_RECOGNIZER_ENDPOINT and settings.AZURE_FORM_RECOGNIZER_KEY:
            logger.info("\n--- Testing Extraction ---")
            
            doc_intelligence_client = DocumentIntelligenceClient()
            field_extractor = FieldExtractor()
            extraction_service = ExtractionService(
                doc_intelligence_client=doc_intelligence_client,
                file_handler=file_handler,
                field_extractor=field_extractor
            )
            
            extract_result = await extraction_service.extract_invoice(
                invoice_id=ingest_result['invoice_id'],
                file_identifier=ingest_result['file_path'],
                file_name=file_name,
                upload_date=ingest_result['upload_date']
            )
            
            logger.info(f"Extraction status: {extract_result['status']}")
            if extract_result['status'] == 'extracted':
                invoice = await DatabaseService.get_invoice(
                    ingest_result['invoice_id'],
                    db=db_session
                )
                if invoice:
                    logger.info(f"  Invoice Number: {invoice.invoice_number}")
                    logger.info(f"  Vendor: {invoice.vendor_name}")
                    logger.info(f"  Total Amount: {invoice.total_amount} {invoice.currency}")
                    logger.info(f"  Line Items: {len(invoice.line_items)}")
                    logger.info(f"  Confidence: {invoice.extraction_confidence:.2%}")
            else:
                logger.error(f"  Errors: {extract_result.get('errors', [])}")
        else:
            logger.warning("Azure Document Intelligence not configured - skipping extraction test")
        
        logger.info(f"\nSuccessfully processed: {blob_name}\n")
        
    except Exception as e:
        logger.error(f"Error processing file {blob_name}: {e}", exc_info=True)


async def main():
    """Main test function"""
    container_name = settings.AZURE_STORAGE_CONTAINER_RAW
    
    logger.info("="*70)
    logger.info("Azure Blob Storage File Processing Test")
    logger.info("="*70)
    logger.info(f"Container: {container_name}")
    logger.info(f"Storage Account: {settings.AZURE_STORAGE_ACCOUNT_NAME}")
    logger.info("")
    
    # Create database tables
    logger.info("Creating database tables...")
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    logger.info("Database tables created.\n")
    
    # List files
    files = list_azure_files(container_name, max_files=5)
    
    if not files:
        logger.error("No PDF files found in container")
        return
    
    logger.info(f"\nFound {len(files)} PDF file(s). Testing first file...\n")
    
    # Test first file
    if files:
        await test_file_processing(files[0], container_name)
    
    logger.info("="*70)
    logger.info("Test completed")
    logger.info("="*70)


if __name__ == "__main__":
    asyncio.run(main())

