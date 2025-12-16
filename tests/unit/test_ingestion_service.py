"""Unit tests for IngestionService"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from src.ingestion.ingestion_service import IngestionService
from src.ingestion.file_handler import FileHandler
from src.ingestion.pdf_processor import PDFProcessor


@pytest.mark.unit
class TestIngestionService:
    """Test IngestionService"""
    
    @pytest.mark.asyncio
    async def test_ingest_invoice_success(
        self,
        sample_pdf_content,
        mock_file_handler,
        mock_pdf_processor
    ):
        """Test successful invoice ingestion"""
        service = IngestionService(
            file_handler=mock_file_handler,
            pdf_processor=mock_pdf_processor
        )
        
        result = await service.ingest_invoice(
            file_content=sample_pdf_content,
            file_name="test_invoice.pdf"
        )
        
        assert result["status"] == "uploaded"
        assert "invoice_id" in result
        assert result["file_name"] == "test_invoice.pdf"
        assert result["file_size"] > 0
        assert result["page_count"] == 1
        assert len(result["errors"]) == 0
        
        # Verify file handler was called
        mock_file_handler.upload_file.assert_called_once()
        mock_pdf_processor.validate_file.assert_called_once()
        mock_pdf_processor.get_pdf_info.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ingest_invoice_validation_failed(
        self,
        sample_pdf_content,
        mock_file_handler,
        mock_pdf_processor
    ):
        """Test invoice ingestion with validation failure"""
        mock_pdf_processor.validate_file.return_value = (False, "Invalid PDF format")
        
        service = IngestionService(
            file_handler=mock_file_handler,
            pdf_processor=mock_pdf_processor
        )
        
        result = await service.ingest_invoice(
            file_content=sample_pdf_content,
            file_name="test_invoice.pdf"
        )
        
        assert result["status"] == "validation_failed"
        assert len(result["errors"]) > 0
        assert "Invalid PDF format" in result["errors"][0]
        
        # Verify file was not uploaded
        mock_file_handler.upload_file.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_ingest_invoice_empty_file(
        self,
        mock_file_handler,
        mock_pdf_processor
    ):
        """Test invoice ingestion with empty file"""
        mock_pdf_processor.validate_file.return_value = (False, "File is empty")
        
        service = IngestionService(
            file_handler=mock_file_handler,
            pdf_processor=mock_pdf_processor
        )
        
        result = await service.ingest_invoice(
            file_content=b"",
            file_name="empty.pdf"
        )
        
        assert result["status"] == "validation_failed"
        assert len(result["errors"]) > 0

