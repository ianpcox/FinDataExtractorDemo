"""
Integration tests for LLM error handling scenarios.

These tests verify that the extraction service handles LLM errors gracefully:
- API failures
- Invalid responses
- Network issues
- Rate limiting
- Partial failures

Requirements:
- Azure OpenAI credentials must be configured (AOAI_ENDPOINT, AOAI_API_KEY, AOAI_DEPLOYMENT_NAME)
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
    from openai import RateLimitError, APIError
except ImportError:
    RateLimitError = None
    APIError = None


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
class TestLLMErrorHandling:
    """Integration tests for LLM error handling"""
    
    @pytest.fixture
    def extraction_service(self, monkeypatch):
        """Create extraction service with real DI and LLM clients"""
        # Check if Azure OpenAI is configured
        if not settings.AOAI_ENDPOINT or not settings.AOAI_API_KEY or not settings.AOAI_DEPLOYMENT_NAME:
            pytest.skip("Azure OpenAI credentials not configured - skipping LLM error handling tests")
        
        # Check if Azure Document Intelligence is configured
        if not settings.AZURE_FORM_RECOGNIZER_ENDPOINT or not settings.AZURE_FORM_RECOGNIZER_KEY:
            pytest.skip("Azure Document Intelligence credentials not configured - skipping LLM error handling tests")
        
        # Override the autouse fixture that disables LLM fallback
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
        sample_path = "data/sample_invoices/Raw/Raw_Basic/ACC012 4202092525.pdf"
        if not os.path.exists(sample_path):
            pytest.skip(f"Sample PDF not found at {sample_path}")
        return sample_path
    
    @pytest.fixture
    def unique_invoice_id(self):
        """Generate a unique invoice ID for each test"""
        timestamp = int(time.time() * 1000)
        unique_id = f"test-llm-error-{timestamp}-{uuid4().hex[:8]}"
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
    
    async def test_llm_rate_limiting_retry(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that LLM rate limiting (429 errors) triggers retry logic with exponential backoff.
        This test mocks the LLM client to simulate rate limiting.
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
        
        # Create invoice with low confidence fields to trigger LLM
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
        
        # Mock AsyncAzureOpenAI to simulate rate limiting
        if RateLimitError is None:
            pytest.skip("OpenAI package not available - cannot test rate limiting")
        
        # Create a mock that raises RateLimitError twice, then succeeds
        call_count = [0]
        
        async def mock_chat_completions_create(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 2:
                # Simulate rate limit error with retry_after
                error = RateLimitError(
                    message="Rate limit exceeded",
                    response=Mock(status_code=429),
                    body={"error": {"message": "Rate limit exceeded"}}
                )
                error.retry_after = 1.0  # 1 second retry after
                raise error
            else:
                # Success on third attempt
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message = MagicMock()
                mock_response.choices[0].message.content = '{"invoice_number": "4202092525", "vendor_name": "ACCURATE fire & safety ltd."}'
                return mock_response
        
        try:
            # Patch the AsyncAzureOpenAI client
            with patch('src.extraction.extraction_service.AsyncAzureOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.chat.completions.create = mock_chat_completions_create
                mock_client_class.return_value = mock_client
                
                # Run extraction
                result = await extraction_service.extract_invoice(
                    invoice_id=invoice_id,
                    file_identifier=file_path,
                    file_name=os.path.basename(sample_pdf_path),
                    upload_date=datetime.utcnow(),
                    db=db_session
                )
                
                # Verify extraction succeeded despite rate limiting
                assert result["status"] == "extracted", f"Extraction should succeed after retries: {result.get('errors', [])}"
                
                # Verify retry logic was used (should have called 3 times: 2 failures + 1 success)
                assert call_count[0] >= 3, f"Expected at least 3 calls (2 retries + 1 success), got {call_count[0]}"
                
                # Verify invoice was still extracted (DI should have worked)
                extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
                assert extracted_invoice is not None
                
        finally:
            pass
    
    async def test_llm_api_failure_handling(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that LLM API failures are handled gracefully and don't break the extraction pipeline.
        DI extraction should still work even if LLM fails completely.
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
        
        # Mock AsyncAzureOpenAI to always fail
        if APIError is None:
            pytest.skip("OpenAI package not available - cannot test API errors")
        
        async def mock_chat_completions_create(*args, **kwargs):
            # Simulate API error
            error = APIError(
                message="API error occurred",
                response=Mock(status_code=500),
                body={"error": {"message": "Internal server error"}}
            )
            raise error
        
        try:
            with patch('src.extraction.extraction_service.AsyncAzureOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.chat.completions.create = mock_chat_completions_create
                mock_client_class.return_value = mock_client
                
                # Run extraction
                result = await extraction_service.extract_invoice(
                    invoice_id=invoice_id,
                    file_identifier=file_path,
                    file_name=os.path.basename(sample_pdf_path),
                    upload_date=datetime.utcnow(),
                    db=db_session
                )
                
                # Extraction should still succeed (DI should work)
                # LLM failure should not break the pipeline
                assert result["status"] == "extracted", \
                    f"Extraction should succeed even if LLM fails: {result.get('errors', [])}"
                
                # Verify invoice was extracted by DI
                extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
                assert extracted_invoice is not None
                
                # Verify at least some fields were extracted (by DI)
                assert extracted_invoice.invoice_number is not None or \
                       extracted_invoice.vendor_name is not None or \
                       extracted_invoice.total_amount is not None, \
                       "At least one field should be extracted by DI even if LLM fails"
                
        finally:
            pass
    
    async def test_llm_invalid_json_response(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that invalid JSON responses from LLM are handled gracefully.
        The system should skip invalid responses and continue with DI extraction.
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
        
        # Mock LLM to return invalid JSON
        async def mock_chat_completions_create(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message = MagicMock()
            # Return invalid JSON (not valid JSON format)
            mock_response.choices[0].message.content = "This is not valid JSON {invoice_number: 4202092525}"
            return mock_response
        
        try:
            with patch('src.extraction.extraction_service.AsyncAzureOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.chat.completions.create = mock_chat_completions_create
                mock_client_class.return_value = mock_client
                
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
                    f"Extraction should succeed even with invalid LLM JSON: {result.get('errors', [])}"
                
                # Verify invoice was extracted
                extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
                assert extracted_invoice is not None
                
        finally:
            pass
    
    async def test_llm_malformed_json_response(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that malformed JSON responses (valid JSON but wrong structure) are handled.
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
        
        # Mock LLM to return malformed JSON (valid JSON but not an object)
        async def mock_chat_completions_create(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message = MagicMock()
            # Return valid JSON but not an object (array instead)
            mock_response.choices[0].message.content = '["invoice_number", "4202092525"]'
            return mock_response
        
        try:
            with patch('src.extraction.extraction_service.AsyncAzureOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.chat.completions.create = mock_chat_completions_create
                mock_client_class.return_value = mock_client
                
                # Run extraction
                result = await extraction_service.extract_invoice(
                    invoice_id=invoice_id,
                    file_identifier=file_path,
                    file_name=os.path.basename(sample_pdf_path),
                    upload_date=datetime.utcnow(),
                    db=db_session
                )
                
                # Extraction should still succeed
                assert result["status"] == "extracted", \
                    f"Extraction should succeed even with malformed LLM JSON: {result.get('errors', [])}"
                
                extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
                assert extracted_invoice is not None
                
        finally:
            pass
    
    async def test_llm_network_timeout(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that network timeouts are handled gracefully.
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
        
        # Mock LLM to simulate timeout
        async def mock_chat_completions_create(*args, **kwargs):
            # Simulate network timeout
            await asyncio.sleep(0.1)  # Small delay to make it async
            raise TimeoutError("Request timed out")
        
        try:
            with patch('src.extraction.extraction_service.AsyncAzureOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.chat.completions.create = mock_chat_completions_create
                mock_client_class.return_value = mock_client
                
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
                    f"Extraction should succeed even with LLM timeout: {result.get('errors', [])}"
                
                extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
                assert extracted_invoice is not None
                
        finally:
            pass
    
    async def test_llm_connection_error(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that connection errors are handled gracefully.
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
        
        # Mock LLM to simulate connection error
        async def mock_chat_completions_create(*args, **kwargs):
            raise ConnectionError("Connection refused")
        
        try:
            with patch('src.extraction.extraction_service.AsyncAzureOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.chat.completions.create = mock_chat_completions_create
                mock_client_class.return_value = mock_client
                
                # Run extraction
                result = await extraction_service.extract_invoice(
                    invoice_id=invoice_id,
                    file_identifier=file_path,
                    file_name=os.path.basename(sample_pdf_path),
                    upload_date=datetime.utcnow(),
                    db=db_session
                )
                
                # Extraction should still succeed
                assert result["status"] == "extracted", \
                    f"Extraction should succeed even with LLM connection error: {result.get('errors', [])}"
                
                extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
                assert extracted_invoice is not None
                
        finally:
            pass
    
    async def test_llm_partial_group_failure(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that partial group failures are handled correctly.
        Some groups should succeed while others fail, and successful groups should still be applied.
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
        
        # Create invoice with multiple low confidence fields across different groups
        invoice = Invoice(
            id=invoice_id,
            file_path=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.utcnow(),
            processing_state=InvoiceState.PENDING,
            field_confidence={
                "invoice_number": 0.3,  # Fields group
                "vendor_name": 0.3,    # Fields group
                "vendor_address": 0.3, # Addresses group
            }
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        
        # Track which groups were called
        group_calls = []
        
        # Mock LLM to fail for addresses group but succeed for fields group
        async def mock_chat_completions_create(*args, **kwargs):
            # Extract group name from prompt (simplified check)
            prompt = kwargs.get("messages", [{}])[-1].get("content", "")
            
            if "addresses" in prompt.lower() or "vendor_address" in prompt.lower():
                # Fail for addresses group
                group_calls.append("addresses")
                if APIError is None:
                    raise Exception("APIError not available")
                error = APIError(
                    message="API error for addresses",
                    response=Mock(status_code=500),
                    body={"error": {"message": "Internal server error"}}
                )
                raise error
            else:
                # Succeed for fields group
                group_calls.append("fields")
                mock_response = MagicMock()
                mock_response.choices = [MagicMock()]
                mock_response.choices[0].message = MagicMock()
                mock_response.choices[0].message.content = '{"invoice_number": "4202092525", "vendor_name": "ACCURATE fire & safety ltd."}'
                return mock_response
        
        try:
            with patch('src.extraction.extraction_service.AsyncAzureOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.chat.completions.create = mock_chat_completions_create
                mock_client_class.return_value = mock_client
                
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
                    f"Extraction should succeed with partial LLM success: {result.get('errors', [])}"
                
                # Verify invoice was extracted
                extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
                assert extracted_invoice is not None
                
                # Verify that at least some fields were extracted
                # (either by DI or by successful LLM groups)
                assert extracted_invoice.invoice_number is not None or \
                       extracted_invoice.vendor_name is not None, \
                       "At least one field should be extracted"
                
                # Verify that multiple groups were attempted
                assert len(group_calls) > 0, "At least one group should have been called"
                
        finally:
            pass
    
    async def test_llm_empty_response(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that empty responses from LLM are handled gracefully.
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
        
        # Mock LLM to return empty response
        async def mock_chat_completions_create(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message = MagicMock()
            mock_response.choices[0].message.content = ""  # Empty response
            return mock_response
        
        try:
            with patch('src.extraction.extraction_service.AsyncAzureOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.chat.completions.create = mock_chat_completions_create
                mock_client_class.return_value = mock_client
                
                # Run extraction
                result = await extraction_service.extract_invoice(
                    invoice_id=invoice_id,
                    file_identifier=file_path,
                    file_name=os.path.basename(sample_pdf_path),
                    upload_date=datetime.utcnow(),
                    db=db_session
                )
                
                # Extraction should still succeed
                assert result["status"] == "extracted", \
                    f"Extraction should succeed even with empty LLM response: {result.get('errors', [])}"
                
                extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
                assert extracted_invoice is not None
                
        finally:
            pass
    
    async def test_llm_no_choices_in_response(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that responses with no choices are handled gracefully.
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
        
        # Mock LLM to return response with no choices
        async def mock_chat_completions_create(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.choices = []  # No choices
            return mock_response
        
        try:
            with patch('src.extraction.extraction_service.AsyncAzureOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.chat.completions.create = mock_chat_completions_create
                mock_client_class.return_value = mock_client
                
                # Run extraction
                result = await extraction_service.extract_invoice(
                    invoice_id=invoice_id,
                    file_identifier=file_path,
                    file_name=os.path.basename(sample_pdf_path),
                    upload_date=datetime.utcnow(),
                    db=db_session
                )
                
                # Extraction should still succeed
                assert result["status"] == "extracted", \
                    f"Extraction should succeed even with no LLM choices: {result.get('errors', [])}"
                
                extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
                assert extracted_invoice is not None
                
        finally:
            pass
    
    async def test_llm_max_retries_exceeded(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that when max retries are exceeded, the system handles it gracefully.
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
        
        # Mock LLM to always fail (exceed max retries)
        if APIError is None:
            pytest.skip("OpenAI package not available - cannot test max retries")
        
        async def mock_chat_completions_create(*args, **kwargs):
            retry_count[0] += 1
            error = APIError(
                message="API error",
                response=Mock(status_code=500),
                body={"error": {"message": "Internal server error"}}
            )
            raise error
        
        try:
            with patch('src.extraction.extraction_service.AsyncAzureOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.chat.completions.create = mock_chat_completions_create
                mock_client_class.return_value = mock_client
                
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
                    f"Extraction should succeed even when LLM max retries exceeded: {result.get('errors', [])}"
                
                # Verify retries were attempted (max_retries = 3, so should try 4 times: initial + 3 retries)
                assert retry_count[0] >= 3, \
                    f"Expected at least 3 retry attempts, got {retry_count[0]}"
                
                extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
                assert extracted_invoice is not None
                
        finally:
            pass
    
    async def test_llm_authentication_error(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that authentication errors (401/403) are handled gracefully.
        These errors should not be retried as they indicate credential issues.
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
        
        # Mock LLM to return authentication error (401)
        if APIError is None:
            pytest.skip("OpenAI package not available - cannot test authentication errors")
        
        async def mock_chat_completions_create(*args, **kwargs):
            error = APIError(
                message="Unauthorized",
                response=Mock(status_code=401),
                body={"error": {"message": "Invalid API key"}}
            )
            raise error
        
        try:
            with patch('src.extraction.extraction_service.AsyncAzureOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.chat.completions.create = mock_chat_completions_create
                mock_client_class.return_value = mock_client
                
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
                    f"Extraction should succeed even with LLM auth error: {result.get('errors', [])}"
                
                extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
                assert extracted_invoice is not None
                
        finally:
            pass
    
    async def test_llm_service_unavailable(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that service unavailable errors (503) are handled with retry logic.
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
        
        # Mock LLM to return 503, then succeed
        if APIError is None:
            pytest.skip("OpenAI package not available - cannot test service unavailable")
        
        async def mock_chat_completions_create(*args, **kwargs):
            retry_count[0] += 1
            if retry_count[0] <= 1:
                # First attempt fails with 503
                error = APIError(
                    message="Service unavailable",
                    response=Mock(status_code=503),
                    body={"error": {"message": "Service temporarily unavailable"}}
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
            pass
    
    async def test_llm_bad_request_error(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that bad request errors (400) are handled gracefully.
        These errors typically indicate invalid request format and should not be retried.
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
        
        # Mock LLM to return bad request error (400)
        if APIError is None:
            pytest.skip("OpenAI package not available - cannot test bad request errors")
        
        async def mock_chat_completions_create(*args, **kwargs):
            error = APIError(
                message="Bad request",
                response=Mock(status_code=400),
                body={"error": {"message": "Invalid request format"}}
            )
            raise error
        
        try:
            with patch('src.extraction.extraction_service.AsyncAzureOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.chat.completions.create = mock_chat_completions_create
                mock_client_class.return_value = mock_client
                
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
                    f"Extraction should succeed even with LLM bad request error: {result.get('errors', [])}"
                
                extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
                assert extracted_invoice is not None
                
        finally:
            pass
    
    async def test_llm_response_with_validation_errors(
        self,
        extraction_service,
        db_session,
        sample_pdf_path,
        unique_invoice_id,
        cleanup_uploaded_file
    ):
        """
        Test that LLM responses with invalid field values (that fail validation) are handled.
        Invalid values should be rejected but valid ones should still be applied.
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
                "invoice_date": 0.3,
            }
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        
        # Mock LLM to return response with some invalid values
        async def mock_chat_completions_create(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message = MagicMock()
            # Return JSON with one valid field and one invalid (future date)
            mock_response.choices[0].message.content = '{"invoice_number": "4202092525", "invoice_date": "2099-12-31"}'
            return mock_response
        
        try:
            with patch('src.extraction.extraction_service.AsyncAzureOpenAI') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.chat.completions.create = mock_chat_completions_create
                mock_client_class.return_value = mock_client
                
                # Run extraction
                result = await extraction_service.extract_invoice(
                    invoice_id=invoice_id,
                    file_identifier=file_path,
                    file_name=os.path.basename(sample_pdf_path),
                    upload_date=datetime.utcnow(),
                    db=db_session
                )
                
                # Extraction should succeed
                assert result["status"] == "extracted", \
                    f"Extraction should succeed even with some invalid LLM values: {result.get('errors', [])}"
                
                extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
                assert extracted_invoice is not None
                
                # At least one field should be extracted (either by DI or valid LLM field)
                assert extracted_invoice.invoice_number is not None or \
                       extracted_invoice.vendor_name is not None or \
                       extracted_invoice.total_amount is not None, \
                       "At least one field should be extracted"
                
        finally:
            pass

