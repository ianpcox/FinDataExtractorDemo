"""Pytest configuration and shared fixtures"""

import pytest
import os
import sys
from typing import Generator, AsyncGenerator
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import Mock, MagicMock, AsyncMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.models.database import Base
from src.models.db_models import Invoice as InvoiceDB
from src.models.invoice import Invoice, LineItem, Address, InvoiceSubtype


# Test database setup (SQLite in-memory)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False
)

TestingSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Create a fresh database session for each test
    
    Yields:
        Async database session
    """
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
    
    # Drop tables after test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def sample_invoice() -> Invoice:
    """Sample invoice Pydantic model for testing"""
    return Invoice(
        id="test-invoice-123",
        file_path="test/path/invoice.pdf",
        file_name="test_invoice.pdf",
        upload_date=datetime(2024, 1, 15, 10, 0, 0),
        status="extracted",
        invoice_number="INV-12345",
        invoice_date=date(2024, 1, 10),
        due_date=date(2024, 2, 10),
        vendor_name="Acme Corp",
        vendor_id="ACME001",
        customer_name="CATSA",
        customer_id="CATSA001",
        subtotal=Decimal("1305.00"),
        tax_amount=Decimal("195.00"),
        total_amount=Decimal("1500.00"),
        currency="CAD",
        po_number="PO-12345",
        line_items=[
            LineItem(
                line_number=1,
                description="Item A",
                quantity=Decimal("10"),
                unit_price=Decimal("100.00"),
                amount=Decimal("1000.00"),
                confidence=0.90
            ),
            LineItem(
                line_number=2,
                description="Item B",
                quantity=Decimal("5"),
                unit_price=Decimal("61.00"),
                amount=Decimal("305.00"),
                confidence=0.85
            )
        ],
        extraction_confidence=0.88,
        field_confidence={
            "invoice_id": 0.95,
            "invoice_date": 0.90,
            "vendor_name": 0.92,
            "invoice_total": 0.98
        },
        extraction_timestamp=datetime(2024, 1, 15, 10, 5, 0)
    )


@pytest.fixture
def sample_pdf_content() -> bytes:
    """Sample PDF content for testing"""
    # Minimal valid PDF
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 1\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"


@pytest.fixture
def mock_file_handler():
    """Mock FileHandler"""
    mock = MagicMock()
    mock.upload_file.return_value = {
        "file_path": "test/path/invoice.pdf",
        "blob_name": "invoices-raw/test_invoice.pdf",
        "stored_name": "test_invoice.pdf",
        "size": 1024,
        "upload_date": datetime.utcnow()
    }
    mock.download_file.return_value = b"%PDF-1.4\n..."
    mock.get_file_path.return_value = "test/path/invoice.pdf"
    return mock


@pytest.fixture
def mock_document_intelligence_client():
    """Mock DocumentIntelligenceClient"""
    mock = MagicMock()
    mock.analyze_invoice.return_value = {
        "invoice_id": "INV-12345",
        "invoice_date": "2024-01-10",
        "due_date": "2024-02-10",
        "vendor_name": "Acme Corp",
        "customer_name": "CATSA",
        "subtotal": "1305.00",
        "total_tax": "195.00",
        "invoice_total": "1500.00",
        "currency": "CAD",
        "items": [
            {
                "description": "Item A",
                "quantity": "10",
                "unit_price": "100.00",
                "amount": "1000.00",
                "confidence": 0.90
            }
        ],
        "field_confidence": {
            "invoice_id": 0.95,
            "invoice_date": 0.90,
            "vendor_name": 0.92,
            "invoice_total": 0.98
        },
        "confidence": 0.88
    }
    return mock


@pytest.fixture
def mock_pdf_processor():
    """Mock PDFProcessor"""
    mock = MagicMock()
    mock.validate_file.return_value = (True, None)
    mock.get_pdf_info.return_value = {
        "page_count": 1,
        "is_encrypted": False,
        "is_corrupted": False
    }
    return mock


@pytest.fixture
def sample_po_data():
    """Sample PO data for matching tests"""
    return {
        "id": "po-uuid-123",
        "po_number": "PO-12345",
        "po_date": "2024-01-05",
        "vendor_name": "Acme Corp",
        "vendor_code": "ACME001",
        "total_amount": 1500.00,
        "line_items": []
    }


@pytest.fixture
def sample_document_intelligence_data():
    """Sample Document Intelligence response data"""
    return {
        "invoice_id": "INV-12345",
        "invoice_date": "2024-01-10",
        "due_date": "2024-02-10",
        "vendor_name": "Acme Corp",
        "vendor_address": {
            "street_address": "123 Main St",
            "city": "Vancouver",
            "state": "BC",
            "postal_code": "V6B 1A1",
            "country_region": "Canada"
        },
        "customer_name": "CATSA",
        "customer_id": "CATSA001",
        "subtotal": "1305.00",
        "total_tax": "195.00",
        "invoice_total": "1500.00",
        "currency": "CAD",
        "payment_term": "Net 30",
        "purchase_order": "PO-12345",
        "items": [
            {
                "description": "Item A",
                "quantity": "10",
                "unit_price": "100.00",
                "amount": "1000.00",
                "unit": "EA",
                "confidence": 0.90
            }
        ],
        "field_confidence": {
            "InvoiceId": 0.95,
            "InvoiceDate": 0.90,
            "VendorName": 0.92,
            "InvoiceTotal": 0.98
        },
        "confidence": 0.88
    }

