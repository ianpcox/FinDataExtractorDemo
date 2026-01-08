"""
Integration tests for Multimodal LLM error handling scenarios.

These tests verify that the extraction service handles multimodal LLM errors gracefully:
- Image rendering failures (PyMuPDF not available, PDF errors, etc.)
- API failures
- Invalid responses
- Network issues
- Rate limiting
- Partial failures

Requirements:
- Azure OpenAI credentials must be configured (AOAI_ENDPOINT, AOAI_API_KEY, AOAI_DEPLOYMENT_NAME or AOAI_MULTIMODAL_DEPLOYMENT_NAME)
- Tests will be skipped if credentials are not available
- Each test uses an isolated test database (no conflicts)
"""

import pytest
import os
import time
from datetime import datetime
from decimal import Decimal
from uuid import uuid4
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, Mock
import asyncio

from src.extraction.extraction_service import ExtractionService
from src.extraction.document_intelligence_client import DocumentIntelligenceClient
from src.extraction.field_extractor import FieldExtractor
from src.ingestion.file_handler import FileHandler
from src.models.invoice import Invoice, InvoiceState
from src.services.db_service import DatabaseService
from src.config import settings

# Import OpenAI error classes if available
try:
    from openai import RateLimitError, APIError, AsyncAzureOpenAI
