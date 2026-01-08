"""Unit tests for ExtractionService"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from datetime import datetime
import json
from decimal import Decimal

from src.extraction.extraction_service import ExtractionService
from src.extraction.document_intelligence_client import DocumentIntelligenceClient
from src.extraction.field_extractor import FieldExtractor
from src.ingestion.file_handler import FileHandler


@pytest.mark.unit
class TestExtractionService:
    """Test ExtractionService"""
    
    @pytest.mark.asyncio
    async def test_extract_invoice_success(
        self,
        mock_document_intelligence_client,
        mock_file_handler,
        sample_invoice
    ):
        """Test successful invoice extraction"""
        # Mock field extractor
        mock_field_extractor = MagicMock()
        mock_field_extractor.extract_invoice.return_value = sample_invoice
        
        service = ExtractionService(
            doc_intelligence_client=mock_document_intelligence_client,
            file_handler=mock_file_handler,
            field_extractor=mock_field_extractor
        )
        
        # Mock database service
        with patch('src.extraction.extraction_service.DatabaseService') as mock_db:
            mock_db.save_invoice = AsyncMock()
            
            result = await service.extract_invoice(
                invoice_id="test-invoice-123",
                file_identifier="test/path/invoice.pdf",
                file_name="test_invoice.pdf",
                upload_date=datetime.utcnow()
            )
        
        assert result["status"] == "extracted"
        assert result["invoice_id"] == "test-invoice-123"
        assert "confidence" in result
        assert "field_confidence" in result
        assert len(result["errors"]) == 0
        
        # Verify Document Intelligence was called
        mock_document_intelligence_client.analyze_invoice.assert_called_once()
        mock_file_handler.download_file.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_extract_invoice_file_not_found(
        self,
        mock_document_intelligence_client,
        mock_file_handler
    ):
        """Test extraction when file is not found"""
        mock_file_handler.download_file.return_value = None
        
        service = ExtractionService(
            doc_intelligence_client=mock_document_intelligence_client,
            file_handler=mock_file_handler
        )
        
        result = await service.extract_invoice(
            invoice_id="test-invoice-123",
            file_identifier="nonexistent.pdf",
            file_name="nonexistent.pdf",
            upload_date=datetime.utcnow()
        )
        
        assert result["status"] == "error"
        assert len(result["errors"]) > 0
        assert "Failed to download file" in result["errors"][0]
    
    @pytest.mark.asyncio
    async def test_extract_invoice_document_intelligence_failed(
        self,
        mock_document_intelligence_client,
        mock_file_handler
    ):
        """Test extraction when Document Intelligence fails"""
        mock_document_intelligence_client.analyze_invoice.return_value = {
            "error": "Document Intelligence API error"
        }
        
        service = ExtractionService(
            doc_intelligence_client=mock_document_intelligence_client,
            file_handler=mock_file_handler
        )
        
        result = await service.extract_invoice(
            invoice_id="test-invoice-123",
            file_identifier="test/path/invoice.pdf",
            file_name="test_invoice.pdf",
            upload_date=datetime.utcnow()
        )
        
        assert result["status"] == "extraction_failed"
        assert len(result["errors"]) > 0

    def test_build_llm_prompt_sanitizes_payload(self, sample_document_intelligence_data):
        service = ExtractionService(
            doc_intelligence_client=MagicMock(),
            file_handler=MagicMock(),
            field_extractor=MagicMock()
        )
        prompt = service._build_llm_prompt(sample_document_intelligence_data, ["payment_term", "vendor_address"])
        assert prompt is not None
        assert "Low-confidence fields" in prompt
        assert "payment_term" in prompt

    def test_apply_llm_suggestions_sets_fields_and_confidence(self, sample_invoice):
        service = ExtractionService(
            doc_intelligence_client=MagicMock(),
            file_handler=MagicMock(),
            field_extractor=MagicMock()
        )
        # ensure field_confidence exists
        sample_invoice.field_confidence = sample_invoice.field_confidence or {}
        suggestion = json.dumps({
            "payment_term": "Net 45",
            "vendor_name": "Updated Vendor"
        })

        service._apply_llm_suggestions(sample_invoice, suggestion, ["payment_term", "vendor_name"])

        assert getattr(sample_invoice, "payment_terms") == "Net 45"
        assert sample_invoice.vendor_name == "Updated Vendor"
        assert sample_invoice.field_confidence["payment_terms"] == 0.9
        assert sample_invoice.field_confidence["vendor_name"] == 0.9

    def test_run_low_confidence_fallback_no_llm(self, sample_invoice):
        service = ExtractionService(
            doc_intelligence_client=MagicMock(),
            file_handler=MagicMock(),
            field_extractor=MagicMock()
        )
        # With USE_LLM_FALLBACK default False, this should no-op without error
        service._run_low_confidence_fallback(sample_invoice, ["vendor_name"], {"vendor_name": "x"})

