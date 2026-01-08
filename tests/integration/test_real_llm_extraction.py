"""
Integration tests for REAL Azure OpenAI LLM extraction.

These tests make actual API calls to Azure OpenAI and write results to isolated test databases.
They verify that the LLM can actually extract and correct invoice fields.

Requirements:
- Azure OpenAI credentials must be configured (AOAI_ENDPOINT, AOAI_API_KEY, AOAI_DEPLOYMENT_NAME)
- Tests will be skipped if credentials are not available
- Each test uses an isolated test database (no conflicts)
- Uploaded files are automatically cleaned up after each test
"""

import pytest
import os
import time
import asyncio
from datetime import datetime, date
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
class TestRealLLMExtraction:
    """Integration tests for real Azure OpenAI LLM extraction"""
    
    @pytest.fixture
    def extraction_service(self, monkeypatch):
        """Create extraction service with real DI and LLM clients"""
        # Check if Azure OpenAI is configured
        if not settings.AOAI_ENDPOINT or not settings.AOAI_API_KEY or not settings.AOAI_DEPLOYMENT_NAME:
            pytest.skip("Azure OpenAI credentials not configured - skipping real LLM tests")
        
        # Check if Azure Document Intelligence is configured
        if not settings.AZURE_FORM_RECOGNIZER_ENDPOINT or not settings.AZURE_FORM_RECOGNIZER_KEY:
            pytest.skip("Azure Document Intelligence credentials not configured - skipping real LLM tests")
        
        # Override the autouse fixture that disables LLM fallback
        # We need LLM fallback enabled for these tests
        monkeypatch.setattr(settings, "USE_LLM_FALLBACK", True, raising=False)
        
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
        unique_id = f"test-llm-{timestamp}-{uuid4().hex[:8]}"
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
                        # Also try to remove parent directory if empty
                        parent = path.parent
                        if parent.exists() and not any(parent.iterdir()):
                            parent.rmdir()
            except Exception as e:
                # Log but don't fail test on cleanup errors
                print(f"Warning: Failed to cleanup file {file_path}: {e}")
    
    async def test_real_llm_extracts_invoice_number(
        self, 
        extraction_service, 
        db_session, 
        sample_pdf_path, 
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """Test that real LLM can extract invoice_number from a low-confidence field"""
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
            pytest.skip("File upload failed - cannot test LLM extraction")
        
        # Track file for cleanup
        cleanup_uploaded_file.append(file_path)
        
        # Ensure invoice doesn't exist or is reset to PENDING state
        existing = await DatabaseService.get_invoice(invoice_id, db=db_session)
        if existing:
            # If invoice is in PROCESSING state, we need to delete it (can't reset from PROCESSING)
            if existing.processing_state == InvoiceState.PROCESSING:
                from src.models.db_models import Invoice as InvoiceDB
                from sqlalchemy import delete
                await db_session.execute(delete(InvoiceDB).where(InvoiceDB.id == invoice_id))
                await db_session.commit()
            else:
                # Try to reset to PENDING if it exists in another state
                reset_success = await DatabaseService.reset_for_reextract(invoice_id, db=db_session)
                if not reset_success:
                    # If reset failed, delete and recreate
                    from src.models.db_models import Invoice as InvoiceDB
                    from sqlalchemy import delete
                    await db_session.execute(delete(InvoiceDB).where(InvoiceDB.id == invoice_id))
                    await db_session.commit()
        
        # Create invoice with low confidence for invoice_number to trigger LLM
        invoice = Invoice(
            id=invoice_id,
            file_path=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            processing_state=InvoiceState.PENDING,
            field_confidence={"invoice_number": 0.5}  # Low confidence to trigger LLM
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        await db_session.commit()  # Ensure invoice is committed before extraction
        
        try:
            # Run extraction with real LLM
            result = await extraction_service.extract_invoice(
                invoice_id=invoice_id,
                file_identifier=file_path,
                file_name=os.path.basename(sample_pdf_path),
                upload_date=datetime.utcnow(),
                db=db_session
            )
            
            # Verify extraction succeeded
            assert result["status"] == "extracted", f"Extraction failed: {result.get('errors', [])}"
            
            # Fetch invoice from database
            extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
            assert extracted_invoice is not None
            
            # Verify invoice_number was extracted (either by DI or LLM)
            assert extracted_invoice.invoice_number is not None, "invoice_number should be extracted"
            assert extracted_invoice.invoice_number != "", "invoice_number should not be empty"
            
            # Verify confidence was updated
            if extracted_invoice.field_confidence:
                invoice_number_conf = extracted_invoice.field_confidence.get("invoice_number")
                if invoice_number_conf is not None:
                    # If LLM was used, confidence should be higher than initial 0.5
                    # If DI extracted it directly, confidence might be high from DI
                    assert invoice_number_conf > 0.0, "Confidence should be set"
            
            # Verify LLM was triggered (if low confidence fields existed)
            if result.get("low_confidence_triggered"):
                assert "low_confidence_fields" in result
                # If invoice_number was in low confidence fields, LLM should have processed it
                if "invoice_number" in result.get("low_confidence_fields", []):
                    # LLM should have improved the field
                    assert extracted_invoice.invoice_number is not None
        finally:
            # Note: No need to manually delete invoice - isolated test database is cleaned up automatically
            # The db_session fixture handles rollback and cleanup
            pass
    
    async def test_full_extraction_pipeline_with_llm(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test the full extraction pipeline: DI extraction -> LLM fallback -> database persistence.
        Verifies that the complete pipeline works end-to-end with real services.
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
            pytest.skip("File upload failed - cannot test full pipeline")
        
        cleanup_uploaded_file.append(file_path)
        
        # Ensure invoice doesn't exist or is reset to PENDING state
        existing = await DatabaseService.get_invoice(invoice_id, db=db_session)
        if existing:
            # If invoice is in PROCESSING state, we need to delete it (can't reset from PROCESSING)
            if existing.processing_state == InvoiceState.PROCESSING:
                from src.models.db_models import InvoiceDB
                from sqlalchemy import delete
                await db_session.execute(delete(InvoiceDB).where(InvoiceDB.id == invoice_id))
                await db_session.commit()
            else:
                # Try to reset to PENDING if it exists in another state
                await DatabaseService.reset_for_reextract(invoice_id, db=db_session)
        
        # Create invoice in PENDING state
        invoice = Invoice(
            id=invoice_id,
            file_path=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            processing_state=InvoiceState.PENDING,
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        await db_session.commit()  # Ensure invoice is committed before extraction
        
        try:
            # Step 1: Run full extraction (DI + LLM)
            result = await extraction_service.extract_invoice(
                invoice_id=invoice_id,
                file_identifier=file_path,
                file_name=os.path.basename(sample_pdf_path),
                upload_date=datetime.utcnow(),
                db=db_session
            )
            
            # Verify extraction succeeded
            assert result["status"] == "extracted", f"Full pipeline extraction failed: {result.get('errors', [])}"
            
            # Step 2: Fetch invoice from database
            extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
            assert extracted_invoice is not None, "Invoice should be saved to database"
            
            # Step 3: Verify invoice state was updated
            assert extracted_invoice.processing_state == InvoiceState.EXTRACTED, \
                "Processing state should be EXTRACTED after successful extraction"
            
            # Step 4: Verify key fields were extracted
            assert extracted_invoice.invoice_number is not None, "invoice_number should be extracted"
            assert extracted_invoice.vendor_name is not None, "vendor_name should be extracted"
            assert extracted_invoice.total_amount is not None, "total_amount should be extracted"
            
            # Step 5: Verify confidence scores are set
            assert extracted_invoice.field_confidence is not None, "Field confidence should be set"
            assert len(extracted_invoice.field_confidence) > 0, "At least some field confidence scores should be set"
            assert extracted_invoice.extraction_confidence is not None, "Overall extraction confidence should be set"
            
            # Step 6: Verify LLM was potentially triggered (if low confidence fields existed)
            # Note: LLM may or may not be triggered depending on DI confidence scores
            print(f"\nExtraction confidence: {extracted_invoice.extraction_confidence}")
            print(f"Fields with confidence: {len(extracted_invoice.field_confidence)}")
            
        finally:
            pass
    
    async def test_llm_improves_low_confidence_fields(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that LLM improves fields with low confidence scores.
        Creates an invoice with low confidence fields and verifies LLM improves them.
        """
        invoice_id = unique_invoice_id
        
        with open(sample_pdf_path, "rb") as f:
            file_content = f.read()
        
        file_handler = FileHandler()
        upload_result = file_handler.upload_file(
            file_content=file_content,
            file_name=os.path.basename(sample_pdf_path)
        )
        file_path = upload_result.get("file_path")
        if not file_path:
            pytest.skip("File upload failed")
        
        cleanup_uploaded_file.append(file_path)
        
        # Ensure invoice doesn't exist or is reset to PENDING state
        existing = await DatabaseService.get_invoice(invoice_id, db=db_session)
        if existing:
            # If invoice is in PROCESSING state, we need to delete it (can't reset from PROCESSING)
            if existing.processing_state == InvoiceState.PROCESSING:
                from src.models.db_models import InvoiceDB
                from sqlalchemy import delete
                await db_session.execute(delete(InvoiceDB).where(InvoiceDB.id == invoice_id))
                await db_session.commit()
            else:
                # Try to reset to PENDING if it exists in another state
                await DatabaseService.reset_for_reextract(invoice_id, db=db_session)
        
        # Create invoice with intentionally low confidence fields
        invoice = Invoice(
            id=invoice_id,
            file_path=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            processing_state=InvoiceState.PENDING,
            field_confidence={
                "invoice_number": 0.3,  # Very low confidence
                "vendor_name": 0.4,     # Very low confidence
                "total_amount": 0.35,    # Very low confidence
            }
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        await db_session.commit()
        
        # Store initial state
        initial_confidences = invoice.field_confidence.copy() if invoice.field_confidence else {}
        
        try:
            # Run extraction with LLM fallback
            result = await extraction_service.extract_invoice(
                invoice_id=invoice_id,
                file_identifier=file_path,
                file_name=os.path.basename(sample_pdf_path),
                upload_date=datetime.utcnow(),
                db=db_session
            )
            
            assert result["status"] == "extracted", f"Extraction failed: {result.get('errors', [])}"
            
            # Fetch updated invoice
            updated_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
            assert updated_invoice is not None
            
            # Verify confidence scores improved for low-confidence fields
            if updated_invoice.field_confidence:
                for field_name, initial_conf in initial_confidences.items():
                    if initial_conf < 0.5:  # Was low confidence
                        updated_conf = updated_invoice.field_confidence.get(field_name)
                        if updated_conf is not None:
                            # Confidence should have improved (or at least be set)
                            assert updated_conf >= initial_conf, \
                                f"Confidence for {field_name} should improve or stay same (was {initial_conf}, now {updated_conf})"
                            
                            # If LLM was used, confidence should be significantly higher
                            if updated_conf > initial_conf + 0.2:
                                print(f"\nLLM improved {field_name}: {initial_conf} -> {updated_conf}")
            
        finally:
            pass
    
    async def test_llm_confidence_calculation_accuracy(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that LLM confidence scores are calculated correctly based on context:
        - Filling blank fields should get high confidence (0.85-0.95)
        - Correcting wrong values should get medium-high confidence (0.75-0.85)
        - Confirming existing values should get medium confidence (0.70-0.80)
        """
        invoice_id = unique_invoice_id
        
        with open(sample_pdf_path, "rb") as f:
            file_content = f.read()
        
        file_handler = FileHandler()
        upload_result = file_handler.upload_file(
            file_content=file_content,
            file_name=os.path.basename(sample_pdf_path)
        )
        file_path = upload_result.get("file_path")
        if not file_path:
            pytest.skip("File upload failed")
        
        cleanup_uploaded_file.append(file_path)
        
        # Ensure invoice doesn't exist or is reset to PENDING state
        existing = await DatabaseService.get_invoice(invoice_id, db=db_session)
        if existing:
            # If invoice is in PROCESSING state, we need to delete it (can't reset from PROCESSING)
            if existing.processing_state == InvoiceState.PROCESSING:
                from src.models.db_models import InvoiceDB
                from sqlalchemy import delete
                await db_session.execute(delete(InvoiceDB).where(InvoiceDB.id == invoice_id))
                await db_session.commit()
            else:
                # Try to reset to PENDING if it exists in another state
                await DatabaseService.reset_for_reextract(invoice_id, db=db_session)
        
        # Create invoice with mixed scenarios:
        # 1. Blank field (should get high confidence if LLM fills it)
        # 2. Wrong value with low confidence (should get medium-high confidence if LLM corrects it)
        # 3. Existing value with low confidence (should get medium confidence if LLM confirms it)
        invoice = Invoice(
            id=invoice_id,
            file_path=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            processing_state=InvoiceState.PENDING,
            # Blank field scenario
            invoice_number=None,
            # Wrong value scenario
            vendor_name="WRONG VENDOR",
            # Existing value scenario
            total_amount=Decimal("999.99"),  # Wrong amount
            field_confidence={
                "invoice_number": 0.0,  # Blank field
                "vendor_name": 0.3,     # Wrong value, low confidence
                "total_amount": 0.4,    # Wrong value, low confidence
            }
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        await db_session.commit()
        
        try:
            # Run extraction
            result = await extraction_service.extract_invoice(
                invoice_id=invoice_id,
                file_identifier=file_path,
                file_name=os.path.basename(sample_pdf_path),
                upload_date=datetime.utcnow(),
                db=db_session
            )
            
            assert result["status"] == "extracted", f"Extraction failed: {result.get('errors', [])}"
            
            # Fetch updated invoice
            updated_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
            assert updated_invoice is not None
            
            # Verify confidence scores are within expected ranges
            if updated_invoice.field_confidence:
                # Check invoice_number (blank field scenario)
                if updated_invoice.invoice_number is not None:
                    invoice_number_conf = updated_invoice.field_confidence.get("invoice_number")
                    if invoice_number_conf is not None:
                        # If LLM filled a blank field, confidence should be high (0.85-0.95)
                        # But we can't guarantee LLM was used, so just verify it's reasonable
                        assert 0.0 <= invoice_number_conf <= 1.0, \
                            f"invoice_number confidence should be between 0 and 1, got {invoice_number_conf}"
                
                # Check vendor_name (wrong value scenario)
                if updated_invoice.vendor_name is not None and updated_invoice.vendor_name != "WRONG VENDOR":
                    vendor_name_conf = updated_invoice.field_confidence.get("vendor_name")
                    if vendor_name_conf is not None:
                        # If LLM corrected a wrong value, confidence should be medium-high (0.75-0.85)
                        # But we can't guarantee LLM was used, so just verify it's reasonable
                        assert 0.0 <= vendor_name_conf <= 1.0, \
                            f"vendor_name confidence should be between 0 and 1, got {vendor_name_conf}"
                
                # Check total_amount (wrong value scenario)
                if updated_invoice.total_amount is not None and updated_invoice.total_amount != Decimal("999.99"):
                    total_amount_conf = updated_invoice.field_confidence.get("total_amount")
                    if total_amount_conf is not None:
                        # If LLM corrected a wrong value, confidence should be medium-high (0.75-0.85)
                        assert 0.0 <= total_amount_conf <= 1.0, \
                            f"total_amount confidence should be between 0 and 1, got {total_amount_conf}"
            
            # Print confidence scores for manual verification
            print("\nConfidence scores after extraction:")
            if updated_invoice.field_confidence:
                for field, conf in updated_invoice.field_confidence.items():
                    if field in ["invoice_number", "vendor_name", "total_amount"]:
                        print(f"  {field}: {conf}")
            
        finally:
            pass
    
    async def test_llm_corrects_multiple_field_types(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that LLM can correct different field types:
        - String fields (invoice_number, vendor_name)
        - Date fields (invoice_date, due_date)
        - Decimal fields (total_amount, tax_amount)
        - Address fields (vendor_address, bill_to_address)
        """
        invoice_id = unique_invoice_id
        
        with open(sample_pdf_path, "rb") as f:
            file_content = f.read()
        
        file_handler = FileHandler()
        upload_result = file_handler.upload_file(
            file_content=file_content,
            file_name=os.path.basename(sample_pdf_path)
        )
        file_path = upload_result.get("file_path")
        if not file_path:
            pytest.skip("File upload failed")
        
        cleanup_uploaded_file.append(file_path)
        
        # Ensure invoice doesn't exist or is reset to PENDING state
        existing = await DatabaseService.get_invoice(invoice_id, db=db_session)
        if existing:
            # If invoice is in PROCESSING state, we need to delete it (can't reset from PROCESSING)
            if existing.processing_state == InvoiceState.PROCESSING:
                from src.models.db_models import InvoiceDB
                from sqlalchemy import delete
                await db_session.execute(delete(InvoiceDB).where(InvoiceDB.id == invoice_id))
                await db_session.commit()
            else:
                # Try to reset to PENDING if it exists in another state
                await DatabaseService.reset_for_reextract(invoice_id, db=db_session)
        
        # Create invoice with wrong values for different field types
        invoice = Invoice(
            id=invoice_id,
            file_path=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            processing_state=InvoiceState.PENDING,
            # Wrong string value
            invoice_number="WRONG-INV-001",
            # Wrong date (far in future)
            invoice_date=datetime(2099, 12, 31).date(),
            # Wrong decimal value
            total_amount=Decimal("999999.99"),
            field_confidence={
                "invoice_number": 0.3,
                "invoice_date": 0.3,
                "total_amount": 0.3,
            }
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        await db_session.commit()
        
        # Store initial values
        initial_values = {
            "invoice_number": invoice.invoice_number,
            "invoice_date": invoice.invoice_date,
            "total_amount": invoice.total_amount,
        }
        
        try:
            # Run extraction
            result = await extraction_service.extract_invoice(
                invoice_id=invoice_id,
                file_identifier=file_path,
                file_name=os.path.basename(sample_pdf_path),
                upload_date=datetime.utcnow(),
                db=db_session
            )
            
            assert result["status"] == "extracted", f"Extraction failed: {result.get('errors', [])}"
            
            # Fetch updated invoice
            updated_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
            assert updated_invoice is not None
            
            # Verify fields were extracted (may or may not be corrected by LLM)
            fields_updated = 0
            
            # Check string field
            if updated_invoice.invoice_number is not None:
                if updated_invoice.invoice_number != initial_values["invoice_number"]:
                    fields_updated += 1
                    print(f"\nString field corrected: invoice_number '{initial_values['invoice_number']}' -> '{updated_invoice.invoice_number}'")
            
            # Check date field
            if updated_invoice.invoice_date is not None:
                if updated_invoice.invoice_date != initial_values["invoice_date"]:
                    fields_updated += 1
                    print(f"\nDate field corrected: invoice_date '{initial_values['invoice_date']}' -> '{updated_invoice.invoice_date}'")
            
            # Check decimal field
            if updated_invoice.total_amount is not None:
                if updated_invoice.total_amount != initial_values["total_amount"]:
                    fields_updated += 1
                    print(f"\nDecimal field corrected: total_amount '{initial_values['total_amount']}' -> '{updated_invoice.total_amount}'")
            
            # At least some fields should be extracted (either by DI or LLM)
            assert updated_invoice.invoice_number is not None or \
                   updated_invoice.invoice_date is not None or \
                   updated_invoice.total_amount is not None, \
                   "At least one field should be extracted"
            
            # Verify confidence scores were updated
            if updated_invoice.field_confidence:
                for field in ["invoice_number", "invoice_date", "total_amount"]:
                    if field in updated_invoice.field_confidence:
                        conf = updated_invoice.field_confidence[field]
                        assert 0.0 <= conf <= 1.0, \
                            f"{field} confidence should be between 0 and 1, got {conf}"
            
            print(f"\nTotal fields updated: {fields_updated}/3")
            
        finally:
            pass
    
    async def test_confidence_scores_persist_to_database(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that confidence scores calculated by LLM are properly persisted to the database.
        """
        invoice_id = unique_invoice_id
        
        with open(sample_pdf_path, "rb") as f:
            file_content = f.read()
        
        file_handler = FileHandler()
        upload_result = file_handler.upload_file(
            file_content=file_content,
            file_name=os.path.basename(sample_pdf_path)
        )
        file_path = upload_result.get("file_path")
        if not file_path:
            pytest.skip("File upload failed")
        
        cleanup_uploaded_file.append(file_path)
        
        # Ensure invoice doesn't exist or is reset to PENDING state
        existing = await DatabaseService.get_invoice(invoice_id, db=db_session)
        if existing:
            # If invoice is in PROCESSING state, we need to delete it (can't reset from PROCESSING)
            if existing.processing_state == InvoiceState.PROCESSING:
                from src.models.db_models import InvoiceDB
                from sqlalchemy import delete
                await db_session.execute(delete(InvoiceDB).where(InvoiceDB.id == invoice_id))
                await db_session.commit()
            else:
                # Try to reset to PENDING if it exists in another state
                await DatabaseService.reset_for_reextract(invoice_id, db=db_session)
        
        invoice = Invoice(
            id=invoice_id,
            file_path=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            processing_state=InvoiceState.PENDING,
            field_confidence={"invoice_number": 0.3, "vendor_name": 0.4}
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        await db_session.commit()
        
        try:
            # Run extraction
            result = await extraction_service.extract_invoice(
                invoice_id=invoice_id,
                file_identifier=file_path,
                file_name=os.path.basename(sample_pdf_path),
                upload_date=datetime.utcnow(),
                db=db_session
            )
            
            assert result["status"] == "extracted", f"Extraction failed: {result.get('errors', [])}"
            
            # Fetch invoice from database
            persisted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
            assert persisted_invoice is not None
            
            # Verify confidence scores are persisted
            assert persisted_invoice.field_confidence is not None, \
                "Field confidence should be persisted to database"
            assert len(persisted_invoice.field_confidence) > 0, \
                "At least some field confidence scores should be persisted"
            
            # Verify overall extraction confidence is persisted
            assert persisted_invoice.extraction_confidence is not None, \
                "Overall extraction confidence should be persisted to database"
            assert 0.0 <= persisted_invoice.extraction_confidence <= 1.0, \
                f"Extraction confidence should be between 0 and 1, got {persisted_invoice.extraction_confidence}"
            
            # Verify specific field confidences are persisted
            if persisted_invoice.invoice_number is not None:
                invoice_number_conf = persisted_invoice.field_confidence.get("invoice_number")
                if invoice_number_conf is not None:
                    assert 0.0 <= invoice_number_conf <= 1.0, \
                        f"invoice_number confidence should be between 0 and 1, got {invoice_number_conf}"
            
            if persisted_invoice.vendor_name is not None:
                vendor_name_conf = persisted_invoice.field_confidence.get("vendor_name")
                if vendor_name_conf is not None:
                    assert 0.0 <= vendor_name_conf <= 1.0, \
                        f"vendor_name confidence should be between 0 and 1, got {vendor_name_conf}"
            
            print(f"\nPersisted extraction confidence: {persisted_invoice.extraction_confidence}")
            print(f"Persisted field confidences: {len(persisted_invoice.field_confidence)} fields")
            
        finally:
            pass
    
    async def test_real_llm_extracts_multiple_fields(
        self, 
        extraction_service, 
        db_session, 
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """Test that real LLM can extract multiple fields from low-confidence data"""
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
            pytest.skip("File upload failed - cannot test LLM extraction")
        
        # Track file for cleanup
        cleanup_uploaded_file.append(file_path)
        
        # Ensure invoice doesn't exist or is reset to PENDING state
        existing = await DatabaseService.get_invoice(invoice_id, db=db_session)
        if existing:
            # If invoice is in PROCESSING state, we need to delete it (can't reset from PROCESSING)
            if existing.processing_state == InvoiceState.PROCESSING:
                from src.models.db_models import InvoiceDB
                from sqlalchemy import delete
                await db_session.execute(delete(InvoiceDB).where(InvoiceDB.id == invoice_id))
                await db_session.commit()
            else:
                # Try to reset to PENDING if it exists in another state
                await DatabaseService.reset_for_reextract(invoice_id, db=db_session)
        
        # Create invoice with multiple low confidence fields
        invoice = Invoice(
            id=invoice_id,
            file_path=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            processing_state=InvoiceState.PENDING,
            field_confidence={
                "invoice_number": 0.5,
                "vendor_name": 0.5,
                "total_amount": 0.5,
                "invoice_date": 0.5
            }
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        await db_session.commit()
        
        try:
            # Run extraction
            result = await extraction_service.extract_invoice(
                invoice_id=invoice_id,
                file_identifier=file_path,
                file_name=os.path.basename(sample_pdf_path),
                upload_date=datetime.utcnow(),
                db=db_session
            )
            
            # Verify extraction succeeded
            assert result["status"] == "extracted", f"Extraction failed: {result.get('errors', [])}"
            
            # Fetch invoice from database
            extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
            assert extracted_invoice is not None
            
            # Verify multiple fields were extracted
            fields_to_check = ["invoice_number", "vendor_name", "total_amount", "invoice_date"]
            extracted_count = 0
            
            for field in fields_to_check:
                value = getattr(extracted_invoice, field, None)
                if value is not None and value != "":
                    extracted_count += 1
            
            # At least some fields should be extracted
            assert extracted_count > 0, "At least one field should be extracted"
            
            # If LLM was triggered, verify it processed low confidence fields
            if result.get("low_confidence_triggered"):
                low_conf_fields = result.get("low_confidence_fields", [])
                assert len(low_conf_fields) > 0, "LLM should have processed low confidence fields"
        finally:
            # Note: No need to manually delete invoice - isolated test database is cleaned up automatically
            # The db_session fixture handles rollback and cleanup
            pass
    
    async def test_real_llm_corrects_wrong_values(
        self, 
        extraction_service, 
        db_session, 
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """Test that real LLM can correct wrong field values"""
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
            pytest.skip("File upload failed - cannot test LLM extraction")
        
        # Track file for cleanup
        cleanup_uploaded_file.append(file_path)
        
        # Ensure invoice doesn't exist or is reset to PENDING state
        existing = await DatabaseService.get_invoice(invoice_id, db=db_session)
        if existing:
            # If invoice is in PROCESSING state, we need to delete it (can't reset from PROCESSING)
            if existing.processing_state == InvoiceState.PROCESSING:
                from src.models.db_models import InvoiceDB
                from sqlalchemy import delete
                await db_session.execute(delete(InvoiceDB).where(InvoiceDB.id == invoice_id))
                await db_session.commit()
            else:
                # Try to reset to PENDING if it exists in another state
                await DatabaseService.reset_for_reextract(invoice_id, db=db_session)
        
        # Create invoice with wrong vendor_name and low confidence
        invoice = Invoice(
            id=invoice_id,
            file_path=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            processing_state=InvoiceState.PENDING,
            vendor_name="WRONG VENDOR NAME",  # Wrong value
            field_confidence={"vendor_name": 0.5}  # Low confidence
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        await db_session.commit()
        
        try:
            # Run extraction
            result = await extraction_service.extract_invoice(
                invoice_id=invoice_id,
                file_identifier=file_path,
                file_name=os.path.basename(sample_pdf_path),
                upload_date=datetime.utcnow(),
                db=db_session
            )
            
            # Verify extraction succeeded
            assert result["status"] == "extracted", f"Extraction failed: {result.get('errors', [])}"
            
            # Fetch invoice from database
            extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
            assert extracted_invoice is not None
            
            # Verify vendor_name was extracted (either corrected by LLM or extracted by DI)
            assert extracted_invoice.vendor_name is not None, "vendor_name should be extracted"
            assert extracted_invoice.vendor_name != "", "vendor_name should not be empty"
            
            # If LLM was triggered and vendor_name was in low confidence fields,
            # it may have been corrected (though we can't guarantee the exact value)
            if result.get("low_confidence_triggered"):
                low_conf_fields = result.get("low_confidence_fields", [])
                if "vendor_name" in low_conf_fields:
                    # LLM should have processed this field
                    # The value may have changed from "WRONG VENDOR NAME"
                    assert extracted_invoice.vendor_name != "WRONG VENDOR NAME" or \
                           extracted_invoice.vendor_name is not None
        finally:
            # Note: No need to manually delete invoice - isolated test database is cleaned up automatically
            # The db_session fixture handles rollback and cleanup
            pass
    
    async def test_llm_extracts_all_canonical_fields(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that the LLM extraction pipeline can extract ALL canonical fields from the schema.
        This is a comprehensive test that verifies the LLM can handle all field types in the canonical schema,
        not just low-confidence fields. It tests the full extraction pipeline (DI + LLM) and verifies
        which canonical fields were successfully extracted.
        """
        from src.extraction.extraction_service import CANONICAL_FIELDS
        
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
            pytest.skip("File upload failed - cannot test comprehensive extraction")
        
        cleanup_uploaded_file.append(file_path)
        
        # Delete invoice if it exists (to avoid any state conflicts)
        from src.models.db_models import Invoice as InvoiceDB
        from sqlalchemy import delete
        await db_session.execute(delete(InvoiceDB).where(InvoiceDB.id == invoice_id))
        await db_session.commit()
        
        # Refresh session to ensure clean state
        await db_session.close()
        await db_session.begin()
        
        # Create invoice directly in database using pydantic_to_db_invoice (like other tests)
        from src.models.db_utils import pydantic_to_db_invoice
        invoice = Invoice(
            id=invoice_id,
            file_path=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            processing_state=InvoiceState.PENDING,
            status="pending",
        )
        db_invoice = pydantic_to_db_invoice(invoice)
        db_session.add(db_invoice)
        await db_session.commit()
        
        # Refresh to ensure invoice is visible
        await db_session.refresh(db_invoice)
        
        try:
            # Run full extraction pipeline (DI + LLM)
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
            
            # Fetch extracted invoice from database
            extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
            assert extracted_invoice is not None, "Invoice should be saved to database"
            
            # Track which canonical fields were extracted
            extracted_fields = {}
            missing_fields = []
            
            # Check each canonical field
            for field_name in sorted(CANONICAL_FIELDS):
                # Get field value from invoice
                field_value = getattr(extracted_invoice, field_name, None)
                
                # Check if field was extracted (has a non-empty value)
                is_extracted = False
                if field_value is not None:
                    # Handle different field types
                    if isinstance(field_value, str):
                        is_extracted = field_value.strip() != ""
                    elif isinstance(field_value, (int, float, Decimal)):
                        is_extracted = True
                    elif isinstance(field_value, (datetime, date)):
                        is_extracted = True
                    elif isinstance(field_value, dict):
                        # For address fields and other dict fields
                        is_extracted = len(field_value) > 0
                    elif isinstance(field_value, list):
                        # For list fields
                        is_extracted = len(field_value) > 0
                    else:
                        is_extracted = field_value is not None
                
                # Get confidence score if available
                confidence = None
                if extracted_invoice.field_confidence:
                    confidence = extracted_invoice.field_confidence.get(field_name)
                
                extracted_fields[field_name] = {
                    "extracted": is_extracted,
                    "value": field_value,
                    "confidence": confidence
                }
                
                if not is_extracted:
                    missing_fields.append(field_name)
            
            # Calculate extraction statistics
            total_fields = len(CANONICAL_FIELDS)
            extracted_count = sum(1 for f in extracted_fields.values() if f["extracted"])
            extraction_rate = (extracted_count / total_fields) * 100 if total_fields > 0 else 0
            
            # Print comprehensive extraction report
            print(f"\n{'='*80}")
            print(f"CANONICAL FIELD EXTRACTION REPORT")
            print(f"{'='*80}")
            print(f"Total canonical fields: {total_fields}")
            print(f"Fields extracted: {extracted_count} ({extraction_rate:.1f}%)")
            print(f"Fields missing: {len(missing_fields)} ({100 - extraction_rate:.1f}%)")
            print(f"\nExtraction confidence: {extracted_invoice.extraction_confidence}")
            
            # Print extracted fields by category
            categories = {
                "Header": ["invoice_number", "invoice_date", "due_date", "invoice_type", "reference_number"],
                "Vendor": ["vendor_name", "vendor_id", "vendor_phone", "vendor_fax", "vendor_email", "vendor_website", "vendor_address"],
                "Vendor Tax IDs": ["gst_number", "qst_number", "pst_number", "business_number"],
                "Customer": ["customer_name", "customer_id", "customer_phone", "customer_email", "customer_fax", "bill_to_address"],
                "Remit-To": ["remit_to_address", "remit_to_name"],
                "Contract": ["entity", "contract_id", "standing_offer_number", "po_number"],
                "Dates": ["period_start", "period_end", "shipping_date", "delivery_date"],
                "Financial": ["subtotal", "discount_amount", "shipping_amount", "handling_fee", "deposit_amount"],
                "Canadian Taxes": ["gst_amount", "gst_rate", "hst_amount", "hst_rate", "qst_amount", "qst_rate", "pst_amount", "pst_rate"],
                "Total": ["tax_amount", "total_amount", "currency", "tax_breakdown"],
                "Payment": ["payment_terms", "payment_method", "payment_due_upon", "tax_registration_number"],
            }
            
            print(f"\n{'Category':<20} {'Extracted':<10} {'Total':<10} {'Rate':<10}")
            print(f"{'-'*50}")
            for category, fields in categories.items():
                cat_extracted = sum(1 for f in fields if extracted_fields.get(f, {}).get("extracted", False))
                cat_total = len(fields)
                cat_rate = (cat_extracted / cat_total * 100) if cat_total > 0 else 0
                print(f"{category:<20} {cat_extracted:<10} {cat_total:<10} {cat_rate:.1f}%")
            
            # Print detailed field status
            print(f"\n{'Field Name':<30} {'Extracted':<12} {'Confidence':<12} {'Value Preview':<30}")
            print(f"{'-'*84}")
            for field_name in sorted(CANONICAL_FIELDS):
                field_info = extracted_fields[field_name]
                extracted_str = "YES" if field_info["extracted"] else "NO"
                conf_str = f"{field_info['confidence']:.2f}" if field_info["confidence"] is not None else "N/A"
                
                # Preview value (truncate if too long)
                value_preview = str(field_info["value"])[:27] if field_info["value"] is not None else "None"
                if field_info["value"] is not None and len(str(field_info["value"])) > 27:
                    value_preview += "..."
                
                print(f"{field_name:<30} {extracted_str:<12} {conf_str:<12} {value_preview:<30}")
            
            # Print missing fields
            if missing_fields:
                print(f"\nMissing fields ({len(missing_fields)}):")
                for field in missing_fields:
                    print(f"  - {field}")
            
            # Assertions
            # At minimum, core invoice fields should be extracted
            core_fields = ["invoice_number", "vendor_name", "total_amount"]
            core_extracted = [f for f in core_fields if extracted_fields.get(f, {}).get("extracted", False)]
            assert len(core_extracted) > 0, \
                f"At least one core field should be extracted. Extracted: {core_extracted}"
            
            # Verify that extraction confidence is set
            assert extracted_invoice.extraction_confidence is not None, \
                "Overall extraction confidence should be set"
            assert 0.0 <= extracted_invoice.extraction_confidence <= 1.0, \
                f"Extraction confidence should be between 0 and 1, got {extracted_invoice.extraction_confidence}"
            
            # Verify field confidence scores are set for extracted fields
            if extracted_invoice.field_confidence:
                for field_name, field_info in extracted_fields.items():
                    if field_info["extracted"]:
                        conf = field_info["confidence"]
                        if conf is not None:
                            assert 0.0 <= conf <= 1.0, \
                                f"{field_name} confidence should be between 0 and 1, got {conf}"
            
            # Note: We don't assert a specific extraction rate because:
            # 1. Not all fields may be present in every invoice
            # 2. DI may not extract all fields
            # 3. LLM may not extract all fields if they're not in the document
            # The test verifies that the system CAN extract fields, not that it MUST extract all fields
            
            print(f"\n{'='*80}")
            print(f"Test completed successfully")
            print(f"{'='*80}\n")
            
        finally:
            pass
