"""Simplified extraction service with field extractor and database integration"""

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, date
from decimal import Decimal
import logging
import json
import re
import hashlib
from typing import Any, Mapping, Dict
import time
import asyncio
from collections import OrderedDict

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from .document_intelligence_client import DocumentIntelligenceClient
from .field_extractor import FieldExtractor
from src.ingestion.file_handler import FileHandler
from src.models.invoice import Invoice
from src.services.db_service import DatabaseService
from src.services.validation_service import ValidationService
from src.models.db_utils import address_to_dict, line_items_to_json, _sanitize_tax_breakdown
from src.services.progress_tracker import progress_tracker, ProcessingStep
from src.config import settings
try:
    from openai import AzureOpenAI, AsyncAzureOpenAI
    from openai import RateLimitError, APIError
except ImportError:
    AzureOpenAI = None
    AsyncAzureOpenAI = None
    RateLimitError = None
    APIError = None

logger = logging.getLogger(__name__)


class TTLCache:
    """Simple in-memory cache with TTL and size limits using LRU eviction."""
    
    def __init__(self, ttl_seconds: int = 3600, max_size: int = 1000):
        """
        Initialize cache with TTL and size limits.
        
        Args:
            ttl_seconds: Time-to-live for cache entries in seconds (default: 1 hour)
            max_size: Maximum number of entries in cache (default: 1000)
        """
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        # OrderedDict maintains insertion order for LRU eviction
        self._cache: OrderedDict = OrderedDict()
        self._timestamps: Dict[Any, float] = {}
    
    def get(self, key: Any) -> Optional[str]:
        """
        Get value from cache if it exists and hasn't expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        if key not in self._cache:
            return None
        
        # Check if entry has expired
        if key in self._timestamps:
            age = time.time() - self._timestamps[key]
            if age > self.ttl_seconds:
                # Expired - remove it
                self._cache.pop(key, None)
                self._timestamps.pop(key, None)
                return None
        
        # Move to end (most recently used) for LRU
        value = self._cache.pop(key)
        self._cache[key] = value
        return value
    
    def set(self, key: Any, value: str) -> None:
        """
        Set value in cache with current timestamp.
        Evicts oldest entries if cache is full.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        # Remove if already exists (will be re-added at end)
        if key in self._cache:
            self._cache.pop(key)
            self._timestamps.pop(key, None)
        
        # Evict oldest entries if at capacity
        while len(self._cache) >= self.max_size:
            oldest_key = next(iter(self._cache))
            self._cache.pop(oldest_key)
            self._timestamps.pop(oldest_key, None)
        
        # Add new entry
        self._cache[key] = value
        self._timestamps[key] = time.time()
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        self._timestamps.clear()
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache.
        
        Returns:
            Number of entries removed
        """
        current_time = time.time()
        expired_keys = [
            key for key, timestamp in self._timestamps.items()
            if current_time - timestamp > self.ttl_seconds
        ]
        
        for key in expired_keys:
            self._cache.pop(key, None)
            self._timestamps.pop(key, None)
        
        return len(expired_keys)
    
    def size(self) -> int:
        """Get current number of entries in cache."""
        return len(self._cache)


# Canonical field names - single source of truth
CANONICAL_FIELDS = {
    # Header
    "invoice_number", "invoice_date", "due_date", "invoice_type", "reference_number",
    # Vendor
    "vendor_name", "vendor_id", "vendor_phone", "vendor_fax", "vendor_email", 
    "vendor_website", "vendor_address",
    # Vendor Tax IDs
    "gst_number", "qst_number", "pst_number", "business_number",
    # Customer
    "customer_name", "customer_id", "customer_phone", "customer_email", 
    "customer_fax", "bill_to_address",
    # Remit-To
    "remit_to_address", "remit_to_name",
    # Contract
    "entity", "contract_id", "standing_offer_number", "po_number",
    # Dates
    "period_start", "period_end", "shipping_date", "delivery_date",
    # Financial
    "subtotal", "discount_amount", "shipping_amount", "handling_fee", "deposit_amount",
    # Canadian Taxes
    "gst_amount", "gst_rate", "hst_amount", "hst_rate", 
    "qst_amount", "qst_rate", "pst_amount", "pst_rate",
    # Total
    "tax_amount", "total_amount", "currency", "tax_breakdown",
    # Payment
    "payment_terms", "payment_method", "payment_due_upon", 
    "acceptance_percentage", "tax_registration_number",
}

LLM_SYSTEM_PROMPT = """
You are a specialized invoice extraction QA assistant for CATSA.

You receive:
- A JSON object `di_payload` that contains the extracted invoice fields and their values, using the canonical field names expected by downstream systems.
- A JSON object `field_confidence` with per-field confidence scores from the upstream extractor.
- A JSON array `low_conf_fields` listing the subset of fields that the upstream model is uncertain about.
- Optionally, a short OCR text snippet from the invoice PDF.

Your task:
1. For each field in `low_conf_fields`, decide whether the value in `di_payload` is correct.
2. If it is clearly wrong or missing, infer a corrected value using ONLY the provided JSON and OCR snippet.
3. NEVER invent fields, change field names, or guess values that are not strongly supported by the data.
4. If you cannot reliably correct a field, set it to null.
5. Output ONLY a single JSON object whose keys are exactly the field names from `low_conf_fields`, with their corrected (or null) values.
6. Do NOT include explanations, comments, or extra properties.

CANONICAL FIELD NAMES (use these EXACTLY):
Header: invoice_number, invoice_date, due_date, invoice_type, reference_number
Vendor: vendor_name, vendor_id, vendor_phone, vendor_fax, vendor_email, vendor_website, vendor_address
Vendor Tax IDs: gst_number, qst_number, pst_number, business_number
Customer: customer_name, customer_id, customer_phone, customer_email, customer_fax, bill_to_address
Remit-To: remit_to_address, remit_to_name
Contract: entity, contract_id, standing_offer_number, po_number
Dates: period_start, period_end, shipping_date, delivery_date
Financial: subtotal, discount_amount, shipping_amount, handling_fee, deposit_amount
Canadian Taxes: gst_amount, gst_rate, hst_amount, hst_rate, qst_amount, qst_rate, pst_amount, pst_rate
Total: tax_amount, total_amount, currency
Payment: payment_terms, payment_method, payment_due_upon, acceptance_percentage, tax_registration_number

