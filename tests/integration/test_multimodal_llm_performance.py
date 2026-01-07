"""
Performance tests for Multimodal LLM extraction.

These tests measure performance characteristics of multimodal LLM extraction:
- Image rendering performance (time, cache effectiveness)
- Multimodal LLM API response times
- Large PDF handling (memory, processing time)
- Multiple page processing (different page selection strategies)

Requirements:
- Azure OpenAI credentials must be configured (AOAI_ENDPOINT, AOAI_API_KEY, AOAI_DEPLOYMENT_NAME or AOAI_MULTIMODAL_DEPLOYMENT_NAME)
- Tests will be skipped if credentials are not available
- Azure Document Intelligence credentials must be configured
- Multimodal LLM fallback must be enabled (USE_MULTIMODAL_LLM_FALLBACK=True)
- PyMuPDF must be installed for image rendering
"""

import pytest
import os
import time
import hashlib
import sys
from datetime import datetime
from decimal import Decimal
from uuid import uuid4
from pathlib import Path
from typing import List, Dict, Any
import asyncio

from src.extraction.extraction_service import ExtractionService
from src.extraction.document_intelligence_client import DocumentIntelligenceClient
from src.extraction.field_extractor import FieldExtractor
from src.ingestion.file_handler import FileHandler
from src.models.invoice import Invoice
from src.services.db_service import DatabaseService
from src.config import settings


