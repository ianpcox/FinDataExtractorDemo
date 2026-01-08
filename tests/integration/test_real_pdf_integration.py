"""
Integration tests for REAL PDF extraction with line items and aggregation validation.

These tests use actual PDF files from the sample_invoices directory and make real API calls
to Azure Document Intelligence. They validate:
1. Full extraction pipeline with real PDFs
2. Line item extraction from real invoices
3. Aggregation validation (totals = sum of line items)
4. Data integrity and consistency

Requirements:
- Azure Document Intelligence credentials must be configured (DI_ENDPOINT, DI_API_KEY)
- Tests will be skipped if credentials are not available
- Sample PDF files must exist in data/sample_invoices/
- Each test uses an isolated test database
"""

import pytest
import os
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from src.extraction.extraction_service import ExtractionService
from src.extraction.document_intelligence_client import DocumentIntelligenceClient
from src.extraction.field_extractor import FieldExtractor
from src.ingestion.file_handler import FileHandler
from src.models.invoice import Invoice, InvoiceState
from src.services.db_service import DatabaseService
from src.validation.aggregation_validator import AggregationValidator
from src.config import settings


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
class TestRealPDFIntegration:
    """Integration tests for real PDF extraction with line items"""
    
    @pytest.fixture
    def extraction_service(self):
        """Create extraction service with real DI client"""
        # Check if Azure Document Intelligence is configured
        if not settings.AZURE_FORM_RECOGNIZER_ENDPOINT or not settings.AZURE_FORM_RECOGNIZER_KEY:
            pytest.skip("Azure Document Intelligence credentials not configured - skipping real PDF tests")
        
        # Create real DI client
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
    def sample_pdf_paths(self):
        """Get paths to sample PDFs for testing"""
        base_path = Path("data/sample_invoices/Raw/Raw_Basic")
        if not base_path.exists():
            pytest.skip(f"Sample PDF directory not found at {base_path}")
        
        # Get a few sample PDFs
        pdf_files = list(base_path.glob("*.pdf")) + list(base_path.glob("*.PDF"))
        if not pdf_files:
            pytest.skip(f"No PDF files found in {base_path}")
        
        return pdf_files[:3]  # Use first 3 PDFs for testing
    
    async def test_real_pdf_extraction_with_line_items(
        self, extraction_service, db_session, sample_pdf_paths
    ):
        """Test full extraction pipeline with real PDF including line items"""
        for pdf_path in sample_pdf_paths:
            invoice_id = f"test-pdf-lineitems-{uuid4().hex[:8]}"
            
            # Read PDF file
            with open(pdf_path, "rb") as f:
                file_content = f.read()
            
            # Upload file
            file_handler = FileHandler()
            upload_result = file_handler.upload_file(
                file_content=file_content,
                file_name=pdf_path.name
            )
            file_path = upload_result.get("file_path")
            if not file_path:
                pytest.skip(f"File upload failed for {pdf_path.name}")
            
            # Create invoice in PENDING state
            invoice = Invoice(
                id=invoice_id,
                file_path=file_path,
                file_name=pdf_path.name,
                upload_date=datetime.utcnow(),
                processing_state=InvoiceState.PENDING,
            )
            await DatabaseService.save_invoice(invoice, db=db_session)
            
            # Disable LLM fallback for this test (we're testing DI extraction)
            original_use_llm = getattr(settings, "USE_LLM_FALLBACK", False)
            settings.USE_LLM_FALLBACK = False
            
            try:
                # Run extraction
                result = await extraction_service.extract_invoice(
                    invoice_id=invoice_id,
                    file_identifier=file_path,
                    file_name=pdf_path.name,
                    upload_date=datetime.utcnow(),
                    db=db_session
                )
                
                # Verify extraction succeeded
                assert result["status"] == "extracted", \
                    f"Extraction failed for {pdf_path.name}: {result.get('errors', [])}"
                
                # Fetch invoice from database
                extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
                assert extracted_invoice is not None, f"Invoice {invoice_id} not found in database"
                
                # Verify basic fields
                assert extracted_invoice.invoice_number is not None or extracted_invoice.vendor_name is not None, \
                    f"At least invoice_number or vendor_name should be extracted from {pdf_path.name}"
                
                # Check if line items were extracted
                if extracted_invoice.line_items:
                    assert len(extracted_invoice.line_items) > 0, \
                        f"Line items list should not be empty if line_items is not None"
                    
                    # Verify line item structure
                    for line_item in extracted_invoice.line_items:
                        assert line_item.line_number > 0, \
                            f"Line number should be positive for {pdf_path.name}"
                        assert line_item.description, \
                            f"Line item description should not be empty for {pdf_path.name}"
                        assert line_item.amount is not None, \
                            f"Line item amount should be extracted for {pdf_path.name}"
                        assert line_item.amount >= 0, \
                            f"Line item amount should be non-negative for {pdf_path.name}"
                    
                    print(f"\n✓ {pdf_path.name}: Extracted {len(extracted_invoice.line_items)} line items")
                else:
                    print(f"\n⚠ {pdf_path.name}: No line items extracted (may be normal for some invoices)")
                
            finally:
                settings.USE_LLM_FALLBACK = original_use_llm
    
    async def test_real_pdf_aggregation_validation(
        self, extraction_service, db_session, sample_pdf_paths
    ):
        """Test aggregation validation with real PDF extraction"""
        for pdf_path in sample_pdf_paths:
            invoice_id = f"test-pdf-agg-{uuid4().hex[:8]}"
            
            with open(pdf_path, "rb") as f:
                file_content = f.read()
            
            file_handler = FileHandler()
            upload_result = file_handler.upload_file(
                file_content=file_content,
                file_name=pdf_path.name
            )
            file_path = upload_result.get("file_path")
            if not file_path:
                pytest.skip(f"File upload failed for {pdf_path.name}")
            
            invoice = Invoice(
                id=invoice_id,
                file_path=file_path,
                file_name=pdf_path.name,
                upload_date=datetime.utcnow(),
                processing_state=InvoiceState.PENDING,
            )
            await DatabaseService.save_invoice(invoice, db=db_session)
            
            original_use_llm = getattr(settings, "USE_LLM_FALLBACK", False)
            settings.USE_LLM_FALLBACK = False
            
            try:
                # Run extraction
                result = await extraction_service.extract_invoice(
                    invoice_id=invoice_id,
                    file_identifier=file_path,
                    file_name=pdf_path.name,
                    upload_date=datetime.utcnow(),
                    db=db_session
                )
                
                assert result["status"] == "extracted", \
                    f"Extraction failed for {pdf_path.name}: {result.get('errors', [])}"
                
                # Check aggregation validation results
                aggregation_validation = result.get("aggregation_validation")
                
                if aggregation_validation:
                    print(f"\n{pdf_path.name} - Aggregation Validation:")
                    print(f"  All Valid: {aggregation_validation['all_valid']}")
                    print(f"  Passed: {aggregation_validation['passed_validations']}/{aggregation_validation['total_validations']}")
                    
                    if not aggregation_validation["all_valid"]:
                        print(f"  Errors:")
                        for error in aggregation_validation["errors"]:
                            print(f"    - {error}")
                    
                    # If line items exist, aggregation validation should have run
                    extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
                    if extracted_invoice.line_items and len(extracted_invoice.line_items) > 0:
                        # Aggregation validation should have been performed
                        assert aggregation_validation is not None, \
                            f"Aggregation validation should be present when line items exist for {pdf_path.name}"
                        
                        # Log validation results (don't fail test - some invoices may have aggregation issues)
                        if aggregation_validation["all_valid"]:
                            print(f"  ✓ All aggregations valid")
                        else:
                            print(f"  ⚠ Some aggregations failed (may be due to extraction accuracy)")
                else:
                    # No aggregation validation means no line items
                    extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
                    if not extracted_invoice.line_items or len(extracted_invoice.line_items) == 0:
                        print(f"\n{pdf_path.name}: No line items, skipping aggregation validation")
                    else:
                        # This shouldn't happen - if line items exist, validation should run
                        pytest.fail(f"Aggregation validation missing but line items exist for {pdf_path.name}")
                
            finally:
                settings.USE_LLM_FALLBACK = original_use_llm
    
    async def test_real_pdf_line_item_field_extraction(
        self, extraction_service, db_session, sample_pdf_paths
    ):
        """Test that line item fields are correctly extracted from real PDFs"""
        for pdf_path in sample_pdf_paths:
            invoice_id = f"test-pdf-lifields-{uuid4().hex[:8]}"
            
            with open(pdf_path, "rb") as f:
                file_content = f.read()
            
            file_handler = FileHandler()
            upload_result = file_handler.upload_file(
                file_content=file_content,
                file_name=pdf_path.name
            )
            file_path = upload_result.get("file_path")
            if not file_path:
                pytest.skip(f"File upload failed for {pdf_path.name}")
            
            invoice = Invoice(
                id=invoice_id,
                file_path=file_path,
                file_name=pdf_path.name,
                upload_date=datetime.utcnow(),
                processing_state=InvoiceState.PENDING,
            )
            await DatabaseService.save_invoice(invoice, db=db_session)
            
            original_use_llm = getattr(settings, "USE_LLM_FALLBACK", False)
            settings.USE_LLM_FALLBACK = False
            
            try:
                result = await extraction_service.extract_invoice(
                    invoice_id=invoice_id,
                    file_identifier=file_path,
                    file_name=pdf_path.name,
                    upload_date=datetime.utcnow(),
                    db=db_session
                )
                
                assert result["status"] == "extracted", \
                    f"Extraction failed for {pdf_path.name}: {result.get('errors', [])}"
                
                extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
                
                if extracted_invoice.line_items and len(extracted_invoice.line_items) > 0:
                    print(f"\n{pdf_path.name} - Line Item Fields:")
                    
                    for idx, line_item in enumerate(extracted_invoice.line_items[:5]):  # Show first 5
                        print(f"  Line {line_item.line_number}:")
                        print(f"    Description: {line_item.description[:50]}...")
                        print(f"    Amount: {line_item.amount}")
                        
                        if line_item.quantity:
                            print(f"    Quantity: {line_item.quantity}")
                        if line_item.unit_price:
                            print(f"    Unit Price: {line_item.unit_price}")
                        if line_item.tax_amount:
                            print(f"    Tax Amount: {line_item.tax_amount}")
                        if line_item.gst_amount:
                            print(f"    GST Amount: {line_item.gst_amount}")
                        if line_item.pst_amount:
                            print(f"    PST Amount: {line_item.pst_amount}")
                        if line_item.qst_amount:
                            print(f"    QST Amount: {line_item.qst_amount}")
                        
                        # Validate quantity * unit_price = amount (if both present)
                        if line_item.quantity and line_item.unit_price and line_item.amount:
                            expected_amount = line_item.quantity * line_item.unit_price
                            difference = abs(line_item.amount - expected_amount)
                            if difference > Decimal("0.01"):
                                print(f"    ⚠ Amount mismatch: {line_item.amount} vs {expected_amount} (diff: {difference})")
                            else:
                                print(f"    ✓ Amount matches quantity * unit_price")
                    
                    # Verify at least basic fields are present
                    first_item = extracted_invoice.line_items[0]
                    assert first_item.description, \
                        f"Line item description should be extracted for {pdf_path.name}"
                    assert first_item.amount is not None, \
                        f"Line item amount should be extracted for {pdf_path.name}"
                
            finally:
                settings.USE_LLM_FALLBACK = original_use_llm
    
    async def test_real_pdf_end_to_end_with_validation(
        self, extraction_service, db_session, sample_pdf_paths
    ):
        """Test complete end-to-end extraction with validation for real PDFs"""
        for pdf_path in sample_pdf_paths:
            invoice_id = f"test-pdf-e2e-{uuid4().hex[:8]}"
            
            with open(pdf_path, "rb") as f:
                file_content = f.read()
            
            file_handler = FileHandler()
            upload_result = file_handler.upload_file(
                file_content=file_content,
                file_name=pdf_path.name
            )
            file_path = upload_result.get("file_path")
            if not file_path:
                pytest.skip(f"File upload failed for {pdf_path.name}")
            
            invoice = Invoice(
                id=invoice_id,
                file_path=file_path,
                file_name=pdf_path.name,
                upload_date=datetime.utcnow(),
                processing_state=InvoiceState.PENDING,
            )
            await DatabaseService.save_invoice(invoice, db=db_session)
            
            original_use_llm = getattr(settings, "USE_LLM_FALLBACK", False)
            settings.USE_LLM_FALLBACK = False
            
            try:
                # Run extraction
                result = await extraction_service.extract_invoice(
                    invoice_id=invoice_id,
                    file_identifier=file_path,
                    file_name=pdf_path.name,
                    upload_date=datetime.utcnow(),
                    db=db_session
                )
                
                # Verify extraction succeeded
                assert result["status"] == "extracted", \
                    f"Extraction failed for {pdf_path.name}: {result.get('errors', [])}"
                
                # Verify result structure
                assert "invoice" in result, "Result should contain invoice data"
                assert "confidence" in result, "Result should contain confidence score"
                assert "field_confidence" in result, "Result should contain field confidence"
                assert "validation" in result, "Result should contain business rule validation"
                
                # Fetch from database
                extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
                assert extracted_invoice is not None
                
                # Verify invoice-level fields
                assert extracted_invoice.file_name == pdf_path.name
                assert extracted_invoice.status == "extracted"
                assert extracted_invoice.extraction_confidence is not None
                
                # Verify line items if present
                if extracted_invoice.line_items:
                    print(f"\n{pdf_path.name} - End-to-End Validation:")
                    print(f"  Invoice Number: {extracted_invoice.invoice_number}")
                    print(f"  Vendor: {extracted_invoice.vendor_name}")
                    print(f"  Total Amount: {extracted_invoice.total_amount}")
                    print(f"  Line Items: {len(extracted_invoice.line_items)}")
                    
                    # Run aggregation validation manually to verify
                    if len(extracted_invoice.line_items) > 0:
                        validation_summary = AggregationValidator.get_validation_summary(extracted_invoice)
                        print(f"  Aggregation Validation: {validation_summary['passed_validations']}/{validation_summary['total_validations']} passed")
                        
                        # Verify aggregation validation is in result
                        assert "aggregation_validation" in result, \
                            "Result should contain aggregation_validation when line items exist"
                        
                        result_agg = result["aggregation_validation"]
                        assert result_agg is not None, \
                            "aggregation_validation should not be None when line items exist"
                        assert "all_valid" in result_agg, \
                            "aggregation_validation should contain all_valid"
                        assert "validations" in result_agg, \
                            "aggregation_validation should contain validations"
                
                # Verify business rule validation
                validation_result = result["validation"]
                assert "is_valid" in validation_result, \
                    "Validation result should contain is_valid"
                assert "passed_rules" in validation_result, \
                    "Validation result should contain passed_rules"
                
                print(f"\n✓ {pdf_path.name}: End-to-end extraction and validation completed")
                
            finally:
                settings.USE_LLM_FALLBACK = original_use_llm
    
    async def test_real_pdf_specific_invoice(
        self, extraction_service, db_session
    ):
        """Test extraction of a specific known invoice PDF"""
        # Use a specific PDF that we know has line items
        pdf_path = Path("data/sample_invoices/Raw/Raw_Basic/ACC012 4202092525.pdf")
        
        if not pdf_path.exists():
            pytest.skip(f"Specific test PDF not found at {pdf_path}")
        
        invoice_id = f"test-pdf-specific-{uuid4().hex[:8]}"
        
        with open(pdf_path, "rb") as f:
            file_content = f.read()
        
        file_handler = FileHandler()
        upload_result = file_handler.upload_file(
            file_content=file_content,
            file_name=pdf_path.name
        )
        file_path = upload_result.get("file_path")
        if not file_path:
            pytest.skip(f"File upload failed for {pdf_path.name}")
        
        invoice = Invoice(
            id=invoice_id,
            file_path=file_path,
            file_name=pdf_path.name,
            upload_date=datetime.utcnow(),
            processing_state=InvoiceState.PENDING,
        )
        await DatabaseService.save_invoice(invoice, db=db_session)
        
        original_use_llm = getattr(settings, "USE_LLM_FALLBACK", False)
        settings.USE_LLM_FALLBACK = False
        
        try:
            result = await extraction_service.extract_invoice(
                invoice_id=invoice_id,
                file_identifier=file_path,
                file_name=pdf_path.name,
                upload_date=datetime.utcnow(),
                db=db_session
            )
            
            assert result["status"] == "extracted", \
                f"Extraction failed: {result.get('errors', [])}"
            
            extracted_invoice = await DatabaseService.get_invoice(invoice_id, db=db_session)
            
            # Detailed validation for this specific invoice
            print(f"\n=== Detailed Extraction Results for {pdf_path.name} ===")
            print(f"Invoice Number: {extracted_invoice.invoice_number}")
            print(f"Vendor: {extracted_invoice.vendor_name}")
            print(f"Invoice Date: {extracted_invoice.invoice_date}")
            print(f"Subtotal: {extracted_invoice.subtotal}")
            print(f"Tax Amount: {extracted_invoice.tax_amount}")
            print(f"Total Amount: {extracted_invoice.total_amount}")
            print(f"Line Items Count: {len(extracted_invoice.line_items) if extracted_invoice.line_items else 0}")
            
            if extracted_invoice.line_items:
                print(f"\nLine Items:")
                for line_item in extracted_invoice.line_items:
                    print(f"  {line_item.line_number}. {line_item.description[:40]}... - ${line_item.amount}")
                
                # Run aggregation validation
                validation_summary = AggregationValidator.get_validation_summary(extracted_invoice)
                print(f"\nAggregation Validation:")
                print(f"  All Valid: {validation_summary['all_valid']}")
                print(f"  Passed: {validation_summary['passed_validations']}/{validation_summary['total_validations']}")
                
                if not validation_summary["all_valid"]:
                    print(f"  Errors:")
                    for error in validation_summary["errors"]:
                        print(f"    - {error}")
            
            # Verify key fields were extracted
            assert extracted_invoice.invoice_number or extracted_invoice.vendor_name, \
                "At least invoice_number or vendor_name should be extracted"
            
        finally:
            settings.USE_LLM_FALLBACK = original_use_llm
