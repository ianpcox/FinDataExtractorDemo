"""
Helper functions for saving line items to the database table.

This module provides functions to save line items to the line_items table
instead of the JSON column, supporting the migration from JSON to table-based storage.
"""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import logging
import uuid

from .invoice import LineItem as LineItemPydantic
from .line_item_db_models import LineItem as LineItemDB

logger = logging.getLogger(__name__)


async def save_line_items_to_table(
    session: AsyncSession,
    invoice_id: str,
    line_items: Optional[List[LineItemPydantic]],
) -> None:
    """
    Save line items to the line_items table.
    
    This function:
    1. Deletes existing line items for the invoice
    2. Inserts new line items from the Pydantic model
    
    Args:
        session: Database session
        invoice_id: Invoice ID
        line_items: List of LineItem Pydantic models (None or empty list to clear)
    """
    # Delete existing line items for this invoice
    await session.execute(
        delete(LineItemDB).where(LineItemDB.invoice_id == invoice_id)
    )
    
    # Insert new line items
    if line_items:
        for item in line_items:
            line_item_db = LineItemDB(
                id=str(uuid.uuid4()),
                invoice_id=invoice_id,
                line_number=item.line_number,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                amount=item.amount,
                confidence=item.confidence or 0.0,
                unit_of_measure=item.unit_of_measure,
                tax_rate=item.tax_rate,
                tax_amount=item.tax_amount,
                gst_amount=item.gst_amount,
                pst_amount=item.pst_amount,
                qst_amount=item.qst_amount,
                combined_tax=item.combined_tax,
                acceptance_percentage=item.acceptance_percentage,
                project_code=item.project_code,
                region_code=item.region_code,
                airport_code=item.airport_code,
                cost_centre_code=item.cost_centre_code,
            )
            session.add(line_item_db)
        
        logger.debug(f"Saved {len(line_items)} line items to table for invoice {invoice_id}")


async def get_line_items_from_table(
    session: AsyncSession,
    invoice_id: str,
) -> List[LineItemPydantic]:
    """
    Get line items from the line_items table.
    
    Args:
        session: Database session
        invoice_id: Invoice ID
        
    Returns:
        List of LineItem Pydantic models
    """
    result = await session.execute(
        select(LineItemDB).where(LineItemDB.invoice_id == invoice_id)
        .order_by(LineItemDB.line_number)
    )
    line_items_db = result.scalars().all()
    
    from decimal import Decimal
    return [
        LineItemPydantic(
            line_number=item.line_number,
            description=item.description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            amount=item.amount or Decimal("0"),
            confidence=item.confidence or 0.0,
            unit_of_measure=item.unit_of_measure,
            tax_rate=item.tax_rate,
            tax_amount=item.tax_amount,
            gst_amount=item.gst_amount,
            pst_amount=item.pst_amount,
            qst_amount=item.qst_amount,
            combined_tax=item.combined_tax,
            acceptance_percentage=item.acceptance_percentage,
            project_code=item.project_code,
            region_code=item.region_code,
            airport_code=item.airport_code,
            cost_centre_code=item.cost_centre_code,
        )
        for item in line_items_db
    ]
