"""Simplified matching service for invoice to PO matching"""

from typing import List, Optional, Dict
from datetime import datetime, date
from decimal import Decimal
from dataclasses import dataclass
from enum import Enum
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from src.models.database import AsyncSessionLocal
from src.models.invoice import Invoice as InvoicePydantic
from src.services.db_service import DatabaseService

logger = logging.getLogger(__name__)


class MatchStrategy(str, Enum):
    """Matching strategy types"""
    EXACT = "exact"  # Exact match on PO number
    FUZZY = "fuzzy"  # Fuzzy match on vendor, amount, date
    HYBRID = "hybrid"  # Combination of strategies


@dataclass
class MatchResult:
    """Result of a matching operation"""
    source_document_id: str
    source_document_type: str  # "invoice"
    matched_document_id: str
    matched_document_type: str  # "po"
    matched_document_number: Optional[str]
    confidence: float
    match_strategy: MatchStrategy
    match_details: Dict
    created_at: datetime


@dataclass
class MatchCriteria:
    """Criteria for matching documents"""
    # Tolerance settings
    amount_tolerance_percent: float = 0.05  # 5% tolerance for amounts
    amount_tolerance_absolute: Decimal = Decimal("10.00")  # $10 absolute tolerance
    date_tolerance_days: int = 30  # 30 days tolerance for dates
    
    # Matching weights (must sum to 1.0)
    weight_po_number: float = 0.40
    weight_vendor: float = 0.30
    weight_amount: float = 0.20
    weight_date: float = 0.10
    
    # Minimum confidence threshold
    min_confidence: float = 0.70


