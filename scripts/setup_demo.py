"""
Setup script for FinDataExtractorDEMO
- Sources invoices from FinDataExtractor/data/sample_invoices/Raw/
- Copies them to storage/raw/
- Creates demo database with sample invoice records
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime, date
from decimal import Decimal
import shutil

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from src.models.database import Base
from src.models.db_models import Invoice as InvoiceDB
from src.models.invoice import Invoice, InvoiceSubtype, InvoiceState, LineItem
from src.models.db_utils import pydantic_to_db_invoice

# Source directory for invoices (local data folder in demo project)
SOURCE_INVOICE_DIR = project_root / "data" / "sample_invoices" / "Raw" / "Raw_Basic"

# Destination directory (demo project storage)
DEMO_STORAGE_DIR = project_root / "storage" / "raw"

# Demo database
DEMO_DB_PATH = project_root / "findataextractor_demo.db"
DEMO_DATABASE_URL = f"sqlite+aiosqlite:///{DEMO_DB_PATH}"


async def setup_database():
    """Create database and tables"""
    print("Creating demo database...")
    
    # Remove existing demo database
    if DEMO_DB_PATH.exists():
        DEMO_DB_PATH.unlink()
        print(f"  Removed existing database: {DEMO_DB_PATH}")
    
    # Create async engine
    engine = create_async_engine(DEMO_DATABASE_URL, echo=False)
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print(f"  Created database: {DEMO_DB_PATH}")
    return engine


def copy_sample_invoices():
    """Copy sample invoices from FinDataExtractor/data to demo storage"""
    print("\nCopying sample invoices...")
    
    if not SOURCE_INVOICE_DIR.exists():
        print(f"  ERROR: Source directory not found: {SOURCE_INVOICE_DIR}")
        print(f"  Please ensure data/sample_invoices exists in the demo project")
        return []
    
    # Create destination directory
    DEMO_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  Source: {SOURCE_INVOICE_DIR}")
    print(f"  Destination: {DEMO_STORAGE_DIR}")
    
    # Find all PDF files
    pdf_files = list(SOURCE_INVOICE_DIR.glob("*.pdf")) + list(SOURCE_INVOICE_DIR.glob("*.PDF"))
    
    if not pdf_files:
        print(f"  WARNING: No PDF files found in {SOURCE_INVOICE_DIR}")
        return []
    
    # Copy first 5 PDFs for demo (to keep it manageable)
    copied_files = []
    for pdf_file in pdf_files[:5]:
        dest_file = DEMO_STORAGE_DIR / pdf_file.name
        shutil.copy2(pdf_file, dest_file)
        copied_files.append(pdf_file.name)
        print(f"  Copied: {pdf_file.name}")
    
    print(f"  Copied {len(copied_files)} invoice files")
    return copied_files


def create_sample_invoice_data(copied_files):
    """Create sample invoice Pydantic models from copied files"""
    sample_invoices = []
    
    # Sample invoice 1: Standard invoice
    if len(copied_files) > 0:
        sample_invoices.append(Invoice(
            id="demo-inv-001",
            file_path=f"storage/raw/{copied_files[0]}",
            file_name=copied_files[0],
            upload_date=datetime(2024, 1, 15, 10, 30, 0),
            status=InvoiceState.PENDING,
            invoice_subtype=InvoiceSubtype.STANDARD_INVOICE,
            invoice_number="INV-2024-001234",
            invoice_date=date(2024, 1, 15),
            due_date=date(2024, 2, 15),
            vendor_name="Acme Office Supplies Inc.",
            vendor_address={
                "street_address": "123 Business Park Drive",
                "city": "Toronto",
                "province": "ON",
                "postal_code": "M5H 2N2",
                "country": "Canada"
            },
            customer_name="Canadian Air Transport Security Authority",
            customer_id="CATSA-001",
            subtotal=Decimal("1150.00"),
            tax_amount=Decimal("100.00"),
            total_amount=Decimal("1250.00"),
            currency="CAD",
            payment_terms="Net 30",
            po_number="PO-2024-0567",
            line_items=[
                LineItem(
                    line_number=1,
                    description="Office Chairs - Ergonomic",
                    quantity=Decimal("10"),
                    unit_price=Decimal("75.00"),
                    amount=Decimal("750.00"),
                    confidence=0.92
                ),
                LineItem(
                    line_number=2,
                    description="Desk Organizers - Set of 5",
                    quantity=Decimal("8"),
                    unit_price=Decimal("50.00"),
                    amount=Decimal("400.00"),
                    confidence=0.88
                )
            ],
            extraction_confidence=0.95,
            field_confidence={
                "invoice_number": 0.98,
                "invoice_date": 0.95,
                "vendor_name": 0.92,
                "total_amount": 0.97
            }
        ))
    
    # Sample invoice 2: Service invoice
    if len(copied_files) > 1:
        sample_invoices.append(Invoice(
            id="demo-inv-002",
            file_path=f"storage/raw/{copied_files[1]}",
            file_name=copied_files[1],
            upload_date=datetime(2024, 2, 1, 14, 15, 0),
            status=InvoiceState.PENDING,
            invoice_subtype=InvoiceSubtype.STANDARD_INVOICE,
            invoice_number="SRV-2024-005678",
            invoice_date=date(2024, 2, 1),
            due_date=date(2024, 3, 3),
            vendor_name="SecureTech Services Ltd.",
            vendor_address={
                "street_address": "456 Security Boulevard",
                "city": "Montreal",
                "province": "QC",
                "postal_code": "H3A 0G4",
                "country": "Canada"
            },
            customer_name="Canadian Air Transport Security Authority",
            customer_id="CATSA-001",
            subtotal=Decimal("3200.00"),
            tax_amount=Decimal("250.50"),
            total_amount=Decimal("3450.50"),
            currency="CAD",
            payment_terms="Net 30",
            standing_offer_number="SO-2023-1234",
            line_items=[
                LineItem(
                    line_number=1,
                    description="Security System Maintenance - Monthly",
                    quantity=Decimal("1"),
                    unit_price=Decimal("3200.00"),
                    amount=Decimal("3200.00"),
                    confidence=0.85
                )
            ],
            extraction_confidence=0.82,
            field_confidence={
                "invoice_number": 0.85,
                "invoice_date": 0.80,
                "vendor_name": 0.88,
                "total_amount": 0.82
            }
        ))
    
    # Sample invoice 3: Timesheet invoice
    if len(copied_files) > 2:
        sample_invoices.append(Invoice(
            id="demo-inv-003",
            file_path=f"storage/raw/{copied_files[2]}",
            file_name=copied_files[2],
            upload_date=datetime(2024, 2, 15, 9, 0, 0),
            status=InvoiceState.PENDING,
            invoice_subtype=InvoiceSubtype.SHIFT_SERVICE_INVOICE,
            invoice_number="TS-2024-009876",
            invoice_date=date(2024, 2, 15),
            due_date=date(2024, 3, 17),
            vendor_name="TempStaff Solutions Inc.",
            vendor_address={
                "street_address": "789 Employment Avenue",
                "city": "Vancouver",
                "province": "BC",
                "postal_code": "V6B 1A1",
                "country": "Canada"
            },
            customer_name="Canadian Air Transport Security Authority",
            customer_id="CATSA-001",
            subtotal=Decimal("5200.00"),
            tax_amount=Decimal("478.90"),
            total_amount=Decimal("5678.90"),
            currency="CAD",
            payment_terms="Net 30",
            po_number="PO-2024-0890",
            line_items=[
                LineItem(
                    line_number=1,
                    description="Security Personnel - Week 1",
                    quantity=Decimal("80"),
                    unit_price=Decimal("35.00"),
                    amount=Decimal("2800.00"),
                    confidence=0.72
                ),
                LineItem(
                    line_number=2,
                    description="Security Personnel - Week 2",
                    quantity=Decimal("80"),
                    unit_price=Decimal("35.00"),
                    amount=Decimal("2400.00"),
                    confidence=0.70
                )
            ],
            extraction_confidence=0.75,
            field_confidence={
                "invoice_number": 0.78,
                "invoice_date": 0.73,
                "vendor_name": 0.70,
                "total_amount": 0.75
            }
        ))
    
    return sample_invoices


async def populate_database(engine, sample_invoices):
    """Populate database with sample invoices"""
    print("\nPopulating database with sample invoices...")
    
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        for invoice_pydantic in sample_invoices:
            # Convert Pydantic model to DB model
            invoice_db = pydantic_to_db_invoice(invoice_pydantic)
            
            # Add to session
            session.add(invoice_db)
            print(f"  Added: {invoice_pydantic.invoice_number} ({invoice_pydantic.file_name})")
        
        # Commit all invoices
        await session.commit()
        print(f"  Committed {len(sample_invoices)} invoices to database")


async def main():
    """Main setup function"""
    print("=" * 60)
    print("FinDataExtractorDEMO Setup")
    print("=" * 60)
    print(f"\nSource invoices: {SOURCE_INVOICE_DIR}")
    print(f"Demo storage: {DEMO_STORAGE_DIR}")
    print(f"Demo database: {DEMO_DB_PATH}")
    print()
    
    # Step 1: Copy sample invoices
    copied_files = copy_sample_invoices()
    if not copied_files:
        print("\nERROR: No invoices copied. Cannot proceed.")
        return
    
    # Step 2: Setup database
    engine = await setup_database()
    
    # Step 3: Create sample invoice data
    sample_invoices = create_sample_invoice_data(copied_files)
    
    # Step 4: Populate database
    await populate_database(engine, sample_invoices)
    
    # Step 5: Cleanup
    await engine.dispose()
    
    print("\n" + "=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    print(f"\nDemo database: {DEMO_DB_PATH}")
    print(f"Sample invoices: {len(copied_files)} files in {DEMO_STORAGE_DIR}")
    print(f"Database records: {len(sample_invoices)} invoices")
    print("\nNext steps:")
    print("  1. Set DEMO_MODE=true")
    print("  2. Set DATABASE_URL=sqlite+aiosqlite:///./findataextractor_demo.db")
    print("  3. Start the demo: .\\scripts\\start_demo.ps1")


if __name__ == "__main__":
    asyncio.run(main())

