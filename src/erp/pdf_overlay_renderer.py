"""PDF overlay renderer for invoice coding and approvals - simplified version"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from io import BytesIO
from decimal import Decimal

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.units import inch
    from reportlab.lib.colors import black, blue, green, red, white
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    canvas = None
    letter = None
    inch = None
    black = blue = green = red = white = None

try:
    from PyPDF2 import PdfReader, PdfWriter
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    PdfReader = PdfWriter = None

logger = logging.getLogger(__name__)

if not REPORTLAB_AVAILABLE:
    logger.warning("ReportLab not available - PDF overlay rendering disabled")
if not PYPDF2_AVAILABLE:
    logger.warning("PyPDF2 not available - PDF overlay rendering disabled")

from src.models.invoice import Invoice
from src.ingestion.file_handler import FileHandler


class PDFOverlayRenderer:
    """Renders PDF overlay with coding and approval information"""
    
    def __init__(self, file_handler: Optional[FileHandler] = None):
        """
        Initialize PDF overlay renderer
        
        Args:
            file_handler: FileHandler instance for file operations
        """
        if not REPORTLAB_AVAILABLE:
            raise ImportError("ReportLab is required for PDF overlay rendering. Install with: pip install reportlab")
        if not PYPDF2_AVAILABLE:
            raise ImportError("PyPDF2 is required for PDF overlay rendering. Install with: pip install PyPDF2")
        
        self.file_handler = file_handler or FileHandler()
    
    def render_overlay(
        self,
        invoice: Invoice,
        original_pdf_content: Optional[bytes] = None
    ) -> bytes:
        """
        Render PDF overlay on top of original invoice
        
        Args:
            invoice: Pydantic Invoice model
            original_pdf_content: Original invoice PDF content (if not provided, will download)
            
        Returns:
            PDF bytes with overlay
        """
        # Download original PDF if not provided
        if not original_pdf_content:
            original_pdf_content = self.file_handler.download_file(invoice.file_path)
        
        if not original_pdf_content:
            raise ValueError(f"Could not retrieve original PDF for invoice {invoice.id}")
        
        # Read original PDF
        original_pdf = PdfReader(BytesIO(original_pdf_content))
        
        # Create overlay
        overlay_pdf = self._create_overlay_pdf(invoice, len(original_pdf.pages))
        
        # Merge overlay with original
        output_pdf = PdfWriter()
        for page_num, page in enumerate(original_pdf.pages):
            # Create overlay page (use first page overlay for all pages)
            overlay_page = overlay_pdf.pages[0]
            
            # Merge overlay onto original page
            page.merge_page(overlay_page)
            output_pdf.add_page(page)
        
        # Write to bytes
        output_buffer = BytesIO()
        output_pdf.write(output_buffer)
        return output_buffer.getvalue()
    
    def _create_overlay_pdf(
        self,
        invoice: Invoice,
        num_pages: int
    ) -> PdfReader:
        """
        Create overlay PDF with coding and approval information
        
        Args:
            invoice: Pydantic Invoice model
            num_pages: Number of pages in original PDF
            
        Returns:
            PdfReader with overlay pages
        """
        overlay_buffer = BytesIO()
        overlay_canvas = canvas.Canvas(overlay_buffer, pagesize=letter)
        
        # Render overlay for first page
        self._render_header_overlay(overlay_canvas, invoice)
        self._render_coding_overlay(overlay_canvas, invoice)  # This is the "red box"
        self._render_approval_overlay(overlay_canvas, invoice)
        
        overlay_canvas.save()
        
        # Create PDF reader from buffer
        overlay_buffer.seek(0)
        return PdfReader(overlay_buffer)
    
    def _render_header_overlay(
        self,
        canvas_obj: canvas.Canvas,
        invoice: Invoice
    ):
        """Render header block with basic invoice info (blue box)"""
        # Header box at top
        canvas_obj.setFillColor(blue)
        canvas_obj.rect(0.5 * inch, 10.5 * inch, 7 * inch, 0.8 * inch, fill=1)
        
        canvas_obj.setFillColor(white)
        canvas_obj.setFont("Helvetica-Bold", 10)
        canvas_obj.drawString(0.6 * inch, 11.1 * inch, "FINANCE PROCESSING HEADER")
        
        canvas_obj.setFont("Helvetica", 9)
        y_pos = 10.9 * inch
        
        # Invoice info
        info_lines = [
            f"Received Date: {invoice.upload_date.strftime('%Y-%m-%d') if invoice.upload_date else 'N/A'}",
            f"Finance Received: {invoice.fa_approval_date.strftime('%Y-%m-%d') if invoice.fa_approval_date else 'N/A'}",
            f"Vendor: {invoice.vendor_name or 'N/A'}",
            f"Vendor ID: {invoice.vendor_id or 'N/A'}",
            f"Location Code: {self._get_location_code(invoice)}",
            f"Entry Number: {invoice.id[:8] if invoice.id else 'N/A'}",
        ]
        
        x_start = 0.6 * inch
        x_mid = 4 * inch
        for i, line in enumerate(info_lines):
            x = x_start if i % 2 == 0 else x_mid
            y = y_pos - (i // 2) * 0.15 * inch
            canvas_obj.drawString(x, y, line)
    
    def _render_coding_overlay(
        self,
        canvas_obj: canvas.Canvas,
        invoice: Invoice
    ):
        """Render coding block with GL/cost centre/project (RED BOX)"""
        # Coding box - RED as requested
        canvas_obj.setFillColor(red)
        canvas_obj.rect(0.5 * inch, 9.5 * inch, 7 * inch, 0.8 * inch, fill=1)
        
        canvas_obj.setFillColor(white)
        canvas_obj.setFont("Helvetica-Bold", 10)
        canvas_obj.drawString(0.6 * inch, 10.1 * inch, "FINANCIAL CODING")
        
        canvas_obj.setFont("Helvetica", 9)
        y_pos = 9.9 * inch
        
        # Get coding from line items or extensions
        gl_code = self._get_gl_code(invoice)
        cost_centre = self._get_cost_centre(invoice)
        project_code = self._get_project_code(invoice)
        
        total_str = f"${invoice.total_amount:.2f}" if invoice.total_amount else "N/A"
        coding_lines = [
            f"Invoice Total: {total_str}",
            f"GL Code: {gl_code or 'N/A'}",
            f"Cost Centre: {cost_centre or 'N/A'}",
            f"Project Code: {project_code or 'N/A'}",
        ]
        
        x_start = 0.6 * inch
        x_mid = 4 * inch
        for i, line in enumerate(coding_lines):
            x = x_start if i % 2 == 0 else x_mid
            y = y_pos - (i // 2) * 0.15 * inch
            canvas_obj.drawString(x, y, line)
        
        # Tax recovery info
        if invoice.tax_amount:
            tax_recovery = self._calculate_tax_recovery(invoice)
            canvas_obj.drawString(
                0.6 * inch,
                9.5 * inch,
                f"Tax Recovery: ${tax_recovery['recoverable']:.2f} / ${tax_recovery['non_recoverable']:.2f}"
            )
    
    def _render_approval_overlay(
        self,
        canvas_obj: canvas.Canvas,
        invoice: Invoice
    ):
        """Render approval block with approver names and timestamps (blue box)"""
        # Approval box
        canvas_obj.setFillColor(blue)
        canvas_obj.rect(0.5 * inch, 8.5 * inch, 7 * inch, 0.8 * inch, fill=1)
        
        canvas_obj.setFillColor(white)
        canvas_obj.setFont("Helvetica-Bold", 10)
        canvas_obj.drawString(0.6 * inch, 9.1 * inch, "APPROVALS")
        
        canvas_obj.setFont("Helvetica", 9)
        y_pos = 8.9 * inch
        
        approvals = []
        if invoice.bv_approver:
            bv_date_str = invoice.bv_approval_date.strftime('%Y-%m-%d %H:%M') if invoice.bv_approval_date else 'N/A'
            approvals.append(f"BV: {invoice.bv_approver} ({bv_date_str})")
        if invoice.fa_approver:
            fa_date_str = invoice.fa_approval_date.strftime('%Y-%m-%d %H:%M') if invoice.fa_approval_date else 'N/A'
            approvals.append(f"FA: {invoice.fa_approver} ({fa_date_str})")
        
        if not approvals:
            approvals.append("No approvals yet")
        
        for i, approval in enumerate(approvals):
            canvas_obj.drawString(0.6 * inch, y_pos - i * 0.15 * inch, approval)
    
    def _get_location_code(self, invoice: Invoice) -> str:
        """Get location code from extensions or line items"""
        # Try to get from ShiftService extension
        if invoice.extensions:
            if hasattr(invoice.extensions, 'shift_service') and invoice.extensions.shift_service:
                return invoice.extensions.shift_service.service_location or "N/A"
        
        # Try to get from line items (airport_code)
        if invoice.line_items:
            for item in invoice.line_items:
                if item.airport_code:
                    return item.airport_code
        
        return "N/A"
    
    def _get_gl_code(self, invoice: Invoice) -> Optional[str]:
        """Get GL code from line items"""
        # Try to get from first line item with GL code
        if invoice.line_items:
            for item in invoice.line_items:
                # GL code might be in project_code or a separate field
                # For now, check if there's a pattern we can extract
                pass
        
        # Could be stored in extensions or review notes
        # For vanilla version, this would typically come from HITL input
        return None
    
    def _get_cost_centre(self, invoice: Invoice) -> Optional[str]:
        """Get cost centre from line items"""
        if invoice.line_items:
            for item in invoice.line_items:
                if item.cost_centre_code:
                    return item.cost_centre_code
        return None
    
    def _get_project_code(self, invoice: Invoice) -> Optional[str]:
        """Get project code from line items"""
        if invoice.line_items:
            for item in invoice.line_items:
                if item.project_code:
                    return item.project_code
        return None
    
    def _calculate_tax_recovery(self, invoice: Invoice) -> Dict[str, Decimal]:
        """Calculate tax recovery amounts"""
        # Default: assume all tax is recoverable
        # In production, this could be overridden by rules or FA adjustments
        total_tax = invoice.tax_amount or Decimal("0.00")
        return {
            "recoverable": total_tax,
            "non_recoverable": Decimal("0.00")
        }

