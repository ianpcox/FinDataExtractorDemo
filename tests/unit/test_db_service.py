"""Unit tests for DatabaseService"""

import pytest
from datetime import datetime, date
from decimal import Decimal

from src.services.db_service import DatabaseService
from src.models.invoice import Invoice, LineItem


@pytest.mark.unit
@pytest.mark.requires_db
class TestDatabaseService:
    """Test DatabaseService"""
    
    @pytest.mark.asyncio
    async def test_save_invoice(
        self,
        db_session,
        sample_invoice
    ):
        """Test saving invoice to database"""
        result = await DatabaseService.save_invoice(
            invoice=sample_invoice,
            db=db_session
        )
        
        assert result is not None
        assert result.id == sample_invoice.id
        assert result.invoice_number == sample_invoice.invoice_number
        assert result.vendor_name == sample_invoice.vendor_name
    
    @pytest.mark.asyncio
    async def test_get_invoice(
        self,
        db_session,
        sample_invoice
    ):
        """Test retrieving invoice from database"""
        # Save invoice first
        await DatabaseService.save_invoice(
            invoice=sample_invoice,
            db=db_session
        )
        
        # Retrieve invoice
        retrieved = await DatabaseService.get_invoice(
            invoice_id=sample_invoice.id,
            db=db_session
        )
        
        assert retrieved is not None
        assert retrieved.id == sample_invoice.id
        assert retrieved.invoice_number == sample_invoice.invoice_number
        assert retrieved.total_amount == sample_invoice.total_amount
    
    @pytest.mark.asyncio
    async def test_get_invoice_not_found(
        self,
        db_session
    ):
        """Test retrieving non-existent invoice"""
        retrieved = await DatabaseService.get_invoice(
            invoice_id="nonexistent-id",
            db=db_session
        )
        
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_list_invoices(
        self,
        db_session,
        sample_invoice
    ):
        """Test listing invoices"""
        # Save multiple invoices
        invoice1 = sample_invoice
        invoice2 = sample_invoice.model_copy()
        invoice2.id = "test-invoice-456"
        invoice2.invoice_number = "INV-67890"
        
        await DatabaseService.save_invoice(invoice1, db=db_session)
        await DatabaseService.save_invoice(invoice2, db=db_session)
        
        # List invoices
        invoices = await DatabaseService.list_invoices(
            skip=0,
            limit=10,
            db=db_session
        )
        
        assert len(invoices) == 2
        assert invoices[0].id in [invoice1.id, invoice2.id]
    
    @pytest.mark.asyncio
    async def test_list_invoices_with_status_filter(
        self,
        db_session,
        sample_invoice
    ):
        """Test listing invoices with status filter"""
        invoice1 = sample_invoice
        invoice2 = sample_invoice.model_copy()
        invoice2.id = "test-invoice-456"
        invoice2.status = "approved"
        
        await DatabaseService.save_invoice(invoice1, db=db_session)
        await DatabaseService.save_invoice(invoice2, db=db_session)
        
        # List approved invoices
        invoices = await DatabaseService.list_invoices(
            skip=0,
            limit=10,
            status="approved",
            db=db_session
        )
        
        assert len(invoices) == 1
        assert invoices[0].status == "approved"
    
    @pytest.mark.asyncio
    async def test_update_invoice_status(
        self,
        db_session,
        sample_invoice
    ):
        """Test updating invoice status"""
        # Save invoice
        await DatabaseService.save_invoice(
            invoice=sample_invoice,
            db=db_session
        )
        
        # Update status
        result = await DatabaseService.update_invoice_status(
            invoice_id=sample_invoice.id,
            status="approved",
            db=db_session
        )
        
        assert result is True
        
        # Verify status was updated
        updated = await DatabaseService.get_invoice(
            invoice_id=sample_invoice.id,
            db=db_session
        )
        assert updated.status == "approved"

