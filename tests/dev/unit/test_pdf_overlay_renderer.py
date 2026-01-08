"""Unit tests for PDF Overlay Renderer"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, date
from decimal import Decimal

from src.erp.pdf_overlay_renderer import PDFOverlayRenderer
from src.models.invoice import Invoice, LineItem


@pytest.mark.unit
class TestPDFOverlayRenderer:
    """Test PDFOverlayRenderer"""
    
    def test_render_overlay_requires_dependencies(self):
        """Test that overlay renderer requires ReportLab and PyPDF2"""
        # This test verifies the import requirements
        try:
            renderer = PDFOverlayRenderer()
            # If we get here, dependencies are available
            assert renderer is not None
        except ImportError as e:
            # Dependencies not available - this is expected in some environments
            assert "ReportLab" in str(e) or "PyPDF2" in str(e)
    
    @pytest.mark.skipif(
        not pytest.importorskip("reportlab", reason="ReportLab not available"),
        reason="ReportLab not available"
    )
    @pytest.mark.skipif(
        not pytest.importorskip("PyPDF2", reason="PyPDF2 not available"),
        reason="PyPDF2 not available"
    )
    def test_render_overlay_success(self, sample_invoice, mock_file_handler):
        """Test successful overlay rendering"""
        # Mock PDF content
        mock_file_handler.download_file.return_value = b"%PDF-1.4\n..."
        
        renderer = PDFOverlayRenderer(file_handler=mock_file_handler)
        
        # Mock PyPDF2
        with patch('src.erp.pdf_overlay_renderer.PdfReader') as mock_reader, \
             patch('src.erp.pdf_overlay_renderer.PdfWriter') as mock_writer:
            
            mock_pdf = MagicMock()
            mock_pdf.pages = [MagicMock()]
            mock_reader.return_value = mock_pdf
            
            mock_writer_instance = MagicMock()
            mock_writer.return_value = mock_writer_instance
            
            overlay_pdf = renderer.render_overlay(sample_invoice)
            
            assert overlay_pdf is not None
            assert isinstance(overlay_pdf, bytes)
    
    def test_get_location_code_from_extensions(self, sample_invoice):
        """Test getting location code from extensions"""
        from src.models.invoice_subtypes import ShiftServiceExtension, InvoiceExtensions
        
        # Add shift service extension
        sample_invoice.extensions = InvoiceExtensions()
        sample_invoice.extensions.shift_service = ShiftServiceExtension(
            service_location="YVR"
        )
        
        renderer = PDFOverlayRenderer()
        location = renderer._get_location_code(sample_invoice)
        
        assert location == "YVR"
    
    def test_get_location_code_from_line_items(self, sample_invoice):
        """Test getting location code from line items"""
        sample_invoice.line_items[0].airport_code = "YYZ"
        
        renderer = PDFOverlayRenderer()
        location = renderer._get_location_code(sample_invoice)
        
        assert location == "YYZ"

