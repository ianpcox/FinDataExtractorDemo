"""
Create sample test data for demos
Generates sample PDF invoices and test data
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# Fix Windows encoding
if sys.platform == 'win32':
    os.system('chcp 65001 >nul 2>&1')
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def create_sample_invoice_pdf(output_path: Path, invoice_number: str, vendor_name: str, 
                             total_amount: float, invoice_date: str = None):
    """Create a sample invoice PDF"""
    if invoice_date is None:
        invoice_date = datetime.now().strftime("%Y-%m-%d")
    
    # Create PDF
    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
    )
    story.append(Paragraph("INVOICE", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Invoice details
    invoice_data = [
        ['Invoice Number:', invoice_number],
        ['Invoice Date:', invoice_date],
        ['Due Date:', (datetime.strptime(invoice_date, "%Y-%m-%d") + timedelta(days=30)).strftime("%Y-%m-%d")],
    ]
    
    invoice_table = Table(invoice_data, colWidths=[2*inch, 3*inch])
    invoice_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(invoice_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Vendor and Customer
    vendor_customer = [
        ['Bill To:', 'From:'],
        ['CATSA', vendor_name],
        ['123 Airport Road', '456 Business St'],
        ['Ottawa, ON K1A 0B1', 'Toronto, ON M5H 2N2'],
    ]
    
    vendor_table = Table(vendor_customer, colWidths=[3*inch, 3*inch])
    vendor_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(vendor_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Line items
    line_items_data = [
        ['Description', 'Quantity', 'Unit Price', 'Amount'],
        ['Security Services - January 2024', '1', f'${total_amount * 0.7:.2f}', f'${total_amount * 0.7:.2f}'],
        ['Equipment Rental', '2', f'${total_amount * 0.15:.2f}', f'${total_amount * 0.3:.2f}'],
        ['Training Materials', '1', f'${total_amount * 0.025:.2f}', f'${total_amount * 0.025:.2f}'],
    ]
    
    items_table = Table(line_items_data, colWidths=[3.5*inch, 1*inch, 1*inch, 1*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 0.2*inch))
    
    # Totals
    subtotal = total_amount * 0.975
    tax = total_amount * 0.025
    totals_data = [
        ['Subtotal:', f'${subtotal:.2f}'],
        ['Tax (GST/HST):', f'${tax:.2f}'],
        ['Total:', f'${total_amount:.2f}'],
    ]
    
    totals_table = Table(totals_data, colWidths=[4*inch, 1.5*inch])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 12),
        ('FONTSIZE', (0, 0), (0, -2), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(totals_table)
    
    # Build PDF
    doc.build(story)
    print(f"[OK] Created sample invoice: {output_path.name}")


def create_sample_shift_service_invoice(output_path: Path):
    """Create a sample Shift Service invoice"""
    invoice_date = datetime.now().strftime("%Y-%m-%d")
    invoice_number = f"SS-{datetime.now().strftime('%Y%m%d')}-001"
    
    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
    )
    story.append(Paragraph("SHIFT SERVICE INVOICE", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Invoice details
    invoice_data = [
        ['Invoice Number:', invoice_number],
        ['Invoice Date:', invoice_date],
        ['Billing Period:', f"2024-01-01 to 2024-01-31"],
        ['Service Location:', 'YYZ Terminal 1'],
    ]
    
    invoice_table = Table(invoice_data, colWidths=[2*inch, 3*inch])
    invoice_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(invoice_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Vendor
    story.append(Paragraph("<b>From:</b>", styles['Normal']))
    story.append(Paragraph("Security Services Inc.", styles['Normal']))
    story.append(Paragraph("123 Security Blvd", styles['Normal']))
    story.append(Paragraph("Toronto, ON M5H 2N2", styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Shift details
    shift_data = [
        ['Date', 'Worker Name', 'Shift #', 'Time In', 'Time Out', 'Hours'],
        ['2024-01-15', 'John Smith', '1', '06:00', '14:00', '8.0'],
        ['2024-01-15', 'Jane Doe', '2', '14:00', '22:00', '8.0'],
        ['2024-01-16', 'John Smith', '1', '06:00', '14:00', '8.0'],
    ]
    
    shift_table = Table(shift_data, colWidths=[1*inch, 1.5*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch])
    shift_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(shift_table)
    story.append(Spacer(1, 0.2*inch))
    
    # Totals
    total_shifts = 3
    shift_rate = 45.00
    total_amount = total_shifts * shift_rate
    
    totals_data = [
        ['Total Shifts:', str(total_shifts)],
        ['Shift Rate:', f'${shift_rate:.2f}'],
        ['Total Amount:', f'${total_amount:.2f}'],
    ]
    
    totals_table = Table(totals_data, colWidths=[4*inch, 1.5*inch])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(totals_table)
    
    doc.build(story)
    print(f"[OK] Created shift service invoice: {output_path.name}")


def main():
    """Create all sample data"""
    print("\n" + "="*60)
    print("Creating Sample Test Data")
    print("="*60)
    
    # Create sample_data directory
    sample_dir = Path(__file__).parent.parent / "demos" / "sample_data"
    sample_dir.mkdir(parents=True, exist_ok=True)
    
    # Create sample invoices
    print("\n[CREATE] Generating sample invoices...")
    
    # Standard invoice
    create_sample_invoice_pdf(
        output_path=sample_dir / "sample_invoice_001.pdf",
        invoice_number="INV-2024-001",
        vendor_name="Acme Corporation",
        total_amount=1358.02,
        invoice_date="2024-01-15"
    )
    
    # Another standard invoice
    create_sample_invoice_pdf(
        output_path=sample_dir / "sample_invoice_002.pdf",
        invoice_number="INV-2024-002",
        vendor_name="Tech Solutions Ltd.",
        total_amount=2450.75,
        invoice_date="2024-01-20"
    )
    
    # Shift service invoice
    create_sample_shift_service_invoice(
        output_path=sample_dir / "sample_shift_service_001.pdf"
    )
    
    print(f"\n[OK] Sample data created in: {sample_dir}")
    print(f"\nFiles created:")
    for pdf in sample_dir.glob("*.pdf"):
        print(f"  - {pdf.name} ({pdf.stat().st_size:,} bytes)")
    
    print("\n" + "="*60)
    print("Sample Data Creation Complete!")
    print("="*60)
    print("\n[INFO] You can now run the demos:")
    print("  1. Start API server: uvicorn api.main:app --reload")
    print("  2. Run demos: python demos/demo_01_ingestion.py")
    print("\n[INFO] Or run all demos: python scripts/run_demo_tests.py")


if __name__ == "__main__":
    main()