class MatchingService:
    """Simplified service for matching invoices to purchase orders"""
    
    def __init__(self, db: Optional[AsyncSession] = None):
        """
        Initialize matching service
        
        Args:
            db: Async database session (optional, creates new if not provided)
        """
        self.db = db
        self.criteria = MatchCriteria()
    
    async def match_invoice_to_po(
        self,
        invoice_id: str,
        po_number: Optional[str] = None,
        po_data: Optional[Dict] = None
    ) -> List[MatchResult]:
        """
        Match an invoice to a purchase order
        
        Args:
            invoice_id: Invoice ID to match
            po_number: Optional PO number to match against (if None, will search)
            po_data: Optional PO data dict (if PO is in separate DB/storage)
            
        Returns:
            List of MatchResult objects
        """
        # Get invoice from database
        invoice = await DatabaseService.get_invoice(invoice_id, db=self.db)
        if not invoice:
            logger.error(f"Invoice not found: {invoice_id}")
            return []
        
        # If PO data is provided (from separate storage), match directly
        if po_data:
            match_result = self._match_invoice_po_data(invoice, po_data)
            if match_result and match_result.confidence >= self.criteria.min_confidence:
                return [match_result]
            return []
        
        # If PO number is provided, try to find PO
        if po_number:
            # For vanilla version, we'll need to query PO from separate storage
            # For now, create a match result based on PO number match
            match_result = self._match_invoice_po_by_number(invoice, po_number)
            if match_result and match_result.confidence >= self.criteria.min_confidence:
                return [match_result]
            return []
        
        # If invoice has PO number, match on that
        if invoice.po_number:
            match_result = self._match_invoice_po_by_number(invoice, invoice.po_number)
            if match_result and match_result.confidence >= self.criteria.min_confidence:
                return [match_result]
        
        return []
    
    def _match_invoice_po_data(
        self,
        invoice: InvoicePydantic,
        po_data: Dict
    ) -> Optional[MatchResult]:
        """
        Match invoice to PO data (from separate storage)
        
        Args:
            invoice: Invoice Pydantic model
            po_data: PO data dictionary with fields:
                - po_number
                - po_date
                - vendor_name
                - vendor_code
                - total_amount
                - line_items (optional)
        """
        confidence_scores = {}
        match_details = {}
        
        # 1. PO Number match (exact)
        if invoice.po_number and po_data.get("po_number"):
            po_match = invoice.po_number == po_data["po_number"]
            confidence_scores['po_number'] = 1.0 if po_match else 0.0
            match_details['po_number_match'] = po_match
        else:
            confidence_scores['po_number'] = 0.0
            match_details['po_number_match'] = None
        
        # 2. Vendor match
        vendor_match = False
        if invoice.vendor_id and po_data.get("vendor_code"):
            vendor_match = invoice.vendor_id == po_data["vendor_code"]
        elif invoice.vendor_name and po_data.get("vendor_name"):
            vendor_match = invoice.vendor_name.lower().strip() == po_data["vendor_name"].lower().strip()
        
        confidence_scores['vendor'] = 1.0 if vendor_match else 0.0
        match_details['vendor_match'] = vendor_match
        
        # 3. Amount match (with tolerance)
        amount_match_score = 0.0
        if invoice.total_amount and po_data.get("total_amount"):
            po_amount = Decimal(str(po_data["total_amount"]))
            amount_diff = abs(invoice.total_amount - po_amount)
            amount_diff_percent = float(amount_diff / po_amount) if po_amount > 0 else 1.0
            
            if amount_diff <= self.criteria.amount_tolerance_absolute:
                amount_match_score = 1.0
            elif amount_diff_percent <= self.criteria.amount_tolerance_percent:
                amount_match_score = 1.0 - (amount_diff_percent / self.criteria.amount_tolerance_percent) * 0.5
            else:
                amount_match_score = max(0.0, 1.0 - amount_diff_percent)
            
            match_details['amount_diff'] = float(amount_diff)
            match_details['amount_diff_percent'] = amount_diff_percent
        else:
            match_details['amount_match'] = None
        
        confidence_scores['amount'] = amount_match_score
        
        # 4. Date match (invoice date should be after PO date)
        date_match_score = 0.0
        if invoice.invoice_date and po_data.get("po_date"):
            po_date = po_data["po_date"]
            if isinstance(po_date, str):
                from dateutil.parser import parse
                po_date = parse(po_date).date()
            elif isinstance(po_date, datetime):
                po_date = po_date.date()
            
            days_diff = (invoice.invoice_date - po_date).days
            if days_diff >= 0 and days_diff <= self.criteria.date_tolerance_days:
                date_match_score = 1.0 - (days_diff / self.criteria.date_tolerance_days) * 0.3
            else:
                date_match_score = max(0.0, 1.0 - abs(days_diff) / 365.0)
            
            match_details['date_diff_days'] = days_diff
        else:
            match_details['date_match'] = None
        
        confidence_scores['date'] = date_match_score
        
        # Calculate weighted confidence
        total_confidence = (
            confidence_scores['po_number'] * self.criteria.weight_po_number +
            confidence_scores['vendor'] * self.criteria.weight_vendor +
            confidence_scores['amount'] * self.criteria.weight_amount +
            confidence_scores['date'] * self.criteria.weight_date
        )
        
        match_details['confidence_breakdown'] = confidence_scores
        
        # Determine strategy
        if confidence_scores['po_number'] == 1.0:
            strategy = MatchStrategy.EXACT
        elif confidence_scores['po_number'] > 0.0:
            strategy = MatchStrategy.HYBRID
        else:
            strategy = MatchStrategy.FUZZY
        
        return MatchResult(
            source_document_id=invoice.id,
            source_document_type="invoice",
            matched_document_id=po_data.get("id", po_data.get("po_number", "unknown")),
            matched_document_type="po",
            matched_document_number=po_data.get("po_number"),
            confidence=total_confidence,
            match_strategy=strategy,
            match_details=match_details,
            created_at=datetime.utcnow()
        )
    
    def _match_invoice_po_by_number(
        self,
        invoice: InvoicePydantic,
        po_number: str
    ) -> Optional[MatchResult]:
        """
        Match invoice to PO by PO number only (simplified)
        
        This is used when we only have the PO number but not full PO data.
        For full matching, PO data should be provided via _match_invoice_po_data.
        """
        # Check if invoice PO number matches
        if invoice.po_number == po_number:
            return MatchResult(
                source_document_id=invoice.id,
                source_document_type="invoice",
                matched_document_id=po_number,  # Use PO number as ID
                matched_document_type="po",
                matched_document_number=po_number,
                confidence=0.85,  # High confidence for exact PO number match
                match_strategy=MatchStrategy.EXACT,
                match_details={
                    'po_number_match': True,
                    'note': 'PO data not available - match based on PO number only'
                },
                created_at=datetime.utcnow()
            )
        
        return None

