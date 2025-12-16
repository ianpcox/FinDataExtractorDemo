"""API routes for importing invoices from Azure Blob Storage"""

from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from typing import Optional, List
import logging

from src.ingestion.azure_blob_utils import AzureBlobBrowser
from src.ingestion.ingestion_service import IngestionService
from src.ingestion.file_handler import FileHandler
from src.ingestion.pdf_processor import PDFProcessor
from src.extraction.extraction_service import ExtractionService
from src.extraction.document_intelligence_client import DocumentIntelligenceClient
from src.extraction.field_extractor import FieldExtractor
from src.services.db_service import DatabaseService
from src.models.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/azure-import", tags=["azure-import"])


@router.get("/list-containers")
async def list_containers():
    """List all containers in Azure Storage"""
    try:
        browser = AzureBlobBrowser()
        containers = browser.list_containers()
        return JSONResponse(
            status_code=200,
            content={"containers": containers}
        )
    except Exception as e:
        logger.error(f"Error listing containers: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error listing containers: {str(e)}"
        )


@router.get("/list-blobs")
async def list_blobs(
    container_name: str = Query(..., description="Container name"),
    prefix: Optional[str] = Query(None, description="Path prefix (e.g., 'RAW Basic/' or 'Raw_Basic/')"),
    file_extension: Optional[str] = Query(None, description="Filter by file extension (e.g., 'pdf')")
):
    """
    List blobs in a container, optionally filtered by path prefix
    
    Examples:
    - List all PDFs in container: /api/azure-import/list-blobs?container_name=invoices-raw&file_extension=pdf
    - List files in specific path: /api/azure-import/list-blobs?container_name=invoices-raw&prefix=RAW Basic/
    """
    try:
        browser = AzureBlobBrowser()
        blobs = browser.list_blobs(container_name=container_name, prefix=prefix)
        
        # Filter by extension if provided
        if file_extension:
            blobs = [
                blob for blob in blobs
                if blob["name"].lower().endswith(f".{file_extension.lower()}")
            ]
        
        return JSONResponse(
            status_code=200,
            content={
                "container": container_name,
                "prefix": prefix,
                "count": len(blobs),
                "blobs": blobs
            }
        )
    except Exception as e:
        logger.error(f"Error listing blobs: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error listing blobs: {str(e)}"
        )


@router.post("/process-blob")
async def process_blob(
    container_name: str = Query(..., description="Container name"),
    blob_name: str = Query(..., description="Blob name/path"),
    run_extraction: bool = Query(True, description="Run extraction after ingestion"),
    db: AsyncSession = Depends(get_db)
):
    """
    Download a blob from Azure Storage and run it through the end-to-end workflow
    
    Args:
        container_name: Container name
        blob_name: Blob name/path (e.g., "RAW Basic/invoice.pdf")
        run_extraction: Whether to run extraction after ingestion
        
    Returns:
        Processing result with invoice_id and status
    """
    try:
        # Step 1: Download blob from Azure
        browser = AzureBlobBrowser()
        logger.info(f"Downloading blob '{blob_name}' from container '{container_name}'")
        file_content = browser.download_blob(container_name, blob_name)
        
        # Extract file name from blob path
        file_name = blob_name.split("/")[-1] if "/" in blob_name else blob_name
        
        # Step 2: Ingest invoice
        ingestion_service = IngestionService(
            file_handler=FileHandler(use_azure=True),
            pdf_processor=PDFProcessor()
        )
        
        ingest_result = await ingestion_service.ingest_invoice(
            file_content=file_content,
            file_name=file_name
        )
        
        if ingest_result["status"] != "uploaded":
            return JSONResponse(
                status_code=400,
                content={
                    "status": "ingestion_failed",
                    "message": "Invoice ingestion failed",
                    "errors": ingest_result.get("errors", []),
                    "invoice_id": ingest_result.get("invoice_id")
                }
            )
        
        invoice_id = ingest_result["invoice_id"]
        file_path = ingest_result["file_path"]
        
        # Step 3: Extract invoice (if requested)
        extraction_result = None
        if run_extraction:
            extraction_service = ExtractionService(
                doc_intelligence_client=DocumentIntelligenceClient(),
                file_handler=FileHandler(use_azure=True),
                field_extractor=FieldExtractor()
            )
            
            extraction_result = await extraction_service.extract_invoice(
                invoice_id=invoice_id,
                file_identifier=file_path,
                file_name=file_name,
                upload_date=ingest_result["upload_date"]
            )
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Blob processed successfully",
                "invoice_id": invoice_id,
                "ingestion": {
                    "status": ingest_result["status"],
                    "file_name": file_name,
                    "file_size": ingest_result["file_size"],
                    "page_count": ingest_result["page_count"]
                },
                "extraction": extraction_result if extraction_result else None
            }
        )
        
    except Exception as e:
        logger.error(f"Error processing blob: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing blob: {str(e)}"
        )


