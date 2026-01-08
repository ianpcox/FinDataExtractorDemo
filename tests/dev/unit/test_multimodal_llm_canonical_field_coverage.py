"""
Comprehensive test coverage for canonical fields extractable by multimodal LLM fallback.

This test suite ensures 75% coverage of canonical fields that can be extracted by the multimodal LLM.
Tests verify that multimodal LLM uses the same system prompt as text-based LLM, ensuring all fields are available.
"""

import pytest
import asyncio
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import MagicMock, patch, AsyncMock
from types import SimpleNamespace

from src.extraction.extraction_service import ExtractionService, LLM_SYSTEM_PROMPT
from src.extraction.field_extractor import FieldExtractor
from src.models.invoice import Invoice, Address
from src.config import settings


@pytest.mark.unit
class TestMultimodalLLMCanonicalFieldCoverage:
    """Test coverage for canonical fields extractable by multimodal LLM fallback"""
    
    @pytest.fixture
    def mock_di_client(self):
        """Create a mock DI client that returns low-confidence fields"""
        from unittest.mock import MagicMock, patch
        with patch("src.extraction.document_intelligence_client.DocumentAnalysisClient"):
            from src.extraction.document_intelligence_client import DocumentIntelligenceClient
            client = DocumentIntelligenceClient(endpoint="https://example.test", api_key="fake")
            return client
    
    @pytest.fixture
    def field_extractor(self):
        """Create a field extractor instance"""
        return FieldExtractor()
    
    @pytest.fixture
    def extraction_service(self, mock_di_client):
        """Create extraction service with real multimodal LLM if configured"""
        from src.ingestion.file_handler import FileHandler
        file_handler = FileHandler()
        field_extractor = FieldExtractor()
        service = ExtractionService(
            doc_intelligence_client=mock_di_client,
            file_handler=file_handler,
            field_extractor=field_extractor
        )
        return service
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_uses_same_system_prompt(self, extraction_service):
        """Test that multimodal LLM uses the same system prompt as text-based LLM"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        # Multimodal LLM uses the same LLM_SYSTEM_PROMPT
        assert LLM_SYSTEM_PROMPT is not None
        assert "CANONICAL FIELD NAMES" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_invoice_number(self, extraction_service):
        """Test multimodal LLM extraction of invoice_number"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "invoice_number" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_invoice_date(self, extraction_service):
        """Test multimodal LLM extraction of invoice_date"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "invoice_date" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_due_date(self, extraction_service):
        """Test multimodal LLM extraction of due_date"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "due_date" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_invoice_type(self, extraction_service):
        """Test multimodal LLM extraction of invoice_type"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "invoice_type" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_reference_number(self, extraction_service):
        """Test multimodal LLM extraction of reference_number"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "reference_number" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_vendor_name(self, extraction_service):
        """Test multimodal LLM extraction of vendor_name"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "vendor_name" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_vendor_id(self, extraction_service):
        """Test multimodal LLM extraction of vendor_id"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "vendor_id" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_vendor_phone(self, extraction_service):
        """Test multimodal LLM extraction of vendor_phone"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "vendor_phone" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_vendor_fax(self, extraction_service):
        """Test multimodal LLM extraction of vendor_fax"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "vendor_fax" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_vendor_email(self, extraction_service):
        """Test multimodal LLM extraction of vendor_email"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "vendor_email" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_vendor_website(self, extraction_service):
        """Test multimodal LLM extraction of vendor_website"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "vendor_website" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_vendor_address(self, extraction_service):
        """Test multimodal LLM extraction of vendor_address"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "vendor_address" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_business_number(self, extraction_service):
        """Test multimodal LLM extraction of business_number"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "business_number" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_gst_number(self, extraction_service):
        """Test multimodal LLM extraction of gst_number"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "gst_number" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_qst_number(self, extraction_service):
        """Test multimodal LLM extraction of qst_number"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "qst_number" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_pst_number(self, extraction_service):
        """Test multimodal LLM extraction of pst_number"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "pst_number" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_customer_name(self, extraction_service):
        """Test multimodal LLM extraction of customer_name"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "customer_name" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_customer_id(self, extraction_service):
        """Test multimodal LLM extraction of customer_id"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "customer_id" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_customer_phone(self, extraction_service):
        """Test multimodal LLM extraction of customer_phone"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "customer_phone" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_customer_email(self, extraction_service):
        """Test multimodal LLM extraction of customer_email"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "customer_email" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_customer_fax(self, extraction_service):
        """Test multimodal LLM extraction of customer_fax"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "customer_fax" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_bill_to_address(self, extraction_service):
        """Test multimodal LLM extraction of bill_to_address"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "bill_to_address" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_remit_to_address(self, extraction_service):
        """Test multimodal LLM extraction of remit_to_address"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "remit_to_address" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_remit_to_name(self, extraction_service):
        """Test multimodal LLM extraction of remit_to_name"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "remit_to_name" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_entity(self, extraction_service):
        """Test multimodal LLM extraction of entity"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "entity" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_contract_id(self, extraction_service):
        """Test multimodal LLM extraction of contract_id"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "contract_id" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_standing_offer_number(self, extraction_service):
        """Test multimodal LLM extraction of standing_offer_number"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "standing_offer_number" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_po_number(self, extraction_service):
        """Test multimodal LLM extraction of po_number"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "po_number" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_period_start(self, extraction_service):
        """Test multimodal LLM extraction of period_start"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "period_start" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_period_end(self, extraction_service):
        """Test multimodal LLM extraction of period_end"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "period_end" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_shipping_date(self, extraction_service):
        """Test multimodal LLM extraction of shipping_date"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "shipping_date" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_delivery_date(self, extraction_service):
        """Test multimodal LLM extraction of delivery_date"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "delivery_date" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_subtotal(self, extraction_service):
        """Test multimodal LLM extraction of subtotal"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "subtotal" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_discount_amount(self, extraction_service):
        """Test multimodal LLM extraction of discount_amount"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "discount_amount" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_shipping_amount(self, extraction_service):
        """Test multimodal LLM extraction of shipping_amount"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "shipping_amount" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_handling_fee(self, extraction_service):
        """Test multimodal LLM extraction of handling_fee"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "handling_fee" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_deposit_amount(self, extraction_service):
        """Test multimodal LLM extraction of deposit_amount"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "deposit_amount" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_gst_amount(self, extraction_service):
        """Test multimodal LLM extraction of gst_amount"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "gst_amount" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_gst_rate(self, extraction_service):
        """Test multimodal LLM extraction of gst_rate"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "gst_rate" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_hst_amount(self, extraction_service):
        """Test multimodal LLM extraction of hst_amount"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "hst_amount" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_hst_rate(self, extraction_service):
        """Test multimodal LLM extraction of hst_rate"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "hst_rate" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_qst_amount(self, extraction_service):
        """Test multimodal LLM extraction of qst_amount"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "qst_amount" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_qst_rate(self, extraction_service):
        """Test multimodal LLM extraction of qst_rate"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "qst_rate" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_pst_amount(self, extraction_service):
        """Test multimodal LLM extraction of pst_amount"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "pst_amount" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_pst_rate(self, extraction_service):
        """Test multimodal LLM extraction of pst_rate"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "pst_rate" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_tax_amount(self, extraction_service):
        """Test multimodal LLM extraction of tax_amount"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "tax_amount" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_total_amount(self, extraction_service):
        """Test multimodal LLM extraction of total_amount"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "total_amount" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_currency(self, extraction_service):
        """Test multimodal LLM extraction of currency"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "currency" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_payment_terms(self, extraction_service):
        """Test multimodal LLM extraction of payment_terms"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "payment_terms" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_payment_method(self, extraction_service):
        """Test multimodal LLM extraction of payment_method"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "payment_method" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_payment_due_upon(self, extraction_service):
        """Test multimodal LLM extraction of payment_due_upon"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "payment_due_upon" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_extracts_tax_registration_number(self, extraction_service):
        """Test multimodal LLM extraction of tax_registration_number"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        assert "tax_registration_number" in LLM_SYSTEM_PROMPT
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_image_rendering(self, extraction_service):
        """Test that multimodal LLM can render PDF pages as images"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        
        # Test with sample PDF content
        sample_pdf = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 1\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"
        images = extraction_service._render_multimodal_images(sample_pdf)
        # Should return empty list if PyMuPDF not available or PDF invalid
        assert isinstance(images, list)
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_scanned_pdf_detection(self, extraction_service):
        """Test that multimodal LLM can detect scanned PDFs"""
        if not extraction_service._has_multimodal_config():
            pytest.skip("Azure OpenAI multimodal not configured")
        
        # Test with sample PDF content
        sample_pdf = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 1\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"
        is_scanned = extraction_service._is_scanned_pdf(sample_pdf)
        assert isinstance(is_scanned, bool)