@pytest.mark.integration
@pytest.mark.asyncio
@pytest.mark.slow
@pytest.mark.performance
class TestMultimodalLLMPerformance:
    """Performance tests for multimodal LLM extraction"""
    
    @pytest.fixture
    def extraction_service(self, monkeypatch):
        """Create extraction service with real DI and Multimodal LLM clients"""
        # Check if Azure OpenAI is configured
        if not settings.AOAI_ENDPOINT or not settings.AOAI_API_KEY:
            pytest.skip("Azure OpenAI credentials not configured - skipping multimodal LLM performance tests")
        
        # Check for multimodal deployment
        multimodal_deployment = settings.AOAI_MULTIMODAL_DEPLOYMENT_NAME or settings.AOAI_DEPLOYMENT_NAME
        if not multimodal_deployment:
            pytest.skip("Azure OpenAI deployment not configured - skipping multimodal LLM performance tests")
        
        # Check if Azure Document Intelligence is configured
        if not settings.AZURE_FORM_RECOGNIZER_ENDPOINT or not settings.AZURE_FORM_RECOGNIZER_KEY:
            pytest.skip("Azure Document Intelligence credentials not configured - skipping multimodal LLM performance tests")
        
        # Check if PyMuPDF is available
        try:
            import fitz  # PyMuPDF
        except ImportError:
            pytest.skip("PyMuPDF not installed - required for image rendering performance tests")
        
        # Enable multimodal LLM fallback
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
            pytest.skip("Multimodal LLM configuration not available - skipping multimodal LLM performance tests")
        
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
        unique_id = f"test-perf-{timestamp}-{uuid4().hex[:8]}"
        return unique_id
    
    def _read_pdf_file(self, file_path: str) -> bytes:
        """Read PDF file content"""
        with open(file_path, "rb") as f:
            return f.read()
    
    def _get_file_hash(self, file_content: bytes) -> str:
        """Get SHA256 hash of file content"""
        return hashlib.sha256(file_content).hexdigest()
    
    @pytest.mark.asyncio
    async def test_image_rendering_performance_first_render(
        self, extraction_service, sample_pdf_path
    ):
        """Test image rendering performance on first render (no cache)"""
        file_content = self._read_pdf_file(sample_pdf_path)
        file_hash = self._get_file_hash(file_content)
        
        # Clear image cache to ensure first render
        if extraction_service._image_cache:
            extraction_service._image_cache.clear()
        
        # Measure rendering time
        start_time = time.time()
        images = await asyncio.to_thread(
            extraction_service._render_multimodal_images,
            file_content,
            file_hash
        )
        render_time = time.time() - start_time
        
        # Assertions
        assert images is not None
        assert len(images) > 0, "Should render at least one image"
        assert render_time > 0, "Render time should be positive"
        
        # Performance assertions (adjust thresholds based on your system)
        assert render_time < 5.0, f"First render should complete in < 5s, took {render_time:.2f}s"
        
        # Verify images are base64 strings
        for img in images:
            assert isinstance(img, str), "Images should be base64 strings"
            assert len(img) > 0, "Image strings should not be empty"
        
        print(f"\n[PERF] First image render: {render_time:.3f}s for {len(images)} images")
    
    @pytest.mark.asyncio
    async def test_image_rendering_performance_cached_render(
        self, extraction_service, sample_pdf_path
    ):
        """Test image rendering performance with cache hit"""
        file_content = self._read_pdf_file(sample_pdf_path)
        file_hash = self._get_file_hash(file_content)
        
        # Ensure cache is enabled
        if not extraction_service._image_cache:
            pytest.skip("Image cache not enabled - cannot test cache performance")
        
        # Clear cache and do first render
        extraction_service._image_cache.clear()
        first_start = time.time()
        images1 = await asyncio.to_thread(
            extraction_service._render_multimodal_images,
            file_content,
            file_hash
        )
        first_render_time = time.time() - first_start
        
        # Second render should hit cache
        second_start = time.time()
        images2 = await asyncio.to_thread(
            extraction_service._render_multimodal_images,
            file_content,
            file_hash
        )
        cached_render_time = time.time() - second_start
        
        # Assertions
        assert images1 == images2, "Cached images should match first render"
        assert cached_render_time < first_render_time, "Cached render should be faster"
        
        # Cache should provide significant speedup (at least 10x faster)
        speedup = first_render_time / cached_render_time if cached_render_time > 0 else float('inf')
        assert speedup >= 10, f"Cache should provide at least 10x speedup, got {speedup:.1f}x"
        
        print(f"\n[PERF] First render: {first_render_time:.3f}s, Cached render: {cached_render_time:.3f}s, Speedup: {speedup:.1f}x")
    
    @pytest.mark.asyncio
    async def test_image_rendering_different_formats(
        self, extraction_service, sample_pdf_path, monkeypatch
    ):
        """Test image rendering performance with different formats (PNG vs JPEG)"""
        file_content = self._read_pdf_file(sample_pdf_path)
        file_hash = self._get_file_hash(file_content)
        
        # Test PNG format
        monkeypatch.setattr(settings, "MULTIMODAL_IMAGE_FORMAT", "png", raising=False)
        extraction_service._image_cache.clear()
        
        png_start = time.time()
        png_images = await asyncio.to_thread(
            extraction_service._render_multimodal_images,
            file_content,
            file_hash
        )
        png_time = time.time() - png_start
        
        # Test JPEG format
        monkeypatch.setattr(settings, "MULTIMODAL_IMAGE_FORMAT", "jpeg", raising=False)
        extraction_service._image_cache.clear()
        
        jpeg_start = time.time()
        jpeg_images = await asyncio.to_thread(
            extraction_service._render_multimodal_images,
            file_content,
            file_hash
        )
        jpeg_time = time.time() - jpeg_start
        
        # Assertions
        assert len(png_images) > 0, "Should render PNG images"
        assert len(jpeg_images) > 0, "Should render JPEG images"
        assert len(png_images) == len(jpeg_images), "Should render same number of images"
        
        # JPEG is typically smaller (faster to encode/decode) but may take similar time to render
        print(f"\n[PERF] PNG render: {png_time:.3f}s, JPEG render: {jpeg_time:.3f}s")
        print(f"[PERF] PNG image sizes: {[len(img) for img in png_images]}")
        print(f"[PERF] JPEG image sizes: {[len(img) for img in jpeg_images]}")
    
    @pytest.mark.asyncio
    async def test_multimodal_llm_response_time(
        self, extraction_service, sample_pdf_path, unique_invoice_id, db_session
    ):
        """Test multimodal LLM API response time"""
        file_content = self._read_pdf_file(sample_pdf_path)
        file_hash = self._get_file_hash(file_content)
        
        # Upload file
        file_handler = FileHandler()
        upload_result = await file_handler.upload_file(
            file_content=file_content,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.now()
        )
        file_path = upload_result["file_path"]
        
        # Create invoice with low-confidence fields to trigger LLM
        invoice = Invoice(
            id=unique_invoice_id,
            file_path=file_path,
            file_name=os.path.basename(sample_pdf_path),
            upload_date=datetime.now(),
            status="extracted",
            invoice_number="TEST-001",
            vendor_name="Test Vendor",
            total_amount=Decimal("100.00"),
            field_confidence={
                "invoice_number": 0.5,  # Low confidence to trigger LLM
                "vendor_name": 0.5,
                "total_amount": 0.5,
            }
        )
        
        # Save invoice to database
        patch = {
            "id": unique_invoice_id,
            "file_path": file_path,
            "file_name": os.path.basename(sample_pdf_path),
            "upload_date": invoice.upload_date.isoformat(),
            "status": "extracted",
            "invoice_number": "TEST-001",
            "vendor_name": "Test Vendor",
            "total_amount": "100.00",
            "field_confidence": invoice.field_confidence,
        }
        await DatabaseService.set_extraction_result(unique_invoice_id, patch, db=db_session)
        
        # Prepare DI data
        di_data = {
            "content": "Sample invoice content",
            "invoice_number": "TEST-001",
            "vendor_name": "Test Vendor",
            "total_amount": "100.00",
        }
        fc = {"invoice_number": 0.5, "vendor_name": 0.5, "total_amount": 0.5}
        low_conf_fields = ["invoice_number", "vendor_name", "total_amount"]
        
        # Measure multimodal LLM call time
        start_time = time.time()
        result = await extraction_service._run_multimodal_fallback(
            invoice,
            low_conf_fields,
            di_data,
            fc,
            file_content,
            invoice_id=unique_invoice_id,
        )
        llm_time = time.time() - start_time
        
        # Assertions
        assert result is not None, "Multimodal LLM should return a result"
        assert "success" in result, "Result should include success status"
        assert llm_time > 0, "LLM call time should be positive"
        
        # Performance assertion (adjust threshold based on your API)
        assert llm_time < 30.0, f"Multimodal LLM call should complete in < 30s, took {llm_time:.2f}s"
        
        print(f"\n[PERF] Multimodal LLM response time: {llm_time:.3f}s")
        print(f"[PERF] LLM result: success={result.get('success')}, groups_succeeded={result.get('groups_succeeded')}")
        
        # Cleanup
        try:
            await file_handler.delete_file(file_path)
        except Exception:
            pass
    
    @pytest.mark.asyncio
    async def test_large_pdf_handling(
        self, extraction_service, sample_pdf_path, monkeypatch
    ):
        """Test handling of larger PDFs (simulate by rendering multiple pages)"""
        file_content = self._read_pdf_file(sample_pdf_path)
        file_hash = self._get_file_hash(file_content)
        
        # Test with different max_pages settings
        import fitz
        pdf_doc = fitz.open(stream=file_content, filetype="pdf")
        total_pages = len(pdf_doc)
        pdf_doc.close()
        
        if total_pages < 2:
            pytest.skip(f"PDF has only {total_pages} page(s), need at least 2 pages for large PDF test")
        
        # Temporarily increase max_pages
        original_max_pages = getattr(settings, "MULTIMODAL_MAX_PAGES", 2)
        
        try:
            # Test with max_pages = total_pages
            monkeypatch.setattr(settings, "MULTIMODAL_MAX_PAGES", total_pages, raising=False)
            
            start_time = time.time()
            images = await asyncio.to_thread(
                extraction_service._render_multimodal_images,
                file_content,
                file_hash
            )
            render_time = time.time() - start_time
            
            # Assertions
            assert images is not None
            assert len(images) <= total_pages, "Should not render more pages than available"
            assert render_time > 0, "Render time should be positive"
            
            # Performance should scale reasonably (not exponentially)
            # Each additional page should add roughly similar time
            avg_time_per_page = render_time / len(images) if images else 0
            assert avg_time_per_page < 2.0, f"Average time per page should be < 2s, got {avg_time_per_page:.2f}s"
            
            print(f"\n[PERF] Large PDF ({total_pages} pages): {render_time:.3f}s total, {avg_time_per_page:.3f}s per page")
            print(f"[PERF] Rendered {len(images)} images")
            
        finally:
            # Restore original setting
            monkeypatch.setattr(settings, "MULTIMODAL_MAX_PAGES", original_max_pages, raising=False)
    
    @pytest.mark.asyncio
    async def test_multiple_page_selection_strategies(
        self, extraction_service, sample_pdf_path, monkeypatch
    ):
        """Test performance of different page selection strategies"""
        file_content = self._read_pdf_file(sample_pdf_path)
        file_hash = self._get_file_hash(file_content)
        
        # Get total pages
        import fitz
        pdf_doc = fitz.open(stream=file_content, filetype="pdf")
        total_pages = len(pdf_doc)
        pdf_doc.close()
        
        if total_pages < 3:
            pytest.skip(f"PDF has only {total_pages} page(s), need at least 3 pages for page selection test")
        
        strategies = ["first", "last", "middle", "all"]
        results = {}
        
        for strategy in strategies:
            # Set page selection strategy
            monkeypatch.setattr(settings, "MULTIMODAL_PAGE_SELECTION", strategy, raising=False)
            extraction_service._image_cache.clear()
            
            # Measure rendering time
            start_time = time.time()
            images = await asyncio.to_thread(
                extraction_service._render_multimodal_images,
                file_content,
                file_hash
            )
            render_time = time.time() - start_time
            
            results[strategy] = {
                "time": render_time,
                "image_count": len(images),
            }
        
        # Assertions
        for strategy, result in results.items():
            assert result["time"] > 0, f"{strategy} strategy should complete in positive time"
            assert result["image_count"] > 0, f"{strategy} strategy should render at least one image"
        
        # "all" should render more images (and potentially take longer) than others
        if total_pages > 2:
            assert results["all"]["image_count"] >= results["first"]["image_count"], \
                "'all' strategy should render at least as many images as 'first'"
        
        print(f"\n[PERF] Page selection strategies (PDF has {total_pages} pages):")
        for strategy, result in results.items():
            print(f"  {strategy}: {result['time']:.3f}s, {result['image_count']} images")
    
    @pytest.mark.asyncio
    async def test_image_cache_size_limits(
        self, extraction_service, sample_pdf_path
    ):
        """Test that image cache respects size limits (LRU eviction)"""
        if not extraction_service._image_cache:
            pytest.skip("Image cache not enabled - cannot test cache size limits")
        
        # Get cache max size
        max_size = extraction_service._image_cache.max_size
        
        if max_size < 2:
            pytest.skip(f"Cache max size ({max_size}) too small for eviction test")
        
        file_content = self._read_pdf_file(sample_pdf_path)
        
        # Render images for multiple different files (simulate with different hashes)
        # Since we only have one file, we'll test by clearing and re-adding
        extraction_service._image_cache.clear()
        
        # Add entries up to max_size
        for i in range(max_size + 1):
            # Create unique hash for each "file"
            fake_hash = f"test-file-{i}"
            images = await asyncio.to_thread(
                extraction_service._render_multimodal_images,
                file_content,
                fake_hash
            )
            
            cache_size = extraction_service._image_cache.size()
            assert cache_size <= max_size, \
                f"Cache size ({cache_size}) should not exceed max_size ({max_size})"
        
        # Final cache size should be at max_size (LRU eviction should have occurred)
        final_size = extraction_service._image_cache.size()
        assert final_size == max_size, \
            f"Final cache size should be {max_size}, got {final_size}"
        
        print(f"\n[PERF] Cache size limit test: max_size={max_size}, final_size={final_size}")
    
    @pytest.mark.asyncio
    async def test_image_rendering_memory_efficiency(
        self, extraction_service, sample_pdf_path
    ):
        """Test that image rendering doesn't cause excessive memory usage"""
        file_content = self._read_pdf_file(sample_pdf_path)
        file_hash = self._get_file_hash(file_content)
        
        # Measure memory before rendering (approximate)
        import sys
        import gc
        gc.collect()
        
        # Render images multiple times and check memory doesn't grow unbounded
        extraction_service._image_cache.clear()
        
        initial_size = sys.getsizeof(file_content)
        
        for i in range(5):
            images = await asyncio.to_thread(
                extraction_service._render_multimodal_images,
                file_content,
                file_hash
            )
            
            # After first render, subsequent renders should use cache
            # Memory should not grow significantly
            gc.collect()
        
        # Verify images are reasonable size (not excessively large)
        images = await asyncio.to_thread(
            extraction_service._render_multimodal_images,
            file_content,
            file_hash
        )
        
        total_image_size = sum(len(img.encode('utf-8')) for img in images)
        
        # Base64 images should be reasonable size (not > 10MB per image)
        max_image_size = 10 * 1024 * 1024  # 10MB
        for i, img in enumerate(images):
            img_size = len(img.encode('utf-8'))
            assert img_size < max_image_size, \
                f"Image {i} size ({img_size} bytes) should be < {max_image_size} bytes"
        
        print(f"\n[PERF] Image rendering memory test:")
        print(f"  PDF size: {len(file_content)} bytes")
        print(f"  Total image size (base64): {total_image_size} bytes")
        print(f"  Number of images: {len(images)}")
        print(f"  Average image size: {total_image_size / len(images) if images else 0:.0f} bytes")
    
    @pytest.mark.asyncio
    async def test_concurrent_image_rendering(
        self, extraction_service, sample_pdf_path
    ):
        """Test concurrent image rendering performance"""
        file_content = self._read_pdf_file(sample_pdf_path)
        
        # Clear cache
        if extraction_service._image_cache:
            extraction_service._image_cache.clear()
        
        # Render same file concurrently multiple times
        num_concurrent = 3
        file_hashes = [f"concurrent-{i}" for i in range(num_concurrent)]
        
        start_time = time.time()
        tasks = [
            asyncio.to_thread(
                extraction_service._render_multimodal_images,
                file_content,
                file_hash
            )
            for file_hash in file_hashes
        ]
        results = await asyncio.gather(*tasks)
        concurrent_time = time.time() - start_time
        
        # Sequential rendering for comparison
        extraction_service._image_cache.clear()
        sequential_start = time.time()
        for file_hash in file_hashes:
            await asyncio.to_thread(
                extraction_service._render_multimodal_images,
                file_content,
                file_hash
            )
        sequential_time = time.time() - sequential_start
        
        # Assertions
        assert len(results) == num_concurrent, "Should render all concurrent requests"
        for result in results:
            assert len(result) > 0, "Each concurrent render should produce images"
        
        # Concurrent should be faster than sequential (though not necessarily num_concurrent times faster)
        assert concurrent_time < sequential_time, \
            f"Concurrent rendering ({concurrent_time:.3f}s) should be faster than sequential ({sequential_time:.3f}s)"
        
        speedup = sequential_time / concurrent_time if concurrent_time > 0 else 1.0
        print(f"\n[PERF] Concurrent rendering ({num_concurrent} requests):")
        print(f"  Concurrent time: {concurrent_time:.3f}s")
        print(f"  Sequential time: {sequential_time:.3f}s")
        print(f"  Speedup: {speedup:.1f}x")

