"""create_line_items_table_and_migrate_data

Revision ID: 7a7490408ff1
Revises: 20251223_add_comprehensive_invoice_fields
Create Date: 2026-01-08 13:10:33.978669

This migration:
1. Creates the line_items table with foreign key to invoices
2. Migrates existing line items from JSON column to the new table
3. Keeps the JSON column for backward compatibility (can be removed in future migration)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite
import json
from decimal import Decimal


# revision identifiers, used by Alembic.
revision = '7a7490408ff1'
down_revision = '20251223_add_fields'  # Matches revision in 20251223_add_comprehensive_invoice_fields.py
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create line_items table
    op.create_table(
        'line_items',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('invoice_id', sa.String(36), sa.ForeignKey('invoices.id', ondelete='CASCADE'), nullable=False),
        sa.Column('line_number', sa.Integer(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('quantity', sa.Numeric(18, 4), nullable=True),
        sa.Column('unit_price', sa.Numeric(18, 4), nullable=True),
        sa.Column('amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('unit_of_measure', sa.String(50), nullable=True),
        sa.Column('tax_rate', sa.Numeric(5, 4), nullable=True),
        sa.Column('tax_amount', sa.Numeric(18, 2), nullable=True),
        sa.Column('gst_amount', sa.Numeric(18, 2), nullable=True),
        sa.Column('pst_amount', sa.Numeric(18, 2), nullable=True),
        sa.Column('qst_amount', sa.Numeric(18, 2), nullable=True),
        sa.Column('combined_tax', sa.Numeric(18, 2), nullable=True),
        sa.Column('acceptance_percentage', sa.Numeric(5, 2), nullable=True),
        sa.Column('project_code', sa.String(50), nullable=True),
        sa.Column('region_code', sa.String(50), nullable=True),
        sa.Column('airport_code', sa.String(10), nullable=True),
        sa.Column('cost_centre_code', sa.String(50), nullable=True),
    )
    
    # Create indexes
    op.create_index('ix_line_items_invoice_id', 'line_items', ['invoice_id'])
    op.create_index('ix_line_items_line_number', 'line_items', ['invoice_id', 'line_number'])
    
    # Migrate data from JSON column to line_items table
    # This is done via raw SQL to handle the JSON parsing
    connection = op.get_bind()
    
    # Get all invoices with line_items JSON
    result = connection.execute(
        sa.text("SELECT id, line_items FROM invoices WHERE line_items IS NOT NULL")
    )
    
    for row in result:
        invoice_id = row[0]
        line_items_json = row[1]
        
        # Parse JSON (handle both string and already-parsed JSON)
        if isinstance(line_items_json, str):
            try:
                line_items_data = json.loads(line_items_json)
            except json.JSONDecodeError:
                continue
        else:
            line_items_data = line_items_json
        
        # Skip if not a list
        if not isinstance(line_items_data, list):
            continue
        
        # Insert each line item
        for idx, item in enumerate(line_items_data):
            if not isinstance(item, dict):
                continue
            
            # Generate UUID for line item
            import uuid
            line_item_id = str(uuid.uuid4())
            
            # Extract values with defaults
            line_number = item.get('line_number', idx + 1)
            description = item.get('description', '')
            amount = item.get('amount', '0')
            
            # Parse decimal strings to ensure proper format
            def parse_decimal(value):
                if value is None:
                    return None
                if isinstance(value, (int, float)):
                    return str(value)
                if isinstance(value, str):
                    try:
                        # Validate it's a valid decimal
                        Decimal(value)
                        return value
                    except:
                        return None
                return None
            
            # Build insert statement
            insert_stmt = sa.text("""
                INSERT INTO line_items (
                    id, invoice_id, line_number, description, quantity, unit_price,
                    amount, confidence, unit_of_measure, tax_rate, tax_amount,
                    gst_amount, pst_amount, qst_amount, combined_tax,
                    acceptance_percentage, project_code, region_code,
                    airport_code, cost_centre_code
                ) VALUES (
                    :id, :invoice_id, :line_number, :description, :quantity, :unit_price,
                    :amount, :confidence, :unit_of_measure, :tax_rate, :tax_amount,
                    :gst_amount, :pst_amount, :qst_amount, :combined_tax,
                    :acceptance_percentage, :project_code, :region_code,
                    :airport_code, :cost_centre_code
                )
            """)
            
            connection.execute(insert_stmt, {
                'id': line_item_id,
                'invoice_id': invoice_id,
                'line_number': line_number,
                'description': description,
                'quantity': parse_decimal(item.get('quantity')),
                'unit_price': parse_decimal(item.get('unit_price')),
                'amount': parse_decimal(amount) or '0',
                'confidence': item.get('confidence', 0.0),
                'unit_of_measure': item.get('unit_of_measure'),
                'tax_rate': parse_decimal(item.get('tax_rate')),
                'tax_amount': parse_decimal(item.get('tax_amount')),
                'gst_amount': parse_decimal(item.get('gst_amount')),
                'pst_amount': parse_decimal(item.get('pst_amount')),
                'qst_amount': parse_decimal(item.get('qst_amount')),
                'combined_tax': parse_decimal(item.get('combined_tax')),
                'acceptance_percentage': parse_decimal(item.get('acceptance_percentage')),
                'project_code': item.get('project_code'),
                'region_code': item.get('region_code'),
                'airport_code': item.get('airport_code'),
                'cost_centre_code': item.get('cost_centre_code'),
            })
    
    # Note: We keep the line_items JSON column for backward compatibility
    # It can be removed in a future migration after all code is updated


def downgrade() -> None:
    # Migrate data back from line_items table to JSON column
    connection = op.get_bind()
    
    # Get all invoices that have line items
    invoice_ids_result = connection.execute(
        sa.text("SELECT DISTINCT invoice_id FROM line_items")
    )
    invoice_ids = [row[0] for row in invoice_ids_result]
    
    # For each invoice, collect line items and convert to JSON
    for invoice_id in invoice_ids:
        line_items_result = connection.execute(
            sa.text("""
                SELECT line_number, description, quantity, unit_price, amount,
                       confidence, unit_of_measure, tax_rate, tax_amount,
                       gst_amount, pst_amount, qst_amount, combined_tax,
                       acceptance_percentage, project_code, region_code,
                       airport_code, cost_centre_code
                FROM line_items
                WHERE invoice_id = :invoice_id
                ORDER BY line_number
            """),
            {'invoice_id': invoice_id}
        )
        
        line_items_list = []
        for row in line_items_result:
            item_dict = {
                'line_number': row[0],
                'description': row[1] or '',
                'quantity': str(row[2]) if row[2] is not None else None,
                'unit_price': str(row[3]) if row[3] is not None else None,
                'amount': str(row[4]) if row[4] is not None else '0',
                'confidence': row[5] or 0.0,
                'unit_of_measure': row[6],
                'tax_rate': str(row[7]) if row[7] is not None else None,
                'tax_amount': str(row[8]) if row[8] is not None else None,
                'gst_amount': str(row[9]) if row[9] is not None else None,
                'pst_amount': str(row[10]) if row[10] is not None else None,
                'qst_amount': str(row[11]) if row[11] is not None else None,
                'combined_tax': str(row[12]) if row[12] is not None else None,
                'acceptance_percentage': str(row[13]) if row[13] is not None else None,
                'project_code': row[14],
                'region_code': row[15],
                'airport_code': row[16],
                'cost_centre_code': row[17],
            }
            # Remove None values to match original format
            item_dict = {k: v for k, v in item_dict.items() if v is not None}
            line_items_list.append(item_dict)
        
        # Update invoice with JSON
        update_stmt = sa.text("UPDATE invoices SET line_items = :line_items WHERE id = :invoice_id")
        connection.execute(update_stmt, {
            'invoice_id': invoice_id,
            'line_items': json.dumps(line_items_list) if line_items_list else None
        })
    
    # Drop indexes
    op.drop_index('ix_line_items_line_number', table_name='line_items')
    op.drop_index('ix_line_items_invoice_id', table_name='line_items')
    
    # Drop line_items table
    op.drop_table('line_items')

