"""Simplified API routes for invoice ingestion"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import List, Optional
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

from src.ingestion.ingestion_service import IngestionService
from src.ingestion.file_handler import FileHandler
from src.ingestion.pdf_processor import PDFProcessor
from src.ingestion.azure_blob_utils import AzureBlobBrowser
from src.models.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


def get_ingestion_service() -> IngestionService:
    """Dependency to get ingestion service instance"""
    file_handler = FileHandler()
    pdf_processor = PDFProcessor()
    return IngestionService(
        file_handler=file_handler,
        pdf_processor=pdf_processor
    )


def get_blob_browser() -> AzureBlobBrowser:
    """Dependency to get Azure blob browser"""
    return AzureBlobBrowser()


@router.post("/ingestion/upload")
async def upload_invoice(
    file: UploadFile = File(...),
    ingestion_service: IngestionService = Depends(get_ingestion_service)
):
    """
    Upload a single invoice PDF
    
    Args:
        file: PDF file to upload
        
    Returns:
        Ingestion result with invoice ID and status
    """
    try:
        # Read file content
        file_content = await file.read()
        
        if not file_content:
            raise HTTPException(status_code=400, detail="File is empty")
        
        # Ingest invoice
        result = await ingestion_service.ingest_invoice(
            file_content=file_content,
            file_name=file.filename or "unknown.pdf"
        )
        
        # Check for errors
        if result["status"] == "validation_failed":
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "File validation failed",
                    "errors": result.get("errors", [])
                }
            )
        
        if result["status"] == "error":
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "Ingestion error",
                    "errors": result.get("errors", [])
                }
            )
        
        return JSONResponse(
            status_code=201,
            content={
                "message": "Invoice uploaded successfully",
                "invoice_id": result["invoice_id"],
                "status": result["status"],
                "file_name": result["file_name"],
                "file_path": result["file_path"],
                "file_size": result["file_size"],
                "page_count": result["page_count"],
                "upload_date": result["upload_date"].isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading invoice: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/ingestion/batch-upload")
async def batch_upload_invoices(
    files: List[UploadFile] = File(...),
    ingestion_service: IngestionService = Depends(get_ingestion_service)
):
    """
    Upload multiple invoice PDFs
    
    Args:
        files: List of PDF files to upload
        
    Returns:
        Batch ingestion results
    """
    results = []
    errors = []
    
    for file in files:
        try:
            file_content = await file.read()
            result = await ingestion_service.ingest_invoice(
                file_content=file_content,
                file_name=file.filename or "unknown.pdf"
            )
            results.append({
                "file_name": file.filename,
                "invoice_id": result.get("invoice_id"),
                "status": result["status"],
                "errors": result.get("errors", [])
            })
        except Exception as e:
            errors.append({
                "file_name": file.filename,
                "error": str(e)
            })
    
    return JSONResponse(
        status_code=200,
        content={
            "message": f"Processed {len(files)} files",
            "successful": len(results),
            "failed": len(errors),
            "results": results,
            "errors": errors
        }
    )


@router.get("/ingestion/blobs")
async def list_blobs(
    container: str,
    prefix: Optional[str] = None,
    blob_browser: AzureBlobBrowser = Depends(get_blob_browser),
):
    """List blobs in a container (optionally filtered by prefix)."""
    try:
        blobs = blob_browser.list_blobs(container_name=container, prefix=prefix)
        return JSONResponse(status_code=200, content={"container": container, "prefix": prefix, "blobs": blobs})
    except Exception as e:
        logger.error(f"Error listing blobs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list blobs: {e}")


@router.post("/ingestion/extract-blob")
async def extract_blob(
    container: str,
    blob_name: str,
    ingestion_service: IngestionService = Depends(get_ingestion_service),
    blob_browser: AzureBlobBrowser = Depends(get_blob_browser),
):
    """Download a blob from storage and ingest it like an uploaded PDF."""
    try:
        content = blob_browser.download_blob(container_name=container, blob_name=blob_name)
        if not content:
            raise HTTPException(status_code=400, detail="Blob is empty or could not be downloaded")

        filename = Path(blob_name).name or "invoice.pdf"
        result = await ingestion_service.ingest_invoice(file_content=content, file_name=filename)

        if result["status"] in ("validation_failed", "error"):
            raise HTTPException(
                status_code=400,
                detail={
                    "message": "Ingestion error",
                    "errors": result.get("errors", [])
                }
            )

        return JSONResponse(
            status_code=201,
            content={
                "message": "Blob ingested successfully",
                "invoice_id": result["invoice_id"],
                "status": result["status"],
                "file_name": result["file_name"],
                "file_path": result["file_path"],
                "file_size": result["file_size"],
                "page_count": result["page_count"],
                "upload_date": result["upload_date"].isoformat() if result.get("upload_date") else None,
                "container": container,
                "blob_name": blob_name,
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting blob '{blob_name}' from '{container}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.get("/health/db")
@router.get("/ingestion/health/db")
async def db_healthcheck(db: AsyncSession = Depends(get_db)):
    """Simple DB connectivity check."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"DB healthcheck failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"database unreachable: {e}")

