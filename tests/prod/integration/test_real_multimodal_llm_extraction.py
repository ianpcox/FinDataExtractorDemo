"""
Integration tests for REAL Azure OpenAI Multimodal LLM extraction.

These tests make actual API calls to Azure OpenAI multimodal LLM and write results to isolated test databases.
They verify that the multimodal LLM can actually extract and correct invoice fields from scanned PDFs.

Requirements:
- Azure OpenAI credentials must be configured (AOAI_ENDPOINT, AOAI_API_KEY, AOAI_DEPLOYMENT_NAME or AOAI_MULTIMODAL_DEPLOYMENT_NAME)
- Tests will be skipped if credentials are not available
- Each test uses an isolated test database (no conflicts)
- Uploaded files are automatically cleaned up after each test
- Multimodal LLM fallback must be enabled (USE_MULTIMODAL_LLM_FALLBACK=True)
"""

import pytest
import os
import time
from datetime import datetime
from decimal import Decimal
from uuid import uuid4
from pathlib import Path

from src.extraction.extraction_service import ExtractionService
from src.extraction.document_intelligence_client import DocumentIntelligenceClient
from src.extraction.field_extractor import FieldExtractor
from src.ingestion.file_handler import FileHandler
from src.models.invoice import Invoice, InvoiceState
from src.services.db_service import DatabaseService
from src.config import settings


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
class TestRealMultimodalLLMExtraction:
    """Integration tests for real Azure OpenAI Multimodal LLM extraction"""
    
    @pytest.fixture
    def extraction_service(self, monkeypatch):
        """Create extraction service with real DI and Multimodal LLM clients"""
        # Check if Azure OpenAI is configured
        if not settings.AOAI_ENDPOINT or not settings.AOAI_API_KEY:
            pytest.skip("Azure OpenAI credentials not configured - skipping multimodal LLM tests")
        
        # Check for multimodal deployment (can use regular deployment if multimodal not specified)
        multimodal_deployment = settings.AOAI_MULTIMODAL_DEPLOYMENT_NAME or settings.AOAI_DEPLOYMENT_NAME
        if not multimodal_deployment:
            pytest.skip("Azure OpenAI deployment not configured - skipping multimodal LLM tests")
        
        # Check if Azure Document Intelligence is configured
        if not settings.AZURE_FORM_RECOGNIZER_ENDPOINT or not settings.AZURE_FORM_RECOGNIZER_KEY:
            pytest.skip("Azure Document Intelligence credentials not configured - skipping multimodal LLM tests")
        
        # Override the autouse fixture that disables LLM fallback
        # We need both LLM fallback and multimodal LLM fallback enabled for these tests
        monkeypatch.setattr(settings, "USE_LLM_FALLBACK", True, raising=False)
        monkeypatch.setattr(settings, "USE_MULTIMODAL_LLM_FALLBACK", True, raising=False)
        
        # Create real clients
        di_client = DocumentIntelligenceClient(
            endpoint=settings.AZURE_FORM_RECOGNIZER_ENDPOINT,
            api_key=settings.AZURE_FORM_RECOGNIZER_KEY
        )
        
        file_handler = FileHandler()
        field_extractor = FieldExtractor()
        
        service = ExtractionService(
            doc_intelligence_client=di_client,
            file_handler=file_handler,
            field_extractor=field_extractor
        )
        
        # Verify multimodal config is available
        if not service._has_multimodal_config():
            pytest.skip("Multimodal LLM configuration not available - skipping multimodal LLM tests")
        
        return service
    
    @pytest.fixture
    def sample_pdf_path(self):
        """Get path to sample PDF for testing"""
        # Use the sample invoice from the data folder
        sample_path = "data/sample_invoices/Raw/Raw_Basic/ACC012 4202092525.pdf"
        if not os.path.exists(sample_path):
            pytest.skip(f"Sample PDF not found at {sample_path}")
        return sample_path
    
    @pytest.fixture
    def unique_invoice_id(self):
        """Generate a unique invoice ID for each test to avoid conflicts"""
        # Use timestamp + uuid for maximum uniqueness
        timestamp = int(time.time() * 1000)  # milliseconds
        unique_id = f"test-multimodal-{timestamp}-{uuid4().hex[:8]}"
        return unique_id
    
    @pytest.fixture
    def cleanup_uploaded_file(self):
        """Fixture to track and cleanup uploaded files after tests"""
        uploaded_files = []
        
        yield uploaded_files
        
        # Cleanup: Remove uploaded files
        file_handler = FileHandler()
        for file_path in uploaded_files:
            try:
                if isinstance(file_path, str):
                    path = Path(file_path)
                    if path.exists() and path.is_file():
                        path.unlink()
                        print(f"Cleaned up uploaded file: {file_path}")
            except Exception as e:
                # Log but don't fail test on cleanup errors
                print(f"Warning: Failed to cleanup file {file_path}: {e}")
    
    async def test_real_multimodal_llm_extracts_invoice_number(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that real multimodal LLM can extract invoice_number from a scanned PDF.
        Verifies that multimodal LLM is actually used (not text-based).
        """
        invoice_id = unique_invoice_id
        
        # Read PDF file
        with open(sample_pdf_path, "rb") as f:
            file_content = f.read()
        
        # Verify PDF is detected as scanned (required for multimodal)
        from starlette.concurrency import run_in_threadpool
        is_scanned = await run_in_threadpool(
            extraction_service._is_scanned_pdf,
            file_content
        )
        
        # If PDF is not scanned, we can't test multimodal LLM properly
        # But we can still test that the system handles it correctly
        if not is_scanned:
            pytest.skip(f"PDF is not detected as scanned (text-based PDF). "
                       f"Multimodal LLM tests require scanned PDFs. "
                       f"To test multimodal, use a scanned/image-based PDF.")
        
        # Upload file
        file_handler = FileHandler()
        upload_result = file_handler.upload_file(
            file_content=file_content,
            file_name=os.path.basename(sample_pdf_path)
        )
        file_path = upload_result.get("file_path")
        if not file_path:
            pytest.skip("File upload failed")
        
        # Track file for cleanup
        cleanup_uploaded_file.append(file_path)
        
        # Verify image rendering works (multimodal requirement)
        images = await run_in_threadpool(
            extraction_service._render_multimodal_images,
            file_content
        )
        assert len(images) > 0, \
            "Multimodal LLM requires rendered images - image rendering failed"
        assert all(isinstance(img, str) for img in images), \
            "Rendered images should be base64-encoded strings"
        
        # Create invoice with low confidence for invoice_number to trigger LLM
        invoice = Invoice(
            id=invoice_id,
            file_path=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            processing_state=InvoiceState.PENDING,
            field_confidence={"invoice_number": 0.3}  # Low confidence to trigger LLM
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        
        # Run extraction (should use multimodal LLM since PDF is scanned)
        result = await extraction_service.extract_invoice(
            invoice_id=invoice_id,
            file_identifier=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            db=db_session
        )
        
        # Verify extraction succeeded
        assert result["status"] == "extracted", \
            f"Extraction failed: {result.get('errors', [])}"
        
        # Verify invoice was extracted
        extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
        assert extracted_invoice is not None
        
        # Verify invoice_number was extracted (should be "4202092525" from the sample PDF)
        assert extracted_invoice.invoice_number is not None, \
            "Invoice number should be extracted by multimodal LLM"
        assert len(extracted_invoice.invoice_number) > 0, \
            "Invoice number should not be empty"
        
        # Verify confidence was updated
        if extracted_invoice.field_confidence:
            invoice_number_conf = extracted_invoice.field_confidence.get("invoice_number")
            assert invoice_number_conf is not None, \
                "Invoice number confidence should be set"
            assert invoice_number_conf >= 0.7, \
                f"Invoice number confidence should be >= 0.7, got {invoice_number_conf}"
    
    async def test_real_multimodal_llm_extracts_multiple_fields(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that real multimodal LLM can extract multiple fields from a scanned PDF.
        Verifies multimodal LLM processes multiple field groups with images.
        """
        invoice_id = unique_invoice_id
        
        # Read PDF file
        with open(sample_pdf_path, "rb") as f:
            file_content = f.read()
        
        # Verify PDF is scanned
        from starlette.concurrency import run_in_threadpool
        is_scanned = await run_in_threadpool(
            extraction_service._is_scanned_pdf,
            file_content
        )
        if not is_scanned:
            pytest.skip("PDF is not detected as scanned - multimodal LLM tests require scanned PDFs")
        
        # Verify image rendering works
        images = await run_in_threadpool(
            extraction_service._render_multimodal_images,
            file_content
        )
        assert len(images) > 0, "Multimodal LLM requires rendered images"
        
        # Upload file
        file_handler = FileHandler()
        upload_result = file_handler.upload_file(
            file_content=file_content,
            file_name=os.path.basename(sample_pdf_path)
        )
        file_path = upload_result.get("file_path")
        if not file_path:
            pytest.skip("File upload failed")
        
        cleanup_uploaded_file.append(file_path)
        
        # Create invoice with multiple low-confidence fields
        invoice = Invoice(
            id=invoice_id,
            file_path=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            processing_state=InvoiceState.PENDING,
            field_confidence={
                "invoice_number": 0.3,
                "invoice_date": 0.3,
                "vendor_name": 0.3,
                "total_amount": 0.3,
            }
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        
        # Run extraction (should use multimodal LLM)
        result = await extraction_service.extract_invoice(
            invoice_id=invoice_id,
            file_identifier=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            db=db_session
        )
        
        # Verify extraction succeeded
        assert result["status"] == "extracted", \
            f"Extraction failed: {result.get('errors', [])}"
        
        # Verify invoice was extracted
        extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
        assert extracted_invoice is not None
        
        # Verify multiple fields were extracted
        extracted_count = 0
        if extracted_invoice.invoice_number:
            extracted_count += 1
        if extracted_invoice.invoice_date:
            extracted_count += 1
        if extracted_invoice.vendor_name:
            extracted_count += 1
        if extracted_invoice.total_amount:
            extracted_count += 1
        
        assert extracted_count >= 2, \
            f"Expected at least 2 fields to be extracted by multimodal LLM, got {extracted_count}"
    
    async def test_real_multimodal_llm_corrects_wrong_values(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that real multimodal LLM can correct wrong field values from a scanned PDF.
        """
        invoice_id = unique_invoice_id
        
        # Read PDF file
        with open(sample_pdf_path, "rb") as f:
            file_content = f.read()
        
        # Upload file
        file_handler = FileHandler()
        upload_result = file_handler.upload_file(
            file_content=file_content,
            file_name=os.path.basename(sample_pdf_path)
        )
        file_path = upload_result.get("file_path")
        if not file_path:
            pytest.skip("File upload failed")
        
        cleanup_uploaded_file.append(file_path)
        
        # Create invoice with wrong values and low confidence
        invoice = Invoice(
            id=invoice_id,
            file_path=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            processing_state=InvoiceState.PENDING,
            invoice_number="WRONG-INVOICE-NUMBER",  # Wrong value
            invoice_date=datetime(2099, 12, 31).date(),  # Wrong future date
            field_confidence={
                "invoice_number": 0.3,  # Low confidence
                "invoice_date": 0.3,  # Low confidence
            }
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        
        # Run extraction
        result = await extraction_service.extract_invoice(
            invoice_id=invoice_id,
            file_identifier=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            db=db_session
        )
        
        # Verify extraction succeeded
        assert result["status"] == "extracted", \
            f"Extraction failed: {result.get('errors', [])}"
        
        # Verify invoice was extracted
        updated_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
        assert updated_invoice is not None
        
        # Verify wrong values were corrected
        # Invoice number should be corrected (not "WRONG-INVOICE-NUMBER")
        if updated_invoice.invoice_number:
            assert updated_invoice.invoice_number != "WRONG-INVOICE-NUMBER", \
                "Invoice number should be corrected by multimodal LLM"
        
        # Invoice date should be corrected (not future date)
        if updated_invoice.invoice_date:
            assert updated_invoice.invoice_date < datetime(2026, 1, 1).date(), \
                "Invoice date should be corrected (not a future date)"
    
    async def test_real_multimodal_llm_improves_low_confidence_fields(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that real multimodal LLM improves low-confidence fields from a scanned PDF.
        """
        invoice_id = unique_invoice_id
        
        # Read PDF file
        with open(sample_pdf_path, "rb") as f:
            file_content = f.read()
        
        # Upload file
        file_handler = FileHandler()
        upload_result = file_handler.upload_file(
            file_content=file_content,
            file_name=os.path.basename(sample_pdf_path)
        )
        file_path = upload_result.get("file_path")
        if not file_path:
            pytest.skip("File upload failed")
        
        cleanup_uploaded_file.append(file_path)
        
        # Create invoice with low-confidence fields
        invoice = Invoice(
            id=invoice_id,
            file_path=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            processing_state=InvoiceState.PENDING,
            field_confidence={
                "invoice_number": 0.5,  # Below threshold
                "vendor_name": 0.6,  # Below threshold
                "total_amount": 0.4,  # Below threshold
            }
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        
        # Store original confidence scores
        original_confidences = invoice.field_confidence.copy()
        
        # Run extraction
        result = await extraction_service.extract_invoice(
            invoice_id=invoice_id,
            file_identifier=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            db=db_session
        )
        
        # Verify extraction succeeded
        assert result["status"] == "extracted", \
            f"Extraction failed: {result.get('errors', [])}"
        
        # Verify invoice was extracted
        updated_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
        assert updated_invoice is not None
        
        # Verify confidence scores were improved
        if updated_invoice.field_confidence:
            for field_name in ["invoice_number", "vendor_name", "total_amount"]:
                original_conf = original_confidences.get(field_name)
                updated_conf = updated_invoice.field_confidence.get(field_name)
                
                if original_conf is not None and updated_conf is not None:
                    assert updated_conf >= original_conf, \
                        f"Confidence for {field_name} should improve or stay same: " \
                        f"{original_conf} -> {updated_conf}"
    
    async def test_real_multimodal_llm_confidence_calculation_accuracy(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that confidence scores are calculated accurately for multimodal LLM corrections.
        """
        invoice_id = unique_invoice_id
        
        # Read PDF file
        with open(sample_pdf_path, "rb") as f:
            file_content = f.read()
        
        # Upload file
        file_handler = FileHandler()
        upload_result = file_handler.upload_file(
            file_content=file_content,
            file_name=os.path.basename(sample_pdf_path)
        )
        file_path = upload_result.get("file_path")
        if not file_path:
            pytest.skip("File upload failed")
        
        cleanup_uploaded_file.append(file_path)
        
        # Create invoice with blank field (should get high confidence when filled)
        invoice = Invoice(
            id=invoice_id,
            file_path=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            processing_state=InvoiceState.PENDING,
            invoice_number=None,  # Blank field
            field_confidence={"invoice_number": None}  # No confidence
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        
        # Run extraction
        result = await extraction_service.extract_invoice(
            invoice_id=invoice_id,
            file_identifier=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            db=db_session
        )
        
        # Verify extraction succeeded
        assert result["status"] == "extracted", \
            f"Extraction failed: {result.get('errors', [])}"
        
        # Verify invoice was extracted
        updated_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
        assert updated_invoice is not None
        
        # If invoice_number was filled from blank, confidence should be high (0.85-0.95)
        if updated_invoice.invoice_number and updated_invoice.field_confidence:
            invoice_number_conf = updated_invoice.field_confidence.get("invoice_number")
            if invoice_number_conf is not None:
                assert invoice_number_conf >= 0.85, \
                    f"Confidence for filled blank field should be >= 0.85, got {invoice_number_conf}"
    
    async def test_real_multimodal_llm_corrects_multiple_field_types(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that real multimodal LLM can correct different field types (dates, amounts, strings).
        """
        invoice_id = unique_invoice_id
        
        # Read PDF file
        with open(sample_pdf_path, "rb") as f:
            file_content = f.read()
        
        # Upload file
        file_handler = FileHandler()
        upload_result = file_handler.upload_file(
            file_content=file_content,
            file_name=os.path.basename(sample_pdf_path)
        )
        file_path = upload_result.get("file_path")
        if not file_path:
            pytest.skip("File upload failed")
        
        cleanup_uploaded_file.append(file_path)
        
        # Create invoice with wrong values of different types
        invoice = Invoice(
            id=invoice_id,
            file_path=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            processing_state=InvoiceState.PENDING,
            invoice_date=datetime(2099, 12, 31).date(),  # Wrong date
            total_amount=Decimal("999999.99"),  # Wrong amount
            vendor_name="WRONG VENDOR",  # Wrong string
            field_confidence={
                "invoice_date": 0.3,
                "total_amount": 0.3,
                "vendor_name": 0.3,
            }
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        
        # Run extraction
        result = await extraction_service.extract_invoice(
            invoice_id=invoice_id,
            file_identifier=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            db=db_session
        )
        
        # Verify extraction succeeded
        assert result["status"] == "extracted", \
            f"Extraction failed: {result.get('errors', [])}"
        
        # Verify invoice was extracted
        updated_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
        assert updated_invoice is not None
        
        # Verify different field types were corrected
        corrections_made = 0
        
        # Date field correction
        if updated_invoice.invoice_date:
            if updated_invoice.invoice_date != datetime(2099, 12, 31).date():
                corrections_made += 1
        
        # Amount field correction
        if updated_invoice.total_amount:
            if updated_invoice.total_amount != Decimal("999999.99"):
                corrections_made += 1
        
        # String field correction
        if updated_invoice.vendor_name:
            if updated_invoice.vendor_name != "WRONG VENDOR":
                corrections_made += 1
        
        assert corrections_made >= 1, \
            f"Expected at least 1 field type to be corrected, got {corrections_made}"
    
    async def test_confidence_scores_persist_to_database(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that confidence scores from multimodal LLM are properly persisted to the database.
        """
        invoice_id = unique_invoice_id
        
        # Read PDF file
        with open(sample_pdf_path, "rb") as f:
            file_content = f.read()
        
        # Upload file
        file_handler = FileHandler()
        upload_result = file_handler.upload_file(
            file_content=file_content,
            file_name=os.path.basename(sample_pdf_path)
        )
        file_path = upload_result.get("file_path")
        if not file_path:
            pytest.skip("File upload failed")
        
        cleanup_uploaded_file.append(file_path)
        
        # Create invoice with low-confidence field
        invoice = Invoice(
            id=invoice_id,
            file_path=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            processing_state=InvoiceState.PENDING,
            field_confidence={"invoice_number": 0.3}
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        
        # Run extraction
        result = await extraction_service.extract_invoice(
            invoice_id=invoice_id,
            file_identifier=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            db=db_session
        )
        
        # Verify extraction succeeded
        assert result["status"] == "extracted", \
            f"Extraction failed: {result.get('errors', [])}"
        
        # Fetch invoice from database again to verify persistence
        persisted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
        assert persisted_invoice is not None
        
        # Verify confidence scores were persisted
        assert persisted_invoice.field_confidence is not None, \
            "Field confidence should be persisted"
        
        if persisted_invoice.invoice_number:
            invoice_number_conf = persisted_invoice.field_confidence.get("invoice_number")
            assert invoice_number_conf is not None, \
                "Invoice number confidence should be persisted"
            assert 0.0 <= invoice_number_conf <= 1.0, \
                f"Confidence should be between 0.0 and 1.0, got {invoice_number_conf}"
    
    async def test_full_extraction_pipeline_with_multimodal_llm(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test the full extraction pipeline with multimodal LLM: DI → Multimodal LLM → Database persistence.
        Verifies that scanned PDFs trigger multimodal LLM and the full pipeline works end-to-end.
        """
        invoice_id = unique_invoice_id
        
        # Read PDF file
        with open(sample_pdf_path, "rb") as f:
            file_content = f.read()
        
        # Verify PDF is scanned (required for multimodal)
        from starlette.concurrency import run_in_threadpool
        is_scanned = await run_in_threadpool(
            extraction_service._is_scanned_pdf,
            file_content
        )
        if not is_scanned:
            pytest.skip("PDF is not detected as scanned - multimodal LLM tests require scanned PDFs")
        
        # Verify multimodal image rendering works
        images = await run_in_threadpool(
            extraction_service._render_multimodal_images,
            file_content
        )
        assert len(images) > 0, "Multimodal LLM requires rendered images"
        assert all(len(img) > 0 for img in images), "Rendered images should not be empty"
        
        # Upload file
        file_handler = FileHandler()
        upload_result = file_handler.upload_file(
            file_content=file_content,
            file_name=os.path.basename(sample_pdf_path)
        )
        file_path = upload_result.get("file_path")
        if not file_path:
            pytest.skip("File upload failed")
        
        # Track file for cleanup
        cleanup_uploaded_file.append(file_path)
        
        # Run full extraction pipeline (DI → Multimodal LLM → DB)
        result = await extraction_service.extract_invoice(
            invoice_id=invoice_id,
            file_identifier=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            db=db_session
        )
        
        # Verify extraction succeeded
        assert result["status"] == "extracted", \
            f"Full pipeline extraction failed: {result.get('errors', [])}"
        
        # Verify invoice was saved to database
        extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
        assert extracted_invoice is not None
        
        # Verify processing state
        assert extracted_invoice.processing_state == InvoiceState.EXTRACTED, \
            f"Processing state should be EXTRACTED, got {extracted_invoice.processing_state}"
        
        # Verify at least some fields were extracted
        extracted_fields = []
        if extracted_invoice.invoice_number:
            extracted_fields.append("invoice_number")
        if extracted_invoice.vendor_name:
            extracted_fields.append("vendor_name")
        if extracted_invoice.total_amount:
            extracted_fields.append("total_amount")
        
        assert len(extracted_fields) >= 1, \
            f"Expected at least 1 field to be extracted by multimodal LLM, got {len(extracted_fields)}"
        
        # Verify confidence scores are present (multimodal LLM should update them)
        assert extracted_invoice.field_confidence is not None, \
            "Field confidence should be set after multimodal LLM extraction"
        
        # The db_session fixture handles rollback and cleanup
    
    async def test_multimodal_llm_with_scanned_pdf_detection(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that multimodal LLM is triggered when PDF is detected as scanned.
        Verifies the detection logic and multimodal fallback activation.
        """
        invoice_id = unique_invoice_id
        
        # Read PDF file
        with open(sample_pdf_path, "rb") as f:
            file_content = f.read()
        
        # Test PDF detection
        from starlette.concurrency import run_in_threadpool
        is_scanned = await run_in_threadpool(
            extraction_service._is_scanned_pdf,
            file_content
        )
        
        # Upload file
        file_handler = FileHandler()
        upload_result = file_handler.upload_file(
            file_content=file_content,
            file_name=os.path.basename(sample_pdf_path)
        )
        file_path = upload_result.get("file_path")
        if not file_path:
            pytest.skip("File upload failed")
        
        cleanup_uploaded_file.append(file_path)
        
        # Create invoice with low-confidence fields
        invoice = Invoice(
            id=invoice_id,
            file_path=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            processing_state=InvoiceState.PENDING,
            field_confidence={"invoice_number": 0.3}
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        
        # If PDF is scanned, verify multimodal components are available
        if is_scanned:
            # Verify image rendering works
            images = await run_in_threadpool(
                extraction_service._render_multimodal_images,
                file_content
            )
            assert len(images) > 0, "Scanned PDF should render images for multimodal LLM"
            
            # Verify multimodal config is available
            assert extraction_service._has_multimodal_config(), \
                "Multimodal config should be available for scanned PDFs"
        
        # Run extraction
        result = await extraction_service.extract_invoice(
            invoice_id=invoice_id,
            file_identifier=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            db=db_session
        )
        
        # Verify extraction succeeded
        assert result["status"] == "extracted", \
            f"Extraction failed: {result.get('errors', [])}"
        
        # Verify invoice was extracted
        extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
        assert extracted_invoice is not None
    
    async def test_multimodal_llm_image_rendering(
        self,
        extraction_service,
        sample_pdf_path,
        unique_invoice_id
    ):
        """
        Test that multimodal LLM image rendering works correctly.
        Verifies PDF pages are converted to base64-encoded images.
        """
        # Read PDF file
        with open(sample_pdf_path, "rb") as f:
            file_content = f.read()
        
        # Test image rendering
        from starlette.concurrency import run_in_threadpool
        images = await run_in_threadpool(
            extraction_service._render_multimodal_images,
            file_content
        )
        
        # Verify images were rendered
        assert len(images) > 0, "Should render at least one image from PDF"
        
        # Verify image format (base64-encoded strings)
        for i, img in enumerate(images):
            assert isinstance(img, str), f"Image {i} should be a string (base64-encoded)"
            assert len(img) > 0, f"Image {i} should not be empty"
            # Base64 strings should be reasonably long (at least 100 chars for a small image)
            assert len(img) > 100, f"Image {i} seems too short to be a valid base64 image"
        
        # Verify max pages setting is respected
        max_pages = getattr(settings, "MULTIMODAL_MAX_PAGES", 2)
        assert len(images) <= max_pages, \
            f"Should not render more than {max_pages} pages, got {len(images)}"

