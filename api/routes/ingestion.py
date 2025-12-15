"""Simplified API routes for invoice ingestion"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import List
import logging

from src.ingestion.ingestion_service import IngestionService
from src.ingestion.file_handler import FileHandler
from src.ingestion.pdf_processor import PDFProcessor

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

