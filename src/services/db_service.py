"""Simplified async database service for invoice persistence"""

from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from src.models.database import AsyncSessionLocal, get_db
from src.models.invoice import Invoice as InvoicePydantic
from src.models.db_models import Invoice as InvoiceDB
from src.models.db_utils import pydantic_to_db_invoice, db_to_pydantic_invoice

logger = logging.getLogger(__name__)


class DatabaseService:
    """Simplified async service for database operations"""
    
    @staticmethod
    async def save_invoice(
        invoice: InvoicePydantic,
        db: Optional[AsyncSession] = None
    ) -> InvoiceDB:
        """
        Save invoice to database
        
        Args:
            invoice: Pydantic Invoice model
            db: Async database session (optional, creates new if not provided)
            
        Returns:
            SQLAlchemy Invoice model
        """
        if db:
            session = db
            should_close = False
        else:
            session = AsyncSessionLocal()
            should_close = True
        
        try:
            # Check if invoice already exists
            result = await session.execute(
                select(InvoiceDB).where(InvoiceDB.id == invoice.id)
            )
            existing_invoice = result.scalar_one_or_none()
            
            if existing_invoice:
                # Update existing invoice
                logger.info(f"Updating existing invoice: {invoice.id}")
                db_invoice = pydantic_to_db_invoice(invoice)
                
                # Update fields
                for key, value in db_invoice.__dict__.items():
                    if not key.startswith('_') and key != 'id':
                        setattr(existing_invoice, key, value)
                
                existing_invoice.updated_at = datetime.utcnow()
                db_invoice = existing_invoice
            else:
                # Create new invoice
                logger.info(f"Creating new invoice: {invoice.id}")
                db_invoice = pydantic_to_db_invoice(invoice)
                session.add(db_invoice)
            
            await session.commit()
            await session.refresh(db_invoice)
            
            logger.info(f"Invoice saved to database: {invoice.id}")
            return db_invoice
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error saving invoice {invoice.id}: {e}", exc_info=True)
            raise
        finally:
            if should_close:
                await session.close()
    
    @staticmethod
    async def get_invoice(
        invoice_id: str,
        db: Optional[AsyncSession] = None
    ) -> Optional[InvoicePydantic]:
        """
        Get invoice from database
        
        Args:
            invoice_id: Invoice ID
            db: Async database session (optional)
            
        Returns:
            Pydantic Invoice model or None if not found
        """
        if db:
            session = db
            should_close = False
        else:
            session = AsyncSessionLocal()
            should_close = True
        
        try:
            result = await session.execute(
                select(InvoiceDB).where(InvoiceDB.id == invoice_id)
            )
            db_invoice = result.scalar_one_or_none()
            
            if db_invoice:
                return db_to_pydantic_invoice(db_invoice)
            return None
            
        except Exception as e:
            logger.error(f"Error getting invoice {invoice_id}: {e}", exc_info=True)
            raise
        finally:
            if should_close:
                await session.close()
    
    @staticmethod
    async def list_invoices(
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> List[InvoicePydantic]:
        """
        List invoices from database
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Optional status filter
            db: Async database session (optional)
            
        Returns:
            List of Pydantic Invoice models
        """
        if db:
            session = db
            should_close = False
        else:
            session = AsyncSessionLocal()
            should_close = True
        
        try:
            query = select(InvoiceDB)
            
            if status:
                query = query.where(InvoiceDB.status == status)
            
            query = query.order_by(InvoiceDB.upload_date.desc())
            query = query.offset(skip).limit(limit)
            
            result = await session.execute(query)
            db_invoices = result.scalars().all()
            
            return [db_to_pydantic_invoice(inv) for inv in db_invoices]
            
        except Exception as e:
            logger.error(f"Error listing invoices: {e}", exc_info=True)
            raise
        finally:
            if should_close:
                await session.close()
    
    @staticmethod
    async def update_invoice_status(
        invoice_id: str,
        status: str,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """
        Update invoice status
        
        Args:
            invoice_id: Invoice ID
            status: New status
            db: Async database session (optional)
            
        Returns:
            True if updated, False if not found
        """
        if db:
            session = db
            should_close = False
        else:
            session = AsyncSessionLocal()
            should_close = True
        
        try:
            result = await session.execute(
                select(InvoiceDB).where(InvoiceDB.id == invoice_id)
            )
            db_invoice = result.scalar_one_or_none()
            
            if not db_invoice:
                return False
            
            db_invoice.status = status
            db_invoice.updated_at = datetime.utcnow()
            
            await session.commit()
            return True
            
        except Exception as e:
            await session.rollback()
            logger.error(f"Error updating invoice status {invoice_id}: {e}", exc_info=True)
            raise
        finally:
            if should_close:
                await session.close()

