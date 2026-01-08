"""End-to-end integration tests"""

import pytest
from datetime import datetime
from decimal import Decimal

from src.ingestion.ingestion_service import IngestionService
from src.extraction.extraction_service import ExtractionService
from src.services.db_service import DatabaseService
from src.models.invoice import Invoice, LineItem


@pytest.mark.integration
@pytest.mark.slow
class TestEndToEndWorkflow:
    """Test complete workflow from ingestion to extraction"""
    
    @pytest.mark.asyncio
    async def test_complete_workflow(
        self,
        db_session,
        sample_pdf_content,
        mock_file_handler,
        mock_pdf_processor,
        mock_document_intelligence_client
    ):
        """Test complete workflow: ingest -> extract -> save"""
        # Step 1: Ingest invoice
        ingestion_service = IngestionService(
            file_handler=mock_file_handler,
            pdf_processor=mock_pdf_processor
        )
        
        ingest_result = await ingestion_service.ingest_invoice(
            file_content=sample_pdf_content,
            file_name="test_invoice.pdf",
            db=db_session,
        )
        
        assert ingest_result["status"] == "uploaded"
        invoice_id = ingest_result["invoice_id"]
        
        # Step 2: Extract invoice
        # Mock field extractor
        from unittest.mock import MagicMock
        mock_field_extractor = MagicMock()
        mock_field_extractor.extract_invoice.return_value = Invoice(
            id=invoice_id,
            file_path=ingest_result["file_path"],
            file_name="test_invoice.pdf",
            upload_date=datetime.utcnow(),
            status="extracted",
            invoice_number="INV-12345",
            total_amount=Decimal("1500.00"),
            currency="CAD",
            line_items=[],
            extraction_confidence=0.85
        )
        
        extraction_service = ExtractionService(
            doc_intelligence_client=mock_document_intelligence_client,
            file_handler=mock_file_handler,
            field_extractor=mock_field_extractor
        )
        
        extract_result = await extraction_service.extract_invoice(
            invoice_id=invoice_id,
            file_identifier=ingest_result["file_path"],
            file_name="test_invoice.pdf",
            upload_date=datetime.utcnow(),
            db=db_session,
        )
        
        assert extract_result["status"] == "extracted"
        
        # Step 3: Verify invoice in database
        invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
        assert invoice is not None
        assert invoice.status == "extracted"
        assert invoice.invoice_number == "INV-12345"

