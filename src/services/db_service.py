"""Simplified async database service for invoice persistence"""

from typing import Optional, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from src.models.database import AsyncSessionLocal, get_db
from src.models.invoice import Invoice as InvoicePydantic
from src.models.db_models import Invoice as InvoiceDB
from src.models.db_utils import (
    pydantic_to_db_invoice,
    db_to_pydantic_invoice,
    address_to_dict,
    line_items_to_json,
    _sanitize_tax_breakdown,
)
from src.models.invoice import InvoiceState

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

            def _get_fields_set(model) -> set:
                if hasattr(model, "model_fields_set"):
                    return set(model.model_fields_set)
                return set(getattr(model, "__fields_set__", set()))

            def _is_empty_collection(val) -> bool:
                return isinstance(val, (list, dict)) and len(val) == 0

            def _convert(field_name: str, val):
                if field_name in ["vendor_address", "bill_to_address", "remit_to_address"]:
                    return address_to_dict(val)
                if field_name == "line_items":
                    return line_items_to_json(val)
                if field_name == "tax_breakdown":
                    return _sanitize_tax_breakdown(val)
                if field_name == "invoice_subtype" and hasattr(val, "value"):
                    return val.value
                if field_name == "extensions" and hasattr(val, "dict"):
                    return val.dict()
                return val

            if existing_invoice:
                # Update existing invoice with conservative patch semantics
                logger.info(f"Updating existing invoice: {invoice.id}")
                fields_set = _get_fields_set(invoice)
                # If caller provided no explicit fields, do nothing
                update_candidates = fields_set or set()

                updates_applied = False
                for field_name in update_candidates:
                    if field_name in ["id", "created_at", "updated_at"]:
                        continue
                    if not hasattr(existing_invoice, field_name):
                        # skip unknown fields
                        continue
                    val = getattr(invoice, field_name, None)
                    if val is None or _is_empty_collection(val):
                        continue
                    converted = _convert(field_name, val)
                    setattr(existing_invoice, field_name, converted)
                    updates_applied = True

                if updates_applied:
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
    async def claim_for_extraction(
        invoice_id: str,
        db: Optional[AsyncSession] = None,
    ) -> bool:
        """
        Attempt to claim an invoice for extraction. Returns True if claimed, False otherwise.
        Allowed transitions: PENDING/FAILED -> PROCESSING. """
        return await DatabaseService.transition_state(
            invoice_id=invoice_id,
            from_states={InvoiceState.PENDING.value, InvoiceState.FAILED.value},
            to_state=InvoiceState.PROCESSING.value,
            error_on_invalid=False,
            db=db,
        )

    @staticmethod
    async def set_extraction_result(
        invoice_id: str,
        patch: dict,
        expected_processing_state: str = "PROCESSING",
        db: Optional[AsyncSession] = None,
    ) -> bool:
        """
        Apply extraction result atomically if processing_state matches expected.
        """
        session = db or AsyncSessionLocal()
        should_close = db is None
        try:
            patch = patch.copy()
            patch["processing_state"] = InvoiceState.EXTRACTED.value
            patch["status"] = InvoiceState.EXTRACTED.value
            patch["updated_at"] = datetime.utcnow()
            result = await session.execute(
                select(InvoiceDB).where(
                    InvoiceDB.id == invoice_id,
                    InvoiceDB.processing_state == expected_processing_state,
                )
            )
            inv = result.scalar_one_or_none()
            if not inv:
                return False
            for key, val in patch.items():
                if not hasattr(inv, key):
                    continue
                setattr(inv, key, val)
            await session.commit()
            return True
        except Exception as e:
            await session.rollback()
            logger.error(f"Error setting extraction result for {invoice_id}: {e}", exc_info=True)
            raise ValueError(f"Failed to set extraction result for {invoice_id}") from e
        finally:
            if should_close:
                await session.close()

    @staticmethod
    async def set_extraction_failed(
        invoice_id: str,
        error_summary: str,
        db: Optional[AsyncSession] = None,
    ) -> None:
        session = db or AsyncSessionLocal()
        should_close = db is None
        try:
            result = await session.execute(select(InvoiceDB).where(InvoiceDB.id == invoice_id))
            inv = result.scalar_one_or_none()
            if inv:
                inv.processing_state = InvoiceState.FAILED.value
                inv.status = InvoiceState.FAILED.value
                inv.updated_at = datetime.utcnow()
                inv.review_notes = error_summary
                await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Error marking extraction failed for {invoice_id}: {e}", exc_info=True)
        finally:
            if should_close:
                await session.close()

    @staticmethod
    async def get_state(invoice_id: str, db: Optional[AsyncSession] = None) -> Optional[str]:
        session = db or AsyncSessionLocal()
        should_close = db is None
        try:
            result = await session.execute(select(InvoiceDB.processing_state).where(InvoiceDB.id == invoice_id))
            row = result.scalar_one_or_none()
            return row
        except Exception as e:
            logger.error(f"Error fetching state for invoice {invoice_id}: {e}", exc_info=True)
            raise
        finally:
            if should_close:
                await session.close()

    @staticmethod
    async def transition_state(
        invoice_id: str,
        from_states: set[str],
        to_state: str,
        error_on_invalid: bool = True,
        db: Optional[AsyncSession] = None,
    ) -> bool:
        """
        Atomic state transition using UPDATE statement with WHERE clause.
        Returns True if transitioned, False otherwise.
        """
        from sqlalchemy import update
        
        session = db or AsyncSessionLocal()
        should_close = db is None
        try:
            # Use atomic UPDATE with WHERE clause (no SELECT-then-UPDATE race)
            stmt = (
                update(InvoiceDB)
                .where(
                    InvoiceDB.id == invoice_id,
                    InvoiceDB.processing_state.in_(list(from_states)),
                )
                .values(
                    processing_state=to_state,
                    status=to_state,
                    updated_at=datetime.utcnow(),
                )
            )
            result = await session.execute(stmt)
            await session.commit()
            
            rows_affected = result.rowcount
            if rows_affected == 0:
                if error_on_invalid:
                    current = await DatabaseService.get_state(invoice_id, db=session)
                    raise ValueError(
                        f"Invalid state transition invoice={invoice_id} current={current} -> {to_state}"
                    )
                return False
            return True
        except Exception as e:
            await session.rollback()
            logger.error(f"State transition failed for {invoice_id}: {e}", exc_info=True)
            if error_on_invalid and not isinstance(e, ValueError):
                raise
            if not error_on_invalid:
                return False
            raise
        finally:
            if should_close:
                await session.close()

    @staticmethod
    async def update_with_review_version(
        invoice_id: str,
        patch: dict,
        expected_review_version: int,
        db: Optional[AsyncSession] = None,
    ) -> bool:
        """
        Atomic optimistic-locking update using single-statement guarded UPDATE.
        Updates fields and increments review_version by 1 only if current review_version
        matches expected_review_version.
        Returns True if updated, False if stale write (caller must treat as 409 STALE_WRITE).
        """
        from sqlalchemy import update
        
        session = db or AsyncSessionLocal()
        should_close = db is None
        try:
            # Sanitize patch: never allow these fields to be patched
            patch = patch.copy()
            patch.pop("id", None)
            patch.pop("created_at", None)
            patch.pop("review_version", None)
            patch.pop("processing_state", None)  # HITL should not change processing state
            
            # Filter patch to only include valid InvoiceDB columns
            valid_patch = {}
            for key, val in patch.items():
                if hasattr(InvoiceDB, key):
                    valid_patch[key] = val
                else:
                    logger.warning(f"Ignoring invalid patch field for InvoiceDB: {key}")
            
            # Use atomic UPDATE with WHERE clause (no SELECT-then-UPDATE race)
            # Increment review_version in the same statement
            stmt = (
                update(InvoiceDB)
                .where(
                    InvoiceDB.id == invoice_id,
                    InvoiceDB.review_version == expected_review_version,
                )
                .values(
                    **valid_patch,
                    review_version=InvoiceDB.review_version + 1,  # Atomic increment
                    updated_at=datetime.utcnow(),  # Explicit for bulk UPDATE
                )
            )
            result = await session.execute(stmt)
            await session.commit()
            
            return (result.rowcount or 0) > 0  # True if updated, False if stale
        except Exception as e:
            await session.rollback()
            logger.error(f"Optimistic update failed for invoice {invoice_id}: {e}", exc_info=True)
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