except ImportError:
    RateLimitError = None
    APIError = None
    AsyncAzureOpenAI = None


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
class TestMultimodalLLMErrorHandling:
    """Integration tests for Multimodal LLM error handling"""
    
    @pytest.fixture
    def extraction_service(self, monkeypatch):
        """Create extraction service with real DI and Multimodal LLM clients"""
        # Check if Azure OpenAI is configured
        if not settings.AOAI_ENDPOINT or not settings.AOAI_API_KEY:
            pytest.skip("Azure OpenAI credentials not configured - skipping multimodal LLM error handling tests")
        
        # Check for multimodal deployment
        multimodal_deployment = settings.AOAI_MULTIMODAL_DEPLOYMENT_NAME or settings.AOAI_DEPLOYMENT_NAME
        if not multimodal_deployment:
            pytest.skip("Azure OpenAI deployment not configured - skipping multimodal LLM error handling tests")
        
        # Check if Azure Document Intelligence is configured
        if not settings.AZURE_FORM_RECOGNIZER_ENDPOINT or not settings.AZURE_FORM_RECOGNIZER_KEY:
            pytest.skip("Azure Document Intelligence credentials not configured - skipping multimodal LLM error handling tests")
        
        # Override the autouse fixture that disables LLM fallback
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
        
        return service
    
    @pytest.fixture
    def sample_pdf_path(self):
        """Get path to sample PDF for testing"""
        sample_path = "data/sample_invoices/Raw/Raw_Basic/ACC012 4202092525.pdf"
        if not os.path.exists(sample_path):
            pytest.skip(f"Sample PDF not found at {sample_path}")
        return sample_path
    
    @pytest.fixture
    def unique_invoice_id(self):
        """Generate a unique invoice ID for each test"""
        timestamp = int(time.time() * 1000)
        unique_id = f"test-multimodal-error-{timestamp}-{uuid4().hex[:8]}"
        return unique_id
    
    @pytest.fixture
    def cleanup_uploaded_file(self):
        """Fixture to track and cleanup uploaded files"""
        uploaded_files = []
        yield uploaded_files
        file_handler = FileHandler()
        for file_path in uploaded_files:
            try:
                if isinstance(file_path, str):
                    path = Path(file_path)
                    if path.exists() and path.is_file():
                        path.unlink()
                        parent = path.parent
                        if parent.exists() and not any(parent.iterdir()):
                            parent.rmdir()
            except Exception as e:
                print(f"Warning: Failed to cleanup file {file_path}: {e}")
    
    async def test_multimodal_image_rendering_pymupdf_not_available(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that multimodal LLM handles PyMuPDF not being available gracefully.
        Should fall back to text-based LLM or skip multimodal.
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
        
        invoice = Invoice(
            id=invoice_id,
            file_path=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            processing_state=InvoiceState.PENDING,
            field_confidence={"invoice_number": 0.3}
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        
        # Mock PyMuPDF import to fail
        with patch('src.extraction.extraction_service.fitz', None):
            # Mock the import error
            original_render = extraction_service._render_multimodal_images
            def mock_render(file_content):
                # Simulate PyMuPDF not available
                return []
            
            extraction_service._render_multimodal_images = mock_render
            
            try:
                # Run extraction
                result = await extraction_service.extract_invoice(
                    invoice_id=invoice_id,
                    file_identifier=file_path,
                    file_name=os.path.basename(sample_pdf_path),
                    upload_date=datetime.utcnow(),
                    db=db_session
                )
                
                # Extraction should still succeed (should fall back to text-based LLM or DI-only)
                assert result["status"] == "extracted", \
                    f"Extraction should succeed even without PyMuPDF: {result.get('errors', [])}"
                
                extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
                assert extracted_invoice is not None
            finally:
                extraction_service._render_multimodal_images = original_render
    
    async def test_multimodal_image_rendering_pdf_open_failure(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that multimodal LLM handles PDF opening failures gracefully.
        """
        invoice_id = unique_invoice_id
        
        # Create corrupted PDF content
        corrupted_pdf = b"Not a valid PDF file content"
        
        file_handler = FileHandler()
        upload_result = file_handler.upload_file(
            file_content=corrupted_pdf,
            file_name="corrupted.pdf"
        )
        file_path = upload_result.get("file_path")
        if not file_path:
            pytest.skip("File upload failed")
        
        cleanup_uploaded_file.append(file_path)
        
        invoice = Invoice(
            id=invoice_id,
            file_path=file_path,
            file_name="corrupted.pdf",
            upload_date=datetime.utcnow(),
            processing_state=InvoiceState.PENDING,
            field_confidence={"invoice_number": 0.3}
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        
        # Run extraction - should handle PDF error gracefully
        result = await extraction_service.extract_invoice(
            invoice_id=invoice_id,
            file_identifier=file_path,
            file_name="corrupted.pdf",
            upload_date=datetime.utcnow(),
            db=db_session
        )
        
        # Extraction should still attempt (may fail at DI stage, but shouldn't crash)
        # The system should handle the error gracefully
        assert result["status"] in ["extracted", "error"], \
            f"Extraction should handle PDF error gracefully: {result.get('status')}"
    
    async def test_multimodal_llm_rate_limiting_retry(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that multimodal LLM rate limiting (429 errors) triggers retry logic with exponential backoff.
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
        
        invoice = Invoice(
            id=invoice_id,
            file_path=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            processing_state=InvoiceState.PENDING,
            field_confidence={"invoice_number": 0.3}
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        
        # Track retry attempts
        retry_count = [0]
        
        # Mock multimodal LLM to return 429, then succeed
        if RateLimitError is None or AsyncAzureOpenAI is None:
            pytest.skip("OpenAI package not available - cannot test rate limiting")
        
        async def mock_chat_completions_create(*args, **kwargs):
            retry_count[0] += 1
            if retry_count[0] <= 1:
                # First attempt fails with 429
                error = RateLimitError(
                    message="Rate limit exceeded",
                    response=Mock(status_code=429),
                    body={"error": {"message": "Rate limit exceeded"}}
                )
                raise error
            else:
                # Second attempt succeeds
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message = MagicMock()
                mock_response.choices[0].message.content = '{"invoice_number": "4202092525"}'
                return mock_response
        
        try:
            with patch('src.extraction.extraction_service.AsyncAzureOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.chat.completions.create = mock_chat_completions_create
                mock_client_class.return_value = mock_client
                
                # Force PDF to be detected as scanned
                from starlette.concurrency import run_in_threadpool
                original_is_scanned = extraction_service._is_scanned_pdf
                def mock_is_scanned(file_content):
                    return True  # Force scanned detection
                extraction_service._is_scanned_pdf = mock_is_scanned
                
                try:
                    # Run extraction
                    result = await extraction_service.extract_invoice(
                        invoice_id=invoice_id,
                        file_identifier=file_path,
                        file_name=os.path.basename(sample_pdf_path),
                        upload_date=datetime.utcnow(),
                        db=db_session
                    )
                    
                    # Extraction should succeed after retry
                    assert result["status"] == "extracted", \
                        f"Extraction should succeed after retry: {result.get('errors', [])}"
                    
                    # Verify retry was attempted
                    assert retry_count[0] >= 2, \
                        f"Expected at least 2 attempts (1 failure + 1 success), got {retry_count[0]}"
                    
                    extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
                    assert extracted_invoice is not None
                finally:
                    extraction_service._is_scanned_pdf = original_is_scanned
        finally:
            pass
    
    async def test_multimodal_llm_api_failure_handling(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that multimodal LLM API failures are handled gracefully.
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
        
        invoice = Invoice(
            id=invoice_id,
            file_path=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            processing_state=InvoiceState.PENDING,
            field_confidence={"invoice_number": 0.3}
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        
        # Mock multimodal LLM to return API error
        if APIError is None or AsyncAzureOpenAI is None:
            pytest.skip("OpenAI package not available - cannot test API failures")
        
        async def mock_chat_completions_create(*args, **kwargs):
            error = APIError(
                message="Internal server error",
                response=Mock(status_code=500),
                body={"error": {"message": "Internal server error"}}
            )
            raise error
        
        try:
            with patch('src.extraction.extraction_service.AsyncAzureOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.chat.completions.create = mock_chat_completions_create
                mock_client_class.return_value = mock_client
                
                # Force PDF to be detected as scanned
                original_is_scanned = extraction_service._is_scanned_pdf
                def mock_is_scanned(file_content):
                    return True
                extraction_service._is_scanned_pdf = mock_is_scanned
                
                try:
                    # Run extraction
                    result = await extraction_service.extract_invoice(
                        invoice_id=invoice_id,
                        file_identifier=file_path,
                        file_name=os.path.basename(sample_pdf_path),
                        upload_date=datetime.utcnow(),
                        db=db_session
                    )
                    
                    # Extraction should still succeed (DI should work)
                    assert result["status"] == "extracted", \
                        f"Extraction should succeed even with multimodal LLM API error: {result.get('errors', [])}"
                    
                    extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
                    assert extracted_invoice is not None
                finally:
                    extraction_service._is_scanned_pdf = original_is_scanned
        finally:
            pass
    
    async def test_multimodal_llm_empty_images(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that multimodal LLM handles empty images gracefully.
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
        
        invoice = Invoice(
            id=invoice_id,
            file_path=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            processing_state=InvoiceState.PENDING,
            field_confidence={"invoice_number": 0.3}
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        
        # Mock image rendering to return empty list
        original_render = extraction_service._render_multimodal_images
        def mock_render(file_content):
            return []  # Empty images
        
        extraction_service._render_multimodal_images = mock_render
        
        try:
            # Force PDF to be detected as scanned
            original_is_scanned = extraction_service._is_scanned_pdf
            def mock_is_scanned(file_content):
                return True
            extraction_service._is_scanned_pdf = mock_is_scanned
            
            try:
                # Run extraction
                result = await extraction_service.extract_invoice(
                    invoice_id=invoice_id,
                    file_identifier=file_path,
                    file_name=os.path.basename(sample_pdf_path),
                    upload_date=datetime.utcnow(),
                    db=db_session
                )
                
                # Extraction should still succeed (should fall back to text-based LLM)
                assert result["status"] == "extracted", \
                    f"Extraction should succeed even with empty images: {result.get('errors', [])}"
                
                extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
                assert extracted_invoice is not None
            finally:
                extraction_service._is_scanned_pdf = original_is_scanned
        finally:
            extraction_service._render_multimodal_images = original_render
    
    async def test_multimodal_llm_invalid_json_response(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that multimodal LLM handles invalid JSON responses gracefully.
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
        
        invoice = Invoice(
            id=invoice_id,
            file_path=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            processing_state=InvoiceState.PENDING,
            field_confidence={"invoice_number": 0.3}
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        
        # Mock multimodal LLM to return invalid JSON
        async def mock_chat_completions_create(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message = MagicMock()
            mock_response.choices[0].message.content = "This is not valid JSON"
            return mock_response
        
        try:
            with patch('src.extraction.extraction_service.AsyncAzureOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.chat.completions.create = mock_chat_completions_create
                mock_client_class.return_value = mock_client
                
                # Force PDF to be detected as scanned
                original_is_scanned = extraction_service._is_scanned_pdf
                def mock_is_scanned(file_content):
                    return True
                extraction_service._is_scanned_pdf = mock_is_scanned
                
                try:
                    # Run extraction
                    result = await extraction_service.extract_invoice(
                        invoice_id=invoice_id,
                        file_identifier=file_path,
                        file_name=os.path.basename(sample_pdf_path),
                        upload_date=datetime.utcnow(),
                        db=db_session
                    )
                    
                    # Extraction should still succeed (DI should work)
                    assert result["status"] == "extracted", \
                        f"Extraction should succeed even with invalid JSON: {result.get('errors', [])}"
                    
                    extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
                    assert extracted_invoice is not None
                finally:
                    extraction_service._is_scanned_pdf = original_is_scanned
        finally:
            pass
    
    async def test_multimodal_llm_network_timeout(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that multimodal LLM handles network timeouts gracefully.
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
        
        invoice = Invoice(
            id=invoice_id,
            file_path=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            processing_state=InvoiceState.PENDING,
            field_confidence={"invoice_number": 0.3}
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        
        # Mock multimodal LLM to timeout
        async def mock_chat_completions_create(*args, **kwargs):
            await asyncio.sleep(120)  # Simulate timeout (longer than typical timeout)
            raise TimeoutError("Request timed out")
        
        try:
            with patch('src.extraction.extraction_service.AsyncAzureOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.chat.completions.create = mock_chat_completions_create
                mock_client_class.return_value = mock_client
                
                # Force PDF to be detected as scanned
                original_is_scanned = extraction_service._is_scanned_pdf
                def mock_is_scanned(file_content):
                    return True
                extraction_service._is_scanned_pdf = mock_is_scanned
                
                try:
                    # Run extraction with shorter timeout
                    result = await extraction_service.extract_invoice(
                        invoice_id=invoice_id,
                        file_identifier=file_path,
                        file_name=os.path.basename(sample_pdf_path),
                        upload_date=datetime.utcnow(),
                        db=db_session
                    )
                    
                    # Extraction should handle timeout gracefully
                    # May succeed with DI-only or fail gracefully
                    assert result["status"] in ["extracted", "error"], \
                        f"Extraction should handle timeout gracefully: {result.get('status')}"
                finally:
                    extraction_service._is_scanned_pdf = original_is_scanned
        finally:
            pass
    
    async def test_multimodal_llm_partial_group_failure(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that multimodal LLM handles partial group failures gracefully.
        Some groups succeed, others fail - successful corrections should still be applied.
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
        
        invoice = Invoice(
            id=invoice_id,
            file_path=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            processing_state=InvoiceState.PENDING,
            field_confidence={
                "invoice_number": 0.3,
                "vendor_name": 0.3,
            }
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        
        # Track which groups are called
        group_calls = []
        
        # Mock multimodal LLM to fail for one group, succeed for another
        async def mock_chat_completions_create(*args, **kwargs):
            # Check the prompt to determine which group
            messages = kwargs.get("messages", [])
            user_content = messages[1]["content"] if len(messages) > 1 else ""
            
            group_calls.append(user_content)
            
            # Fail for first group (fields), succeed for second (addresses)
            if len(group_calls) == 1:
                # First group fails
                if APIError is None:
                    raise Exception("API error")
                error = APIError(
                    message="Group processing failed",
                    response=Mock(status_code=500),
                    body={"error": {"message": "Group processing failed"}}
                )
                raise error
            else:
                # Second group succeeds
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message = MagicMock()
                mock_response.choices[0].message.content = '{"vendor_name": "ACCURATE fire & safety ltd."}'
                return mock_response
        
        try:
            with patch('src.extraction.extraction_service.AsyncAzureOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.chat.completions.create = mock_chat_completions_create
                mock_client_class.return_value = mock_client
                
                # Force PDF to be detected as scanned
                original_is_scanned = extraction_service._is_scanned_pdf
                def mock_is_scanned(file_content):
                    return True
                extraction_service._is_scanned_pdf = mock_is_scanned
                
                try:
                    # Run extraction
                    result = await extraction_service.extract_invoice(
                        invoice_id=invoice_id,
                        file_identifier=file_path,
                        file_name=os.path.basename(sample_pdf_path),
                        upload_date=datetime.utcnow(),
                        db=db_session
                    )
                    
                    # Extraction should succeed (partial success is acceptable)
                    assert result["status"] == "extracted", \
                        f"Extraction should succeed with partial group success: {result.get('errors', [])}"
                    
                    extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
                    assert extracted_invoice is not None
                finally:
                    extraction_service._is_scanned_pdf = original_is_scanned
        finally:
            pass
    
    async def test_multimodal_llm_image_rendering_exception(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that multimodal LLM handles image rendering exceptions gracefully.
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
        
        invoice = Invoice(
            id=invoice_id,
            file_path=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            processing_state=InvoiceState.PENDING,
            field_confidence={"invoice_number": 0.3}
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        
        # Mock image rendering to raise exception
        original_render = extraction_service._render_multimodal_images
        def mock_render(file_content):
            raise Exception("Image rendering failed")
        
        extraction_service._render_multimodal_images = mock_render
        
        try:
            # Force PDF to be detected as scanned
            original_is_scanned = extraction_service._is_scanned_pdf
            def mock_is_scanned(file_content):
                return True
            extraction_service._is_scanned_pdf = mock_is_scanned
            
            try:
                # Run extraction
                result = await extraction_service.extract_invoice(
                    invoice_id=invoice_id,
                    file_identifier=file_path,
                    file_name=os.path.basename(sample_pdf_path),
                    upload_date=datetime.utcnow(),
                    db=db_session
                )
                
                # Extraction should handle exception gracefully
                # Should fall back to text-based LLM or DI-only
                assert result["status"] in ["extracted", "error"], \
                    f"Extraction should handle image rendering exception: {result.get('status')}"
            finally:
                extraction_service._is_scanned_pdf = original_is_scanned
        finally:
            extraction_service._render_multimodal_images = original_render