Formatting rules:
- Dates must be ISO 8601 date strings: "YYYY-MM-DD".
- Monetary amounts must be numeric strings, using "." as the decimal separator (e.g., "1234.56").
- Trim whitespace and normalize casing where appropriate, but do not rewrite vendor names beyond obvious OCR fixes.
- For address fields (vendor_address, bill_to_address, remit_to_address), return an object with keys: street, city, province, postal_code, country. Use null or empty for unknown subfields.
"""


class ExtractionService:
    """Service for extracting data from invoice PDFs"""
    
    def __init__(
        self,
        doc_intelligence_client: Optional[DocumentIntelligenceClient] = None,
        file_handler: Optional[FileHandler] = None,
        field_extractor: Optional[FieldExtractor] = None
    ):
        """
        Initialize extraction service
        
        Args:
            doc_intelligence_client: DocumentIntelligenceClient instance
            file_handler: FileHandler instance
            field_extractor: FieldExtractor instance
        """
        self.doc_intelligence_client = (
            doc_intelligence_client or DocumentIntelligenceClient()
        )
        self.file_handler = file_handler or FileHandler()
        self.field_extractor = field_extractor or FieldExtractor()
        self.validation_service = ValidationService()
        # In-memory cache with TTL and size limits to avoid re-spending tokens for identical requests
        cache_ttl = getattr(settings, "LLM_CACHE_TTL_SECONDS", 3600)
        cache_max_size = getattr(settings, "LLM_CACHE_MAX_SIZE", 1000)
        self._llm_cache = TTLCache(ttl_seconds=cache_ttl, max_size=cache_max_size)
    
    async def extract_invoice(
        self,
        invoice_id: str,
        file_identifier: str,
        file_name: str,
        upload_date: datetime,
        db: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        Extract data from an invoice PDF
        
        Args:
            invoice_id: Unique invoice ID
            file_identifier: File path (local) or blob name (Azure)
            file_name: Original file name
            upload_date: Upload timestamp
            db: Optional async DB session (uses default if not provided)
            
        Returns:
            Dictionary with extraction result
        """
        errors = []
        
        try:
            logger.info(f"Starting extraction for invoice: {invoice_id}")

            claimed = await DatabaseService.claim_for_extraction(invoice_id)
            if not claimed:
                return {
                    "invoice_id": invoice_id,
                    "status": "conflict",
                    "errors": ["Invoice is already processing"],
                }
            
            # Step 1: Download PDF
            logger.info(f"Downloading PDF: {file_identifier}")
            file_content = await run_in_threadpool(self.file_handler.download_file, file_identifier)
            
            if not file_content:
                errors.append("Failed to download file")
                return {
                    "invoice_id": invoice_id,
                    "status": "error",
                    "errors": errors
                }
            
            # Step 2: Analyze with Document Intelligence
            logger.info(f"Analyzing invoice with Document Intelligence: {invoice_id}")
            doc_intelligence_data = await run_in_threadpool(
                self.doc_intelligence_client.analyze_invoice,
                file_content,
            )
            
            if not doc_intelligence_data or doc_intelligence_data.get("error"):
                errors.append(
                    doc_intelligence_data.get("error", "Document Intelligence analysis failed")
                )
                return {
                    "invoice_id": invoice_id,
                    "status": "upstream_error",
                    "errors": errors
                }
            
            # Step 3: Extract text for subtype detection (optional, for better subtype extraction)
            invoice_text = None  # Could extract from PDF if needed
            
            # Step 4: Map to Invoice model using FieldExtractor
            logger.info(f"Mapping extracted data to Invoice model: {invoice_id}")
            file_path = self.file_handler.get_file_path(file_identifier)
            
            invoice = self.field_extractor.extract_invoice(
                doc_intelligence_data=doc_intelligence_data,
                file_path=file_path,
                file_name=file_name,
                upload_date=upload_date,
                invoice_text=doc_intelligence_data.get("content") or invoice_text
            )
            invoice.id = invoice_id
            invoice.status = "extracted"
            
            await progress_tracker.update(invoice_id, 70, "Fields mapped, saving to database...")
            
            # Step 5: Save to database
            logger.info(f"Saving extracted invoice to database: {invoice_id}")
            patch = self._invoice_to_patch(invoice)
            ok = await DatabaseService.set_extraction_result(invoice_id, patch, db=db)
            if not ok:
                raise ValueError("Failed to persist extraction result; state mismatch")
            
            await progress_tracker.update(invoice_id, 75, "Extraction complete, checking for LLM evaluation...")
            await progress_tracker.complete_step(invoice_id, ProcessingStep.EXTRACTION, "Extraction complete")
            
            # Prepare JSON-serializable payload
            invoice_dict = invoice.model_dump(mode="json")
            extraction_ts = invoice.extraction_timestamp.isoformat() if invoice.extraction_timestamp else None

            # Low-confidence fallback: trigger when required fields are missing or low,
            # and when any field is explicitly low or blank/"Not Extracted".
            low_conf_threshold = getattr(settings, "LLM_LOW_CONF_THRESHOLD", 0.75)
            low_conf_fields: List[str] = []
            fc = invoice.field_confidence or {}

            def _is_blank(value: Any) -> bool:
                if value is None:
                    return True
                if isinstance(value, str):
                    return value.strip() == "" or value.strip().lower() == "not extracted"
                if isinstance(value, (list, dict)):
                    return len(value) == 0
                return False

            required = [
                "invoice_number",
                "invoice_date",
                "vendor_name",
                "total_amount",
                "vendor_address",
                "bill_to_address",
                "remit_to_address",
            ]
            for field in required:
                val = getattr(invoice, field, None)
                conf = fc.get(field)
                if _is_blank(val) or conf is None or conf < low_conf_threshold:
                    low_conf_fields.append(field)

            # Include any blank/"Not Extracted" fields across the invoice payload,
            # even if they don't have an explicit confidence score.
            invoice_payload = invoice.model_dump()
            excluded_fields = {
                "id",
                "created_at",
                "updated_at",
                "upload_date",
                "extraction_timestamp",
                "status",
                "processing_state",
                "extraction_confidence",
                "field_confidence",
            }
            for field, value in invoice_payload.items():
                if field in excluded_fields:
                    continue
                if _is_blank(value):
                    low_conf_fields.append(field)

            for name, conf in fc.items():
                if name in required:
                    continue
                if conf is None or conf < low_conf_threshold:
                    low_conf_fields.append(name)

            # Deduplicate while preserving order
            seen = set()
            low_conf_fields = [x for x in low_conf_fields if not (x in seen or seen.add(x))]

            llm_changed = False
            # Skip LLM fallback in demo mode or if disabled
            if settings.DEMO_MODE or not getattr(settings, "USE_LLM_FALLBACK", False):
                if low_conf_fields:
                    logger.info("Demo mode or LLM disabled - skipping LLM fallback for %d low-confidence fields", len(low_conf_fields))
                await progress_tracker.update(invoice_id, 100, "No LLM evaluation needed (demo mode or disabled)")
            elif not low_conf_fields:
                logger.info("No fields below low_conf_threshold=%.2f, skipping LLM fallback", low_conf_threshold)
                await progress_tracker.update(invoice_id, 100, "No LLM evaluation needed")
            else:
                aoai_ready = self._has_aoai_config()
                use_llm = bool(getattr(settings, "USE_LLM_FALLBACK", False))
                use_demo_llm = settings.DEMO_MODE and not aoai_ready

                # Check for address fields specifically
                address_fields = [f for f in low_conf_fields if f in {"vendor_address", "bill_to_address", "remit_to_address"}]
                if address_fields:
                    logger.info("Address fields with low confidence detected: %s", address_fields)

                if not use_llm and not use_demo_llm:
                    logger.warning("LLM fallback disabled; skipping %d low-confidence fields (including %d address fields: %s)", 
                                 len(low_conf_fields), len(address_fields), address_fields if address_fields else "none")
                    if address_fields:
                        logger.warning("ADDRESSES WILL NOT BE EXTRACTED: LLM fallback is disabled and addresses have low confidence")
                    await progress_tracker.update(invoice_id, 100, f"LLM evaluation disabled - {len(low_conf_fields)} fields skipped")
                else:
                    await progress_tracker.start(
                        invoice_id,
                        ProcessingStep.LLM_EVALUATION,
                        f"Evaluating {len(low_conf_fields)} low-confidence fields with LLM...",
                    )
                    await progress_tracker.update(
                        invoice_id,
                        75,
                        f"Starting {'mock' if use_demo_llm else 'LLM'} evaluation for {len(low_conf_fields)} fields...",
                    )
                    invoice_before_llm = invoice.model_dump(mode="json")
                    llm_error_details = []
                    try:
                        if use_demo_llm:
                            self._run_mock_llm_fallback(
                                invoice,
                                low_conf_fields,
                                doc_intelligence_data,
                                fc,
                            )
                        else:
                            llm_result = await self._run_low_confidence_fallback(
                                invoice,
                                low_conf_fields,
                                doc_intelligence_data,
                                fc,
                                invoice_id=invoice_id,
                            )
                            # Log per-group results
                            if llm_result:
                                groups_succeeded = llm_result.get("groups_succeeded", 0)
                                groups_failed = llm_result.get("groups_failed", 0)
                                overall_success = llm_result.get("success", False)
                                
                                if groups_succeeded > 0:
                                    logger.info(
                                        f"LLM fallback partial success: {groups_succeeded} groups succeeded, "
                                        f"{groups_failed} groups failed for invoice {invoice_id}"
                                    )
                                    # Log failed groups for debugging
                                    for grp_name, result in llm_result.get("group_results", {}).items():
                                        if not result.get("success"):
                                            logger.warning(
                                                f"LLM group '{grp_name}' failed: {result.get('error', 'Unknown error')}"
                                            )
                                
                                if groups_failed > 0 and groups_succeeded == 0:
                                    # All groups failed - this is a complete failure
                                    failed_groups = [
                                        f"{name}: {r.get('error', 'Unknown')}"
                                        for name, r in llm_result.get("group_results", {}).items()
                                        if not r.get("success")
                                    ]
                                    error_summary = f"LLM evaluation failed for all {groups_failed} groups"
                                    if failed_groups:
                                        error_summary += f": {', '.join(failed_groups[:3])}"
                                    await progress_tracker.error(invoice_id, error_summary, ProcessingStep.LLM_EVALUATION)
                                elif overall_success:
                                    # At least one group succeeded
                                    await progress_tracker.complete_step(
                                        invoice_id, 
                                        ProcessingStep.LLM_EVALUATION, 
                                        f"LLM evaluation complete ({groups_succeeded} groups succeeded, {groups_failed} failed)"
                                    )
                        
                        llm_changed = invoice.model_dump(mode="json") != invoice_before_llm
                        if llm_changed:
                            await progress_tracker.update(invoice_id, 95, "LLM evaluation complete - fields updated")
                        else:
                            await progress_tracker.update(invoice_id, 95, "LLM evaluation complete - no changes")
                        
                        # Only mark as complete if we haven't already marked it as error
                        if llm_result and llm_result.get("groups_succeeded", 0) > 0:
                            await progress_tracker.complete_step(invoice_id, ProcessingStep.LLM_EVALUATION, "LLM evaluation complete")
                    except Exception as e:
                        error_msg = str(e)
                        # Extract more details from the error
                        if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                            error_msg = f"HTTP {e.response.status_code}: {error_msg}"
                        if hasattr(e, 'response') and hasattr(e.response, 'url'):
                            error_msg += f" (URL: {e.response.url})"
                        # Check if addresses were affected
                        address_fields_affected = [f for f in low_conf_fields if f in {"vendor_address", "bill_to_address", "remit_to_address"}]
                        if address_fields_affected:
                            logger.error("LLM FAILED FOR ADDRESSES: invoice %s - Address fields NOT evaluated: %s. Error: %s", 
                                       invoice_id, address_fields_affected, error_msg, exc_info=True)
                        else:
                            logger.error("LLM fallback failed for invoice %s: %s. Low-confidence fields that were NOT evaluated: %s", 
                                       invoice_id, error_msg, low_conf_fields, exc_info=True)
                        
                        error_summary = f"LLM evaluation failed: {error_msg}"
                        if address_fields_affected:
                            error_summary += f" | ADDRESSES MISSING: {', '.join(address_fields_affected)}"
                        error_summary += f" | Fields not evaluated: {', '.join(low_conf_fields[:5])}{'...' if len(low_conf_fields) > 5 else ''}"
                        await progress_tracker.error(invoice_id, error_summary, ProcessingStep.LLM_EVALUATION)
                        # Store error details for later retrieval
                        llm_error_details.append({
                            "error": error_msg,
                            "fields_affected": low_conf_fields,
                            "endpoint": aoai_endpoint if not use_demo_llm else "mock",
                            "deployment": settings.AOAI_DEPLOYMENT_NAME if not use_demo_llm else "mock"
                        })

            # Final save after LLM post-processing only when there was a change
            if llm_changed:
                logger.info("Saving extracted invoice to database (after LLM) for: %s", invoice_id)
                await progress_tracker.update(invoice_id, 98, "Saving LLM-enhanced results...")
                patch = self._invoice_to_patch(invoice)
                # After initial extraction, state is EXTRACTED, so we need to update with that expectation
                ok2 = await DatabaseService.set_extraction_result(invoice_id, patch, expected_processing_state="EXTRACTED", db=db)
                if not ok2:
                    raise ValueError("Failed to persist post-LLM extraction result; state mismatch")
            else:
                logger.info("Skipping post-LLM save; no LLM changes detected.")
            invoice_dict = invoice.model_dump(mode="json")

            # Run business rule validation
            validation_result = self.validation_service.validate(invoice)
            logger.info(
                f"Invoice {invoice_id} validation: {validation_result['passed_rules']}/{validation_result['total_rules']} rules passed"
            )

            result = {
                "invoice_id": invoice_id,
                "status": "extracted",
                "invoice": invoice_dict,
                "confidence": invoice.extraction_confidence,
                "field_confidence": invoice.field_confidence,
                "extraction_timestamp": extraction_ts,
                "errors": [],
                "low_confidence_fields": low_conf_fields,
                "low_confidence_triggered": bool(low_conf_fields),
                "validation": validation_result
            }
            
            logger.info(f"Extraction completed successfully for invoice: {invoice_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error extracting invoice {invoice_id}: {e}", exc_info=True)
            errors.append(str(e))
            await DatabaseService.set_extraction_failed(invoice_id, "; ".join(errors), db=db)
            return {
                "invoice_id": invoice_id,
                "status": "error",
                "errors": errors
            }
    
    async def run_ai_extraction(
        self,
        invoice_id: str,
        confidence_threshold: float = 0.7,
        db: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Manually trigger AI extraction for low-confidence fields
        
        Args:
            invoice_id: Invoice ID to improve
            confidence_threshold: Minimum confidence threshold (fields below will be processed)
            db: Optional async DB session
            
        Returns:
            Dictionary with AI extraction results
        """
        try:
            logger.info(f"Starting manual AI extraction for invoice: {invoice_id}")
            
            # Get current invoice from database
            invoice_dict = await DatabaseService.get_invoice(invoice_id, db=db)
            if not invoice_dict:
                return {
                    "invoice_id": invoice_id,
                    "status": "error",
                    "errors": ["Invoice not found"]
                }
            
            # Convert to Invoice model
            invoice = Invoice(**invoice_dict)
            
            # Get field confidence
            fc = invoice.field_confidence or {}
            
            # Identify low-confidence fields
            low_conf_fields = []
            for field_name, confidence in fc.items():
                if confidence is not None and confidence < confidence_threshold:
                    low_conf_fields.append(field_name)
            
            # Also check required fields with no value or confidence
            required = [
                "invoice_number", "invoice_date", "vendor_name", "total_amount",
                "vendor_address", "bill_to_address", "remit_to_address",
            ]
            for field in required:
                val = getattr(invoice, field, None)
                conf = fc.get(field)
                if (val in (None, "", {}) or conf is None or conf < confidence_threshold) and field not in low_conf_fields:
                    low_conf_fields.append(field)
            
            if not low_conf_fields:
                logger.info(f"No low-confidence fields found for invoice {invoice_id}")
                return {
                    "invoice_id": invoice_id,
                    "status": "success",
                    "message": "All fields have sufficient confidence",
                    "fields_improved": 0,
                    "low_confidence_fields": []
                }
            
            logger.info(f"Processing {len(low_conf_fields)} low-confidence fields: {low_conf_fields}")
            
            # Get original DI data - we need the content for LLM context
            # For now, we'll work with what we have in the invoice
            # TODO: Store original DI data with bounding boxes for better LLM context
            di_data = {
                "content": invoice_dict.get("content") or "",
                "invoice_number": invoice.invoice_number,
                "vendor_name": invoice.vendor_name,
                "total_amount": str(invoice.total_amount) if invoice.total_amount else None,
            }
            
            # Store before state
            invoice_before = invoice.model_dump(mode="json")
            
            # Run LLM fallback
            await self._run_low_confidence_fallback(
                invoice,
                low_conf_fields,
                di_data,
                fc,
                invoice_id=invoice_id,
            )
            
            # Check what changed
            invoice_after = invoice.model_dump(mode="json")
            fields_improved = []
            for field in low_conf_fields:
                before_val = invoice_before.get(field)
                after_val = invoice_after.get(field)
                if before_val != after_val:
                    fields_improved.append(field)
            
            # Save updated invoice
            if fields_improved:
                logger.info(f"AI extraction improved {len(fields_improved)} fields: {fields_improved}")
                patch = self._invoice_to_patch(invoice)
                ok = await DatabaseService.set_extraction_result(invoice_id, patch, db=db)
                if not ok:
                    raise ValueError("Failed to persist AI extraction result")
            else:
                logger.info("AI extraction did not improve any fields")
            
            return {
                "invoice_id": invoice_id,
                "status": "success",
                "fields_improved": len(fields_improved),
                "improved_fields": fields_improved,
                "low_confidence_fields": low_conf_fields,
                "invoice": invoice.model_dump(mode="json")
            }
            
        except Exception as e:
            logger.error(f"Error in AI extraction for {invoice_id}: {e}", exc_info=True)
            return {
                "invoice_id": invoice_id,
                "status": "error",
                "errors": [str(e)]
            }
    
    async def _run_low_confidence_fallback(
        self,
        invoice: Invoice,
        low_conf_fields: List[str],
        di_data: Dict[str, Any],
        di_field_confidence: Optional[Dict[str, float]] = None,
        invoice_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run LLM fallback to refine low-confidence fields. Best-effort and non-blocking. Async version.
        
        Args:
            invoice: Invoice object to update
            low_conf_fields: List of low-confidence field names
            di_data: Document Intelligence raw data
            di_field_confidence: Optional field confidence dict
            invoice_id: Optional invoice ID for progress tracking
        
        Returns:
            Dict with keys:
                - success: bool - True if at least one group succeeded
                - groups_processed: int - Number of groups processed
                - groups_succeeded: int - Number of groups that succeeded
                - groups_failed: int - Number of groups that failed
                - group_results: Dict[str, Dict] - Per-group results with 'success', 'fields', 'error' keys
        """
        logger.info("Running LLM fallback for low confidence fields: %s", low_conf_fields)

        if not low_conf_fields:
            logger.info("No low-confidence fields to refine; skipping LLM fallback.")
            return {
                "success": False,
                "groups_processed": 0,
                "groups_succeeded": 0,
                "groups_failed": 0,
                "group_results": {},
            }

        if not getattr(settings, "USE_LLM_FALLBACK", False):
            logger.info("LLM fallback disabled via settings; skipping.")
            return {
                "success": False,
                "groups_processed": 0,
                "groups_succeeded": 0,
                "groups_failed": 0,
                "group_results": {},
            }

        if AsyncAzureOpenAI is None:
            logger.warning("openai package not installed; skipping LLM fallback.")
            return {
                "success": False,
                "groups_processed": 0,
                "groups_succeeded": 0,
                "groups_failed": 0,
                "group_results": {},
            }

        if not settings.AOAI_ENDPOINT or not settings.AOAI_API_KEY or not settings.AOAI_DEPLOYMENT_NAME:
            logger.warning("AOAI config missing; skipping LLM fallback.")
            logger.warning("AOAI_ENDPOINT: %s, AOAI_API_KEY: %s, AOAI_DEPLOYMENT_NAME: %s", 
                          bool(settings.AOAI_ENDPOINT), bool(settings.AOAI_API_KEY), bool(settings.AOAI_DEPLOYMENT_NAME))
            return {
                "success": False,
                "groups_processed": 0,
                "groups_succeeded": 0,
                "groups_failed": 0,
                "group_results": {},
            }
        
        # Normalize endpoint (remove trailing slash if present)
        aoai_endpoint = settings.AOAI_ENDPOINT.rstrip('/')

        # Cleanup expired cache entries periodically (every 10th call)
        if hasattr(self, '_llm_cache_call_count'):
            self._llm_cache_call_count += 1
        else:
            self._llm_cache_call_count = 1
        
        if self._llm_cache_call_count % 10 == 0:
            expired_count = self._llm_cache.cleanup_expired()
            if expired_count > 0:
                logger.debug(f"Cleaned up {expired_count} expired cache entries. Cache size: {self._llm_cache.size()}")

        try:
            # group fields to reduce payload; process sequentially with small jitter
            fc = di_field_confidence or {}
            groups = [
                (
                    "fields",
                    {
                        "invoice_number", "invoice_date", "due_date", "invoice_type", "reference_number",
                        "vendor_name", "vendor_id", "vendor_phone", "vendor_fax", "vendor_email", "vendor_website",
                        "customer_name", "customer_id", "customer_phone", "customer_email", "customer_fax",
                        "subtotal", "tax_amount", "total_amount",
                        "currency", "payment_terms", "payment_method", "payment_due_upon",
                        "acceptance_percentage", "tax_registration_number",
                        "entity", "contract_id", "standing_offer_number", "po_number",
                        "period_start", "period_end", "shipping_date", "delivery_date",
                        "discount_amount", "shipping_amount", "handling_fee", "deposit_amount",
                        "gst_number", "qst_number", "pst_number", "business_number",
                        "remit_to_name",
                    },
                ),
                ("addresses", {"vendor_address", "bill_to_address", "remit_to_address"}),
                (
                    "canadian_taxes",
                    {
                        "gst_amount", "gst_rate",
                        "hst_amount", "hst_rate",
                        "qst_amount", "qst_rate",
                        "pst_amount", "pst_rate",
                    },
                ),
                ("line_items", {f for f in low_conf_fields if f.startswith("line_items")}),
            ]

            # Prepare sanitized DI snapshot for caching (common)
            di_snapshot_base = {
                "di_fields": di_data or {},
                "di_field_confidence": fc,
            }
            try:
                canonical_di = self.field_extractor.normalize_di_data(di_data or {})
            except Exception:
                canonical_di = di_data or {}

            # Track per-group results
            group_results: Dict[str, Dict[str, Any]] = {}
            groups_succeeded = 0
            groups_failed = 0
            
            # Progress update task for long-running LLM calls
            progress_task = None
            if invoice_id:
                async def send_progress_updates():
                    """Send periodic progress updates during LLM calls"""
                    update_interval = 7  # Update every 7 seconds
                    base_progress = 75
                    max_progress = 94
                    iteration = 0
                    
                    while True:
                        await asyncio.sleep(update_interval)
                        iteration += 1
                        # Gradually increase progress, but cap at max_progress
                        progress = min(base_progress + (iteration * 2), max_progress)
                        await progress_tracker.update(
                            invoice_id,
                            progress,
                            f"LLM evaluation in progress... (processing group {iteration})",
                            ProcessingStep.LLM_EVALUATION
                        )
                
                progress_task = asyncio.create_task(send_progress_updates())

            for idx, (grp_name, grp_fields) in enumerate(groups):
                sub_fields = [f for f in low_conf_fields if f in grp_fields]
                if not sub_fields:
                    continue

                # Initialize group result tracking
                group_results[grp_name] = {
                    "success": False,
                    "fields": sub_fields,
                    "error": None,
                }

                di_snapshot = dict(di_snapshot_base)
                di_snapshot["low_conf_fields"] = sub_fields
                di_snapshot = self._sanitize_for_json(di_snapshot)

                prompt = self._build_llm_prompt(canonical_di, sub_fields, di_data)
                if not prompt:
                    logger.info("No prompt built for group %s; skipping.", grp_name)
                    group_results[grp_name]["error"] = "No prompt built"
                    groups_failed += 1
                    continue

                cache_key = (
                    settings.AOAI_DEPLOYMENT_NAME or "",
                    tuple(sorted(sub_fields)),
                    invoice.file_name or invoice.id or "",
                    json.dumps(di_snapshot, sort_keys=True),
                )

                suggestion_text = self._llm_cache.get(cache_key)
                if suggestion_text is None:
                    logger.info(
                        "Calling Azure OpenAI chat.completions for group %s. Endpoint: %s, Deployment: %s, API Version: %s",
                        grp_name,
                        aoai_endpoint,
                        settings.AOAI_DEPLOYMENT_NAME,
                        settings.AOAI_API_VERSION
                    )
                    
                    client = AsyncAzureOpenAI(
                        api_key=settings.AOAI_API_KEY,
                        api_version=settings.AOAI_API_VERSION,
                        azure_endpoint=aoai_endpoint,
                    )
                    
                    # Retry logic for OpenAI calls
                    max_retries = 3
                    initial_delay = 1.0
                    max_delay = 60.0
                    exponential_base = 2.0
                    resp = None
                    
                    # Update progress before starting LLM call
                    if invoice_id and idx == 0:
                        await progress_tracker.update(
                            invoice_id,
                            78,
                            f"Calling LLM for group '{grp_name}' ({len(sub_fields)} fields)...",
                            ProcessingStep.LLM_EVALUATION
                        )
                    
                    for attempt in range(max_retries + 1):
                        try:
                            # Update progress during retry attempts
                            if invoice_id and attempt > 0:
                                await progress_tracker.update(
                                    invoice_id,
                                    80,
                                    f"Retrying LLM call for group '{grp_name}' (attempt {attempt + 1}/{max_retries + 1})...",
                                    ProcessingStep.LLM_EVALUATION
                                )
                            
                            resp = await client.chat.completions.create(
                                model=settings.AOAI_DEPLOYMENT_NAME,
                                temperature=0.0,
                                messages=[
                                    {"role": "system", "content": LLM_SYSTEM_PROMPT},
                                    {"role": "user", "content": prompt},
                                ],
                            )
                            break  # Success, exit retry loop
                            
                        except Exception as call_err:
                            status = getattr(call_err, "status_code", None)
                            
                            # Rate limit error (429) - always retry with backoff
                            if status == 429 or (RateLimitError and isinstance(call_err, RateLimitError)):
                                if attempt < max_retries:
                                    delay = min(initial_delay * (exponential_base ** attempt), max_delay)
                                    # Try to get retry_after from error if available
                                    try:
                                        retry_after = getattr(call_err, "retry_after", None)
                                        if retry_after:
                                            delay = max(delay, float(retry_after))
                                    except (ValueError, AttributeError):
                                        pass
                                    
                                    logger.warning(
                                        f"LLM fallback hit rate limit (429) on group {grp_name}, "
                                        f"attempt {attempt + 1}/{max_retries}, backing off for {delay:.2f}s"
                                    )
                                    await asyncio.sleep(delay)
                                    continue
                                else:
                                    logger.warning("LLM fallback hit rate limit (429) on group %s after max retries; stopping further LLM calls.", grp_name)
                                    break
                            
                            # Other API errors - retry if not max attempts
                            elif APIError and isinstance(call_err, APIError) and attempt < max_retries:
                                delay = min(initial_delay * (exponential_base ** attempt), max_delay)
                                error_msg = str(call_err)
                                if hasattr(call_err, 'response') and hasattr(call_err.response, 'url'):
                                    error_msg += f" (URL: {call_err.response.url})"
                                logger.warning(
                                    f"LLM fallback API error on group {grp_name}, "
                                    f"attempt {attempt + 1}/{max_retries}: {error_msg}, retrying in {delay:.2f}s"
                                )
                                await asyncio.sleep(delay)
                                continue
                            
                            # Non-retryable error or max retries reached
                            error_msg = str(call_err)
                            if hasattr(call_err, 'response') and hasattr(call_err.response, 'url'):
                                error_msg += f" (URL: {call_err.response.url})"
                            logger.error("LLM fallback call failed for group %s: %s. Endpoint: %s, Deployment: %s", 
                                       grp_name, error_msg, aoai_endpoint, settings.AOAI_DEPLOYMENT_NAME, exc_info=True)
                            # Mark group as failed
                            group_results[grp_name]["error"] = error_msg
                            groups_failed += 1
                            resp = None  # Ensure resp is None to trigger failure handling
                            break
                    else:
                        # All retries exhausted without success
                        error_msg = "All retries exhausted"
                        logger.error("LLM fallback exhausted all retries for group %s", grp_name)
                        group_results[grp_name]["error"] = error_msg
                        groups_failed += 1
                        resp = None  # Ensure resp is None to trigger failure handling
                        continue

                    if resp is None:
                        # Already handled above, but double-check
                        if group_results[grp_name].get("error") is None:
                            error_msg = "No response received"
                            logger.error("LLM fallback failed: no response received for group %s", grp_name)
                            group_results[grp_name]["error"] = error_msg
                            groups_failed += 1
                        continue

                    if not resp.choices or not resp.choices[0].message or not resp.choices[0].message.content:
                        error_msg = "No content in response"
                        logger.warning("LLM fallback returned no content for group %s; skipping.", grp_name)
                        group_results[grp_name]["error"] = error_msg
                        groups_failed += 1
                        continue

                    suggestion_text = resp.choices[0].message.content.strip()
                    self._llm_cache.set(cache_key, suggestion_text)

                llm_data = self._coerce_llm_json(suggestion_text)
                if llm_data is None:
                    logger.error("LLM fallback returned non-JSON content for group %s; skipping.", grp_name)
                    logger.debug("Raw LLM suggestion text: %s", suggestion_text)
                    continue

                if not isinstance(llm_data, dict):
                    logger.error("LLM fallback JSON is not an object for group %s; got %s", grp_name, type(llm_data))
                    logger.debug("Raw LLM suggestion text: %s", suggestion_text)
                    continue

                self._apply_llm_suggestions(invoice, llm_data, sub_fields)
                logger.info("LLM fallback suggestions applied successfully for group %s.", grp_name)
                group_results[grp_name]["success"] = True
                groups_succeeded += 1
                
                # Update progress after successful group
                if invoice_id:
                    total_groups = len([g for g in groups if any(f in low_conf_fields for f in g[1])])
                    if total_groups > 0:
                        progress_pct = 75 + int((groups_succeeded / total_groups) * 15)  # 75-90% range
                        await progress_tracker.update(
                            invoice_id,
                            progress_pct,
                            f"Completed group '{grp_name}' ({groups_succeeded}/{total_groups} groups done)...",
                            ProcessingStep.LLM_EVALUATION
                        )

        except Exception as e:
            error_msg = f"Unexpected error in LLM fallback: {str(e)}"
            logger.exception("LLM fallback failed: %s", e)
            # Mark all remaining groups as failed
            for grp_name, result in group_results.items():
                if not result["success"] and result["error"] is None:
                    result["error"] = error_msg
                    groups_failed += 1
        finally:
            # Cancel progress update task if it's still running
            if progress_task and not progress_task.done():
                progress_task.cancel()
                try:
                    await progress_task
                except asyncio.CancelledError:
                    pass
        
        # Return results summary
        groups_processed = len(group_results)
        overall_success = groups_succeeded > 0
        
        return {
            "success": overall_success,
            "groups_processed": groups_processed,
            "groups_succeeded": groups_succeeded,
            "groups_failed": groups_failed,
            "group_results": group_results,
        }

    def _run_mock_llm_fallback(
        self,
        invoice: Invoice,
        low_conf_fields: List[str],
        di_data: Dict[str, Any],
        di_field_confidence: Optional[Dict[str, float]] = None,
    ) -> None:
        """Demo-mode LLM fallback that uses deterministic heuristics (no external calls)."""
        logger.info("Running mock LLM fallback for low confidence fields: %s", low_conf_fields)
        if not low_conf_fields:
            return

        canonical = self.field_extractor.normalize_di_data(di_data or {})
        di_raw = di_data or {}

        def _first_value(*values):
            for val in values:
                if val not in (None, "", {}):
                    return val
            return None

        def _promote_confidence(field_name: str, original_value: Any = None, new_value: Any = None) -> None:
            if invoice.field_confidence is None:
                invoice.field_confidence = {}
            current = invoice.field_confidence.get(field_name, 0.0)
            
            # Use dynamic confidence calculation if we have context
            if original_value is not None or new_value is not None:
                calculated = self._calculate_llm_confidence(
                    field_name,
                    original_value,
                    new_value,
                    current,
                )
                invoice.field_confidence[field_name] = calculated
            else:
                # Fallback: use max of current or 0.85 (slightly lower than 0.9 for mock LLM)
                invoice.field_confidence[field_name] = max(float(current or 0.0), 0.85)

        for field in low_conf_fields:
            try:
                # Get original value for confidence calculation
                original_value = getattr(invoice, field, None)
                
                if field in {"vendor_address", "bill_to_address", "remit_to_address"}:
                    addr_data = _first_value(canonical.get(field), di_raw.get(field))
                    if addr_data:
                        new_value = self.field_extractor._map_address(addr_data)
                        setattr(invoice, field, new_value)
                        _promote_confidence(field, original_value, new_value)
                    continue

                if field in {"invoice_date", "due_date", "period_start", "period_end"}:
                    parsed = self.field_extractor._parse_date(canonical.get(field))
                    if parsed:
                        setattr(invoice, field, parsed)
                        _promote_confidence(field, original_value, parsed)
                    continue

                if field in {"subtotal", "tax_amount", "total_amount", "acceptance_percentage"}:
                    parsed = self.field_extractor._parse_decimal(canonical.get(field))
                    if parsed is not None:
                        setattr(invoice, field, parsed)
                        _promote_confidence(field, original_value, parsed)
                    continue

                candidate = _first_value(
                    canonical.get(field),
                    di_raw.get(field),
                    di_raw.get("invoice_id") if field == "invoice_number" else None,
                    di_raw.get("InvoiceId") if field == "invoice_number" else None,
                    di_raw.get("purchase_order") if field == "po_number" else None,
                    di_raw.get("PurchaseOrder") if field == "po_number" else None,
                    di_raw.get("payment_term") if field == "payment_terms" else None,
                    di_raw.get("PaymentTerm") if field == "payment_terms" else None,
                )
                if candidate not in (None, "", {}):
                    setattr(invoice, field, candidate)
                    _promote_confidence(field, original_value, candidate)
            except Exception as err:
                logger.warning("Mock LLM fallback skipped field %s: %s", field, err)

        try:
            if invoice.field_confidence:
                invoice.extraction_confidence = self.field_extractor._calculate_overall_confidence(
                    invoice.field_confidence
                )
        except Exception:
            pass

    def _has_aoai_config(self) -> bool:
        """Return True if AOAI client/config is available for real LLM fallback."""
        return bool(
            AsyncAzureOpenAI is not None
            and settings.AOAI_ENDPOINT
            and settings.AOAI_API_KEY
            and settings.AOAI_DEPLOYMENT_NAME
        )

    def _build_llm_prompt(
        self,
        canonical_di: Dict[str, Any],
        low_conf_fields: list[str],
        di_raw: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Build a JSON-safe prompt payload for the LLM, focusing ONLY on low-confidence fields.
        """
        if not canonical_di or not low_conf_fields:
            return ""

        # Only include the fields the DI model is unsure about
        minimal = {k: canonical_di.get(k) for k in low_conf_fields}

        # Make sure there are no date/Decimal/etc. objects
        sanitized = self._sanitize_for_json(minimal)

        payload = {
            "low_confidence_fields": low_conf_fields,
            "fields": sanitized,
        }

        snippet = self._build_content_snippet(di_raw or {}, low_conf_fields)
        if snippet:
            payload["ocr_snippet"] = snippet

        # This string is what you send as the LLM "input"
        prefix = f"Low-confidence fields: {', '.join(low_conf_fields)}\n"
        return prefix + json.dumps(payload, ensure_ascii=False, default=str)

    def _build_content_snippet(self, di_data: Dict[str, Any], low_conf_fields: Optional[List[str]] = None) -> str:
        """
        Extract an intelligent OCR snippet that includes relevant context.
        
        Strategy:
        1. For multi-page documents: Include first page, middle page(s), and last page
        2. For single-page or content string: Include beginning, middle, and end sections
        3. Prioritize content that might contain the low-confidence fields
        
        Args:
            di_data: Document Intelligence data with 'pages' or 'content'
            low_conf_fields: Optional list of low-confidence field names for context-aware selection
            
        Returns:
            OCR snippet string with improved context coverage
        """
        try:
            max_chars = getattr(settings, "LLM_OCR_SNIPPET_MAX_CHARS", 3000)
            
            pages = di_data.get("pages")
            if isinstance(pages, list) and pages:
                num_pages = len(pages)
                
                if num_pages == 1:
                    # Single page: include beginning, middle, and end
                    page_content = str(pages[0])
                    if len(page_content) <= max_chars:
                        return page_content
                    
                    # Split into beginning, middle, and end
                    chunk_size = max_chars // 3
                    head = page_content[:chunk_size]
                    middle_start = len(page_content) // 2 - chunk_size // 2
                    middle = page_content[middle_start:middle_start + chunk_size]
                    tail = page_content[-chunk_size:]
                    return f"{head}\n...\n{middle}\n...\n{tail}"
                
                elif num_pages == 2:
                    # Two pages: include beginning of first, end of last, and middle section
                    first_page = str(pages[0])
                    last_page = str(pages[1])
                    chunk_size = max_chars // 3
                    
                    head = first_page[:chunk_size]
                    # Get middle from end of first page and beginning of last page
                    first_tail = first_page[-chunk_size//2:] if len(first_page) > chunk_size//2 else first_page
                    last_head = last_page[:chunk_size//2] if len(last_page) > chunk_size//2 else last_page
                    middle = first_tail + "\n" + last_head
                    tail = last_page[-chunk_size:] if len(last_page) > chunk_size else last_page
                    return f"{head}\n...\n{middle}\n...\n{tail}"
                
                else:
                    # Multiple pages: include first, middle page(s), and last
                    first_page = str(pages[0])
                    last_page = str(pages[-1])
                    
                    # Calculate chunk sizes
                    chunk_size = max_chars // 4  # Reserve space for separators
                    
                    # First page (beginning)
                    head = first_page[:chunk_size]
                    
                    # Middle page(s) - include one or two middle pages
                    middle_pages = []
                    if num_pages >= 3:
                        # Include middle page
                        mid_idx = num_pages // 2
                        middle_pages.append(str(pages[mid_idx]))
                    if num_pages >= 5:
                        # Include pages around middle
                        mid_idx1 = num_pages // 3
                        mid_idx2 = (num_pages * 2) // 3
                        if mid_idx1 != mid_idx and mid_idx2 != mid_idx:
                            middle_pages.append(str(pages[mid_idx1]))
                            middle_pages.append(str(pages[mid_idx2]))
                    
                    # Combine middle pages, taking chunks from each
                    middle_chunk_size = chunk_size // max(len(middle_pages), 1) if middle_pages else chunk_size
                    middle_sections = []
                    for mid_page in middle_pages[:2]:  # Limit to 2 middle pages
                        if len(mid_page) > middle_chunk_size:
                            # Take beginning and end of middle page
                            mid_head = mid_page[:middle_chunk_size//2]
                            mid_tail = mid_page[-middle_chunk_size//2:]
                            middle_sections.append(f"{mid_head}...{mid_tail}")
                        else:
                            middle_sections.append(mid_page)
                    middle = "\n".join(middle_sections) if middle_sections else ""
                    
                    # Last page (end)
                    tail = last_page[-chunk_size:] if len(last_page) > chunk_size else last_page
                    
                    parts = [head]
                    if middle:
                        parts.append(f"...\n{middle}\n...")
                    parts.append(tail)
                    return "\n".join(parts)
            
            # Fallback: use raw content string
            raw_content = str(di_data.get("content", ""))
            if len(raw_content) <= max_chars:
                return raw_content
            
            # Split content into beginning, middle, and end
            chunk_size = max_chars // 3
            head = raw_content[:chunk_size]
            middle_start = len(raw_content) // 2 - chunk_size // 2
            middle = raw_content[middle_start:middle_start + chunk_size]
            tail = raw_content[-chunk_size:]
            return f"{head}\n...\n{middle}\n...\n{tail}"
            
        except Exception as e:
            logger.warning(f"Error building content snippet: {e}")
            return ""

    def _calculate_llm_confidence(
        self,
        field_name: str,
        original_value: Any,
        new_value: Any,
        original_confidence: Optional[float],
    ) -> float:
        """
        Calculate confidence score for LLM-corrected field based on context.
        
        Factors considered:
        - Original value was null/blank: Higher confidence (0.85-0.95) - LLM filled in missing data
        - Original value existed but was wrong: Medium confidence (0.75-0.85) - LLM corrected existing data
        - Original value matches new value: Lower confidence (0.70-0.80) - LLM confirmed existing value
        - Original confidence was very low (<0.5): Higher confidence boost - LLM improved low-confidence field
        
        Args:
            field_name: Name of the field
            original_value: Original value before LLM correction
            new_value: New value from LLM
            original_confidence: Original confidence score (if available)
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        def _is_blank(value: Any) -> bool:
            """Check if value is blank/null/not extracted"""
            if value is None:
                return True
            if isinstance(value, str):
                return value.strip() == "" or value.strip().lower() == "not extracted"
            if isinstance(value, (list, dict)):
                return len(value) == 0
            return False
        
        original_was_blank = _is_blank(original_value)
        new_is_blank = _is_blank(new_value)
        value_changed = original_value != new_value
        
        # Base confidence ranges
        if original_was_blank and not new_is_blank:
            # LLM filled in a blank field - high confidence
            base_confidence = 0.90
        elif value_changed and not original_was_blank:
            # LLM corrected an existing (wrong) value - medium-high confidence
            base_confidence = 0.80
        elif not value_changed and not original_was_blank:
            # LLM confirmed existing value - medium confidence
            base_confidence = 0.75
        elif new_is_blank:
            # LLM set to null/blank - lower confidence (might be intentional)
            base_confidence = 0.70
        else:
            # Default case
            base_confidence = 0.80
        
        # Adjust based on original confidence
        if original_confidence is not None:
            if original_confidence < 0.5:
                # Original was very low confidence - LLM improvement is more significant
                base_confidence = min(0.95, base_confidence + 0.05)
            elif original_confidence > 0.85:
                # Original was already high - LLM confirmation is less significant
                base_confidence = max(0.70, base_confidence - 0.05)
        
        # Field-specific adjustments
        # Critical fields get slight confidence boost if filled from blank
        critical_fields = {"invoice_number", "invoice_date", "total_amount", "vendor_name"}
        if field_name in critical_fields and original_was_blank and not new_is_blank:
            base_confidence = min(0.95, base_confidence + 0.03)
        
        # Ensure confidence is within valid range
        return max(0.0, min(1.0, base_confidence))
    
    def _validate_llm_suggestion(
        self,
        field_name: str,
        value: Any,
        invoice: Invoice,
        original_value: Any = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate an LLM suggestion before applying it.
        
        Args:
            field_name: Name of the field
            value: Suggested value from LLM
            invoice: Current invoice object (for context)
            original_value: Original value before LLM suggestion
            
        Returns:
            (is_valid, error_message) - is_valid is False if value should be rejected
        """
        from datetime import date, datetime
        from decimal import Decimal, InvalidOperation
        
        # Allow null values (LLM may intentionally set to null)
        if value is None:
            return (True, None)
        
        # Date field validations
        date_fields = {
            "invoice_date", "due_date", "period_start", "period_end",
            "shipping_date", "delivery_date"
        }
        if field_name in date_fields:
            try:
                if isinstance(value, str):
                    from dateutil.parser import parse
                    parsed_date = parse(value).date()
                elif isinstance(value, date):
                    parsed_date = value
                elif isinstance(value, datetime):
                    parsed_date = value.date()
                else:
                    return (False, f"Invalid date format for {field_name}: {value}")
                
                # Check if date is in the future (with 1 year buffer for reasonable invoices)
                today = date.today()
                max_future_date = date(today.year + 1, 12, 31)
                if parsed_date > max_future_date:
                    return (False, f"Date {parsed_date} is too far in the future for {field_name}")
                
                # Check date logic relative to other dates
                if field_name == "due_date" and invoice.invoice_date:
                    if parsed_date < invoice.invoice_date:
                        return (False, f"Due date {parsed_date} is before invoice date {invoice.invoice_date}")
                
                if field_name == "period_end" and invoice.period_start:
                    if parsed_date < invoice.period_start:
                        return (False, f"Period end {parsed_date} is before period start {invoice.period_start}")
                
                if field_name == "delivery_date" and invoice.shipping_date:
                    if parsed_date < invoice.shipping_date:
                        return (False, f"Delivery date {parsed_date} is before shipping date {invoice.shipping_date}")
                
                return (True, None)
            except Exception as e:
                return (False, f"Invalid date value for {field_name}: {str(e)}")
        
        # Amount field validations
        amount_fields = {
            "subtotal", "tax_amount", "total_amount", "discount_amount",
            "shipping_amount", "handling_fee", "deposit_amount",
            "gst_amount", "hst_amount", "qst_amount", "pst_amount",
            "acceptance_percentage"
        }
        if field_name in amount_fields:
            try:
                if isinstance(value, (int, float, Decimal)):
                    decimal_value = Decimal(str(value))
                elif isinstance(value, str):
                    # Try to parse as decimal
                    decimal_value = Decimal(value.replace(",", "").replace("$", "").strip())
                else:
                    return (False, f"Invalid amount format for {field_name}: {value}")
                
                # Check for negative amounts (allow only for credit notes)
                if decimal_value < 0:
                    is_credit = invoice.invoice_type and "credit" in str(invoice.invoice_type).lower()
                    if not is_credit:
                        return (False, f"Negative amount {decimal_value} for {field_name} (not a credit note)")
                
                # Check for unreasonably large amounts (likely OCR error)
                max_reasonable_amount = Decimal("999999999.99")  # ~1 billion
                if abs(decimal_value) > max_reasonable_amount:
                    return (False, f"Amount {decimal_value} is unreasonably large for {field_name}")
                
                # Special validation for percentages
                if field_name == "acceptance_percentage":
                    if decimal_value < 0 or decimal_value > 100:
                        return (False, f"Acceptance percentage {decimal_value} must be between 0 and 100")
                
                return (True, None)
            except (ValueError, InvalidOperation, TypeError) as e:
                return (False, f"Invalid amount value for {field_name}: {str(e)}")
        
        # Tax rate validations
        rate_fields = {"gst_rate", "hst_rate", "qst_rate", "pst_rate"}
        if field_name in rate_fields:
            try:
                if isinstance(value, (int, float, Decimal)):
                    rate_value = Decimal(str(value))
                elif isinstance(value, str):
                    rate_value = Decimal(value.replace("%", "").strip())
                else:
                    return (False, f"Invalid rate format for {field_name}: {value}")
                
                # Tax rates should be between 0 and 100 (or 0 and 1 if decimal)
                if rate_value < 0:
                    return (False, f"Tax rate {rate_value} cannot be negative for {field_name}")
                if rate_value > 100:
                    # Might be decimal format (0.15 = 15%), check if reasonable
                    if rate_value > 1:
                        return (False, f"Tax rate {rate_value} seems too high for {field_name} (expected 0-100% or 0-1)")
                
                return (True, None)
            except (ValueError, InvalidOperation, TypeError) as e:
                return (False, f"Invalid rate value for {field_name}: {str(e)}")
        
        # String field validations
        if isinstance(value, str):
            # Check for extremely long strings (likely OCR error or concatenation issue)
            max_string_length = 1000
            if len(value) > max_string_length:
                return (False, f"String value too long ({len(value)} chars) for {field_name}")
            
            # Check for suspicious patterns (all numbers, all special chars, etc.)
            if len(value) > 50:
                # For long strings, check if it's mostly one character (likely OCR error)
                if len(set(value)) < 3:
                    return (False, f"Suspicious string pattern for {field_name} (too repetitive)")
        
        # Address field validations
        if field_name in {"vendor_address", "bill_to_address", "remit_to_address"}:
            if isinstance(value, dict):
                # Validate address structure
                required_keys = {"street", "city", "province", "postal_code", "country"}
                if not all(k in value for k in required_keys):
                    # Not an error - address can have partial data
                    pass
                # Check postal code format (basic validation for Canadian postal codes)
                if "postal_code" in value and value["postal_code"]:
                    postal_code = str(value["postal_code"]).upper().replace(" ", "")
                    # Canadian postal code: A1A1A1 or A1A 1A1
                    if len(postal_code) == 6:
                        # Check format: letter-digit-letter-digit-letter-digit
                        import re
                        if not re.match(r"^[A-Z]\d[A-Z]\d[A-Z]\d$", postal_code):
                            # Not an error - might be US zip or other format
                            pass
        
        # All other validations passed
        return (True, None)
    
    def _apply_llm_suggestions(self, invoice: Invoice, suggestions: Any, low_conf_fields: List[str]):
        """
        Apply LLM suggestions to the invoice. Accepts either raw text or a parsed dict.
        Validates that LLM only returns canonical field names and validates field values.
        """
        if isinstance(suggestions, str):
            llm_suggestions = self._coerce_llm_json(suggestions)
        elif isinstance(suggestions, dict):
            llm_suggestions = suggestions
        else:
            logger.warning("LLM suggestions are neither str nor dict; skipping apply.")
            return

        if llm_suggestions is None:
            logger.warning("LLM suggestions could not be coerced to JSON; skipping apply.")
            return

        # Validate LLM output - only canonical fields allowed
        invalid_fields = set(llm_suggestions.keys()) - CANONICAL_FIELDS
        if invalid_fields:
            logger.warning(f"LLM returned non-canonical fields (ignoring them): {invalid_fields}")
            # Remove non-canonical fields
            llm_suggestions = {k: v for k, v in llm_suggestions.items() if k in CANONICAL_FIELDS}
        
        if not llm_suggestions:
            logger.info("No valid canonical fields in LLM suggestions after validation")
            return

        logger.info("LLM suggestions (validated): %s", llm_suggestions)

        before = invoice.model_dump()
        validation_errors = []
        
        for field, value in llm_suggestions.items():
            try:
                # Field names from LLM should already be canonical
                target_field = field
                
                # Get original value and confidence for confidence calculation
                original_value = before.get(target_field)
                original_confidence = None
                if invoice.field_confidence:
                    original_confidence = invoice.field_confidence.get(target_field)

                # Validate the LLM suggestion before applying
                is_valid, error_msg = self._validate_llm_suggestion(
                    target_field,
                    value,
                    invoice,
                    original_value,
                )
                
                if not is_valid:
                    logger.warning(
                        f"LLM suggestion rejected for {target_field}: {error_msg}. "
                        f"Original value: {original_value}, Suggested value: {value}"
                    )
                    validation_errors.append(f"{target_field}: {error_msg}")
                    continue  # Skip applying this invalid suggestion

                # Allow explicit null to clear a low-confidence field
                if value is None:
                    setattr(invoice, target_field, None)
                elif target_field in ["subtotal", "tax_amount", "total_amount", "acceptance_percentage"]:
                    parsed = self.field_extractor._parse_decimal(value)
                    setattr(invoice, target_field, parsed)
                elif target_field in [
                    "invoice_date",
                    "due_date",
                    "service_start_date",
                    "service_end_date",
                    "period_start",
                    "period_end",
                ]:
                    from dateutil.parser import parse

                    setattr(invoice, target_field, parse(value).date())
                elif target_field in ["vendor_address", "bill_to_address", "remit_to_address"]:
                    if isinstance(value, dict):
                        from src.models.invoice import Address

                        setattr(invoice, target_field, Address(**value))
                    else:
                        setattr(invoice, target_field, None)
                else:
                    setattr(invoice, target_field, value)

                # Calculate dynamic confidence based on context
                if invoice.field_confidence is None:
                    invoice.field_confidence = {}
                
                # Get new value after setting
                new_value = getattr(invoice, target_field, None)
                calculated_confidence = self._calculate_llm_confidence(
                    target_field,
                    original_value,
                    new_value,
                    original_confidence,
                )
                invoice.field_confidence[target_field] = calculated_confidence
            except Exception as e:
                logger.warning(f"Could not apply LLM suggestion for {field}: {e}")

        after = invoice.model_dump()
        diff = {
            k: {"before": before.get(k), "after": after.get(k)}
            for k in llm_suggestions.keys()
            if before.get(k) != after.get(k)
        }
        logger.info("LLM applied diff: %s", diff)
        
        if validation_errors:
            logger.warning(f"LLM suggestions had {len(validation_errors)} validation errors: {validation_errors}")

        # Recompute overall confidence after applying suggestions
        try:
            if invoice.field_confidence:
                invoice.extraction_confidence = self.field_extractor._calculate_overall_confidence(
                    invoice.field_confidence
                )
        except Exception:
            pass

    def _invoice_to_patch(self, invoice: Invoice) -> Dict[str, Any]:
        """Convert an Invoice Pydantic model into a dict suitable for DB update."""
        return {
            "status": invoice.status,
            "processing_state": invoice.processing_state,
            "content_sha256": invoice.content_sha256,
            "invoice_number": invoice.invoice_number,
            "invoice_date": invoice.invoice_date,
            "due_date": invoice.due_date,
            "vendor_name": invoice.vendor_name,
            "vendor_id": invoice.vendor_id,
            "vendor_phone": invoice.vendor_phone,
            "vendor_address": address_to_dict(invoice.vendor_address),
            "customer_name": invoice.customer_name,
            "customer_id": invoice.customer_id,
            "entity": invoice.entity,
            "bill_to_address": address_to_dict(invoice.bill_to_address),
            "remit_to_address": address_to_dict(invoice.remit_to_address),
            "remit_to_name": invoice.remit_to_name,
            "contract_id": invoice.contract_id,
            "standing_offer_number": invoice.standing_offer_number,
            "po_number": invoice.po_number,
            "period_start": invoice.period_start,
            "period_end": invoice.period_end,
            "subtotal": invoice.subtotal,
            "tax_breakdown": _sanitize_tax_breakdown(invoice.tax_breakdown),
            "tax_amount": invoice.tax_amount,
            "total_amount": invoice.total_amount,
            "currency": invoice.currency,
            "acceptance_percentage": invoice.acceptance_percentage,
            "tax_registration_number": invoice.tax_registration_number,
            "payment_terms": invoice.payment_terms,
            "line_items": line_items_to_json(invoice.line_items),
            "invoice_subtype": invoice.invoice_subtype.value if invoice.invoice_subtype else None,
            "extensions": invoice.extensions.dict() if invoice.extensions else None,
            "extraction_confidence": invoice.extraction_confidence,
            "field_confidence": invoice.field_confidence,
            "extraction_timestamp": invoice.extraction_timestamp,
            "review_status": invoice.review_status,
            "reviewer": invoice.reviewer,
            "review_timestamp": invoice.review_timestamp,
            "review_notes": invoice.review_notes,
        }

    def _sanitize_for_json(self, obj):
        """Recursively convert payload objects to JSON-serializable primitives."""
        return self._sanitize_for_json_v2(obj)

    def _coerce_llm_json(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Best-effort extraction of JSON object from LLM output that may include noise or code fences.
        Returns a parsed dict if successful, otherwise None.
        """
        if not text:
            return None

        # 1) Fast path: direct JSON
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else None
        except Exception:
            pass

        # 2) Strip common code fences like ```json ... ```
        fenced = re.search(r"```(?:json)?\\s*(\\{.*?\\})\\s*```", text, re.DOTALL)
        if fenced:
            candidate = fenced.group(1)
            try:
                data = json.loads(candidate)
                return data if isinstance(data, dict) else None
            except Exception:
                pass

        # 3) Take substring from first '{' to last '}' and try to parse
        if "{" in text and "}" in text:
            start = text.find("{")
            end = text.rfind("}") + 1
            candidate = text[start:end]
            try:
                data = json.loads(candidate)
                return data if isinstance(data, dict) else None
            except Exception:
                pass

        # 4) Gentle single-quote to double-quote normalization on the candidate block
        if "{" in text and "}" in text:
            candidate = text[text.find("{"): text.rfind("}") + 1]
            try:
                normalized = candidate.replace("'", "\"")
                data = json.loads(normalized)
                return data if isinstance(data, dict) else None
            except Exception:
                pass

        return None

    def _sanitize_for_json_v2(
        self,
        data: Any,
        max_depth: int = 4,
        _depth: int = 0,
    ) -> Any:
        """Best-effort scrubber to make DI/canonical data JSON-safe and small."""
        if _depth >= max_depth:
            return str(data)

        # Primitives
        if data is None or isinstance(data, (str, int, float, bool)):
            return data

        # Dates → ISO strings
        if isinstance(data, (date, datetime)):
            return data.isoformat()

        # Decimals → float
        if isinstance(data, Decimal):
            return float(data)

        # Mappings/dicts
        if isinstance(data, Mapping):
            filtered: Dict[str, Any] = {}
            for k, v in data.items():
                # Only string keys, skip private-ish keys
                if not isinstance(k, str) or k.startswith("_"):
                    continue

                key = k.lower()
                # Drop obvious secrets
                if any(bad in key for bad in ("password", "secret", "token", "key")):
                    continue

                filtered[k] = self._sanitize_for_json_v2(v, max_depth=max_depth, _depth=_depth + 1)
            return filtered

        # Lists / tuples / sets
        if isinstance(data, (list, tuple, set)):
            return [
                self._sanitize_for_json_v2(v, max_depth=max_depth, _depth=_depth + 1)
                for v in list(data)[:64]  # cap length so payload stays small
            ]

        # Handle Azure SDK field objects like CurrencyValue by using amount/value/text
        if hasattr(data, "amount"):
            return self._sanitize_for_json_v2(getattr(data, "amount"), max_depth=max_depth, _depth=_depth + 1)
        if hasattr(data, "value"):
            return self._sanitize_for_json_v2(getattr(data, "value"), max_depth=max_depth, _depth=_depth + 1)
        if hasattr(data, "text"):
            return self._sanitize_for_json_v2(getattr(data, "text"), max_depth=max_depth, _depth=_depth + 1)

        # Everything else
        return str(data)