@router.post("/process-batch")
async def process_batch(
    container_name: str = Query(..., description="Container name"),
    prefix: Optional[str] = Query(None, description="Path prefix to filter"),
    file_extension: Optional[str] = Query("pdf", description="File extension filter"),
    max_files: int = Query(10, description="Maximum number of files to process"),
    run_extraction: bool = Query(True, description="Run extraction after ingestion"),
    db: AsyncSession = Depends(get_db)
):
    """
    Process multiple blobs from Azure Storage
    
    Args:
        container_name: Container name
        prefix: Path prefix (e.g., "RAW Basic/")
        file_extension: File extension to filter (default: "pdf")
        max_files: Maximum number of files to process
        run_extraction: Whether to run extraction after ingestion
        
    Returns:
        Batch processing results
    """
    try:
        # List blobs
        browser = AzureBlobBrowser()
        blobs = browser.list_blobs(
            container_name=container_name,
            prefix=prefix
        )
        
        # Filter by extension
        if file_extension:
            blobs = [
                blob for blob in blobs
                if blob["name"].lower().endswith(f".{file_extension.lower()}")
            ]
        
        # Limit number of files
        blobs = blobs[:max_files]
        
        results = []
        errors = []
        
        for blob in blobs:
            try:
                # Process each blob
                file_content = browser.download_blob(container_name, blob["name"])
                file_name = blob["name"].split("/")[-1]
                
                # Ingest
                ingestion_service = IngestionService(
                    file_handler=FileHandler(use_azure=True),
                    pdf_processor=PDFProcessor()
                )
                
                ingest_result = await ingestion_service.ingest_invoice(
                    file_content=file_content,
                    file_name=file_name
                )
                
                if ingest_result["status"] == "uploaded":
                    invoice_id = ingest_result["invoice_id"]
                    
                    # Extract if requested
                    if run_extraction:
                        extraction_service = ExtractionService(
                            doc_intelligence_client=DocumentIntelligenceClient(),
                            file_handler=FileHandler(use_azure=True),
                            field_extractor=FieldExtractor()
                        )
                        
                        await extraction_service.extract_invoice(
                            invoice_id=invoice_id,
                            file_identifier=ingest_result["file_path"],
                            file_name=file_name,
                            upload_date=ingest_result["upload_date"]
                        )
                    
                    results.append({
                        "blob_name": blob["name"],
                        "invoice_id": invoice_id,
                        "status": "success"
                    })
                else:
                    errors.append({
                        "blob_name": blob["name"],
                        "error": "Ingestion failed",
                        "details": ingest_result.get("errors", [])
                    })
                    
            except Exception as e:
                errors.append({
                    "blob_name": blob["name"],
                    "error": str(e)
                })
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "completed",
                "total": len(blobs),
                "successful": len(results),
                "failed": len(errors),
                "results": results,
                "errors": errors
            }
        )
        
    except Exception as e:
        logger.error(f"Error processing batch: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing batch: {str(e)}"
        )

