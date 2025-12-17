"""Unit tests for PDFProcessor."""

from io import BytesIO

import pytest
from PyPDF2 import PdfWriter

from src.ingestion.pdf_processor import PDFProcessor


def _make_one_page_pdf() -> bytes:
    buf = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    writer.write(buf)
    return buf.getvalue()


@pytest.mark.unit
class TestPDFProcessor:
    def test_validate_rejects_non_pdf_extension(self):
        proc = PDFProcessor(max_file_size_mb=1)
        ok, err = proc.validate_file(b"not-a-pdf", "invoice.txt")
        assert ok is False
        assert "File must be a PDF" in err

    def test_validate_rejects_empty_file(self):
        proc = PDFProcessor(max_file_size_mb=1)
        ok, err = proc.validate_file(b"", "invoice.pdf")
        assert ok is False
        assert err == "File is empty"

    def test_validate_rejects_oversize(self):
        # Max 1 byte to force oversize path
        proc = PDFProcessor(max_file_size_mb=0)
        ok, err = proc.validate_file(b"x", "invoice.pdf")
        assert ok is False
        assert "exceeds maximum allowed size" in err

    def test_validate_accepts_simple_pdf_and_get_info(self):
        proc = PDFProcessor(max_file_size_mb=1)
        pdf_bytes = _make_one_page_pdf()

        ok, err = proc.validate_file(pdf_bytes, "invoice.pdf")
        assert ok is True
        assert err is None

        info = proc.get_pdf_info(pdf_bytes)
        assert info["page_count"] == 1
        assert info["is_encrypted"] is False

