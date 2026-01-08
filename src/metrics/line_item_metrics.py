"""
Line item-specific metrics calculation for invoice extraction evaluation.

Supports:
- Per-line-item field metrics (description, quantity, unit_price, amount, taxes)
- Line item count metrics (extracted vs ground truth)
- Aggregation validation metrics (subtotal, tax totals match line item sums)
- Line item-level precision/recall/F1
"""

from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal, InvalidOperation
from dataclasses import dataclass, field
from collections import defaultdict
import difflib
import logging

logger = logging.getLogger(__name__)


@dataclass
class LineItemFieldMetrics:
    """Metrics for a single line item field across all line items"""
    field_name: str
    
    # Confusion matrix components
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    true_negatives: int = 0
    
    # Accuracy metrics
    exact_match_count: int = 0
    tolerant_match_count: int = 0
    total_line_items: int = 0
    
    # Similarity metrics (for text fields like description)
    similarity_scores: List[float] = field(default_factory=list)
    
    # Value tolerance for numeric fields
    tolerance: Decimal = Decimal("0.01")
    
    @property
    def precision(self) -> float:
        """Precision: TP / (TP + FP)"""
        total_positive = self.true_positives + self.false_positives
        if total_positive == 0:
            return 0.0
        return self.true_positives / total_positive
    
    @property
    def recall(self) -> float:
        """Recall: TP / (TP + FN)"""
        total_actual = self.true_positives + self.false_negatives
        if total_actual == 0:
            return 0.0
        return self.true_positives / total_actual
    
    @property
    def f1_score(self) -> float:
        """F1 Score: 2 * (Precision * Recall) / (Precision + Recall)"""
        p = self.precision
        r = self.recall
        if p + r == 0:
            return 0.0
        return 2 * (p * r) / (p + r)
    
    @property
    def accuracy(self) -> float:
        """Overall accuracy: (TP + TN) / Total"""
        total = self.true_positives + self.false_positives + self.false_negatives + self.true_negatives
        if total == 0:
            return 0.0
        return (self.true_positives + self.true_negatives) / total
    
    @property
    def exact_match_accuracy(self) -> float:
        """Exact match accuracy"""
        if self.total_line_items == 0:
            return 0.0
        return self.exact_match_count / self.total_line_items
    
    @property
    def tolerant_match_accuracy(self) -> float:
        """Tolerant match accuracy (within tolerance)"""
        if self.total_line_items == 0:
            return 0.0
        return self.tolerant_match_count / self.total_line_items
    
    @property
    def mean_similarity(self) -> float:
        """Mean similarity score"""
        if not self.similarity_scores:
            return 0.0
        return sum(self.similarity_scores) / len(self.similarity_scores)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting"""
        return {
            "field_name": self.field_name,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "true_negatives": self.true_negatives,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "accuracy": self.accuracy,
            "exact_match_count": self.exact_match_count,
            "tolerant_match_count": self.tolerant_match_count,
            "total_line_items": self.total_line_items,
            "exact_match_accuracy": self.exact_match_accuracy,
            "tolerant_match_accuracy": self.tolerant_match_accuracy,
            "mean_similarity": self.mean_similarity,
        }


@dataclass
class LineItemCountMetrics:
    """Metrics for line item count per document"""
    pdf_name: str
    extracted_count: int = 0
    ground_truth_count: int = 0
    count_match: bool = False
    count_difference: int = 0
    
    @property
    def count_accuracy(self) -> float:
        """Accuracy of line item count"""
        if self.ground_truth_count == 0:
            return 1.0 if self.extracted_count == 0 else 0.0
        if self.extracted_count == 0:
            return 0.0
        # Use ratio of correct count
        return min(self.extracted_count, self.ground_truth_count) / max(self.extracted_count, self.ground_truth_count)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting"""
        return {
            "pdf_name": self.pdf_name,
            "extracted_count": self.extracted_count,
            "ground_truth_count": self.ground_truth_count,
            "count_match": self.count_match,
            "count_difference": self.count_difference,
            "count_accuracy": self.count_accuracy,
        }


@dataclass
class AggregationMetrics:
    """Metrics for aggregation validation (totals = sum of line items)"""
    pdf_name: str
    
    # Validation results
    subtotal_valid: bool = False
    gst_amount_valid: bool = False
    pst_amount_valid: bool = False
    qst_amount_valid: bool = False
    tax_amount_valid: bool = False
    total_amount_valid: bool = False
    
    # Differences (if validation failed)
    subtotal_difference: Optional[Decimal] = None
    gst_difference: Optional[Decimal] = None
    pst_difference: Optional[Decimal] = None
    qst_difference: Optional[Decimal] = None
    tax_difference: Optional[Decimal] = None
    total_difference: Optional[Decimal] = None
    
    @property
    def all_valid(self) -> bool:
        """Check if all aggregations are valid"""
        return (
            self.subtotal_valid and
            self.gst_amount_valid and
            self.pst_amount_valid and
            self.qst_amount_valid and
            self.tax_amount_valid and
            self.total_amount_valid
        )
    
    @property
    def validation_score(self) -> float:
        """Percentage of validations that passed"""
        validations = [
            self.subtotal_valid,
            self.gst_amount_valid,
            self.pst_amount_valid,
            self.qst_amount_valid,
            self.tax_amount_valid,
            self.total_amount_valid,
        ]
        return sum(validations) / len(validations)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting"""
        return {
            "pdf_name": self.pdf_name,
            "subtotal_valid": self.subtotal_valid,
            "gst_amount_valid": self.gst_amount_valid,
            "pst_amount_valid": self.pst_amount_valid,
            "qst_amount_valid": self.qst_amount_valid,
            "tax_amount_valid": self.tax_amount_valid,
            "total_amount_valid": self.total_amount_valid,
            "all_valid": self.all_valid,
            "validation_score": self.validation_score,
            "subtotal_difference": str(self.subtotal_difference) if self.subtotal_difference else None,
            "gst_difference": str(self.gst_difference) if self.gst_difference else None,
            "pst_difference": str(self.pst_difference) if self.pst_difference else None,
            "qst_difference": str(self.qst_difference) if self.qst_difference else None,
            "tax_difference": str(self.tax_difference) if self.tax_difference else None,
            "total_difference": str(self.total_difference) if self.total_difference else None,
        }


class LineItemMetricsCalculator:
    """Calculate line item-specific metrics"""
    
    TOLERANCE = Decimal("0.01")  # 1 cent tolerance for numeric fields
    
    # Line item fields to track
    LINE_ITEM_FIELDS = [
        "line_number",
        "description",
        "quantity",
        "unit_price",
        "amount",
        "tax_rate",
        "tax_amount",
        "gst_amount",
        "pst_amount",
        "qst_amount",
        "combined_tax",
        "unit_of_measure",
        "project_code",
        "region_code",
        "airport_code",
        "cost_centre_code",
    ]
    
    def __init__(self):
        """Initialize calculator"""
        self.field_metrics: Dict[str, LineItemFieldMetrics] = {}
        self.count_metrics: Dict[str, LineItemCountMetrics] = {}
        self.aggregation_metrics: Dict[str, AggregationMetrics] = {}
        
        # Initialize field metrics
        for field_name in self.LINE_ITEM_FIELDS:
            self.field_metrics[field_name] = LineItemFieldMetrics(field_name=field_name)
    
    def calculate_metrics(
        self,
        extracted_data: List[Dict[str, Any]],
        ground_truth_data: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Calculate all line item metrics.
        
        Args:
            extracted_data: List of extraction results, each with 'pdf_name' and 'line_items'
            ground_truth_data: Dict mapping pdf_name to ground truth with 'line_items'
        
        Returns:
            Dictionary with all metrics
        """
        # Reset metrics
        self.field_metrics = {field: LineItemFieldMetrics(field_name=field) for field in self.LINE_ITEM_FIELDS}
        self.count_metrics = {}
        self.aggregation_metrics = {}
        
        # Process each document
        for extracted in extracted_data:
            pdf_name = extracted.get("pdf_name", "unknown")
            extracted_line_items = extracted.get("line_items", [])
            ground_truth = ground_truth_data.get(pdf_name, {})
            gt_line_items = ground_truth.get("line_items", [])
            
            # Calculate line item count metrics
            self._calculate_count_metrics(pdf_name, extracted_line_items, gt_line_items)
            
            # Calculate per-field metrics
            self._calculate_field_metrics(pdf_name, extracted_line_items, gt_line_items)
            
            # Calculate aggregation metrics
            self._calculate_aggregation_metrics(pdf_name, extracted, ground_truth)
        
        return self._compile_results()
    
    def _calculate_count_metrics(
        self,
        pdf_name: str,
        extracted_line_items: List[Dict[str, Any]],
        gt_line_items: List[Dict[str, Any]],
    ) -> None:
        """Calculate line item count metrics"""
        extracted_count = len(extracted_line_items)
        gt_count = len(gt_line_items)
        
        metrics = LineItemCountMetrics(
            pdf_name=pdf_name,
            extracted_count=extracted_count,
            ground_truth_count=gt_count,
            count_match=(extracted_count == gt_count),
            count_difference=extracted_count - gt_count,
        )
        
        self.count_metrics[pdf_name] = metrics
    
    def _calculate_field_metrics(
        self,
        pdf_name: str,
        extracted_line_items: List[Dict[str, Any]],
        gt_line_items: List[Dict[str, Any]],
    ) -> None:
        """Calculate per-field metrics for line items"""
        # Match line items by line_number or index
        matched_pairs = self._match_line_items(extracted_line_items, gt_line_items)
        
        for field_name in self.LINE_ITEM_FIELDS:
            metrics = self.field_metrics[field_name]
            
            for extracted_item, gt_item in matched_pairs:
                if gt_item is None:
                    # False positive: extracted but not in ground truth
                    if self._field_extracted(extracted_item, field_name):
                        metrics.false_positives += 1
                    else:
                        metrics.true_negatives += 1
                    continue
                
                if extracted_item is None:
                    # False negative: in ground truth but not extracted
                    if self._field_exists(gt_item, field_name):
                        metrics.false_negatives += 1
                    else:
                        metrics.true_negatives += 1
                    continue
                
                # Both exist - compare values
                extracted_value = self._get_field_value(extracted_item, field_name)
                gt_value = self._get_field_value(gt_item, field_name)
                
                extracted_exists = extracted_value is not None
                gt_exists = gt_value is not None
                
                if extracted_exists and gt_exists:
                    # Both exist - check if they match
                    if self._values_match(extracted_value, gt_value, field_name):
                        metrics.true_positives += 1
                        metrics.exact_match_count += 1
                        metrics.tolerant_match_count += 1
                    else:
                        # Check tolerant match for numeric fields
                        if self._tolerant_match(extracted_value, gt_value, field_name):
                            metrics.true_positives += 1
                            metrics.tolerant_match_count += 1
                        else:
                            metrics.false_positives += 1
                            metrics.false_negatives += 1
                    
                    # Calculate similarity for text fields
                    if field_name in ["description"]:
                        similarity = self._calculate_similarity(extracted_value, gt_value)
                        metrics.similarity_scores.append(similarity)
                
                elif extracted_exists and not gt_exists:
                    metrics.false_positives += 1
                elif not extracted_exists and gt_exists:
                    metrics.false_negatives += 1
                else:
                    metrics.true_negatives += 1
                
                metrics.total_line_items += 1
    
    def _calculate_aggregation_metrics(
        self,
        pdf_name: str,
        extracted: Dict[str, Any],
        ground_truth: Dict[str, Any],
    ) -> None:
        """Calculate aggregation validation metrics"""
        from src.validation.aggregation_validator import AggregationValidator
        from src.models.invoice import Invoice
        
        # Create Invoice object from extracted data for validation
        # This is a simplified version - in practice, you'd reconstruct the full Invoice
        # For now, we'll calculate aggregations manually
        
        extracted_line_items = extracted.get("line_items", [])
        gt_line_items = ground_truth.get("line_items", [])
        
        # Calculate sums from line items
        extracted_subtotal = sum(
            self._parse_decimal(item.get("amount", 0)) for item in extracted_line_items
        )
        extracted_gst = sum(
            self._parse_decimal(item.get("gst_amount", 0)) for item in extracted_line_items
        )
        extracted_pst = sum(
            self._parse_decimal(item.get("pst_amount", 0)) for item in extracted_line_items
        )
        extracted_qst = sum(
            self._parse_decimal(item.get("qst_amount", 0)) for item in extracted_line_items
        )
        extracted_tax = sum(
            self._parse_decimal(item.get("tax_amount", 0)) for item in extracted_line_items
        )
        
        # Get invoice-level totals
        extracted_fields = extracted.get("extracted_fields", {})
        invoice_subtotal = self._parse_decimal(extracted_fields.get("subtotal", {}).get("value"))
        invoice_gst = self._parse_decimal(extracted_fields.get("gst_amount", {}).get("value"))
        invoice_pst = self._parse_decimal(extracted_fields.get("pst_amount", {}).get("value"))
        invoice_qst = self._parse_decimal(extracted_fields.get("qst_amount", {}).get("value"))
        invoice_tax = self._parse_decimal(extracted_fields.get("tax_amount", {}).get("value"))
        invoice_total = self._parse_decimal(extracted_fields.get("total_amount", {}).get("value"))
        
        # Validate aggregations
        metrics = AggregationMetrics(pdf_name=pdf_name)
        
        if invoice_subtotal is not None:
            diff = abs(invoice_subtotal - extracted_subtotal)
            metrics.subtotal_valid = diff <= self.TOLERANCE
            if not metrics.subtotal_valid:
                metrics.subtotal_difference = diff
        
        if invoice_gst is not None:
            diff = abs(invoice_gst - extracted_gst)
            metrics.gst_amount_valid = diff <= self.TOLERANCE
            if not metrics.gst_amount_valid:
                metrics.gst_difference = diff
        
        if invoice_pst is not None:
            diff = abs(invoice_pst - extracted_pst)
            metrics.pst_amount_valid = diff <= self.TOLERANCE
            if not metrics.pst_amount_valid:
                metrics.pst_difference = diff
        
        if invoice_qst is not None:
            diff = abs(invoice_qst - extracted_qst)
            metrics.qst_amount_valid = diff <= self.TOLERANCE
            if not metrics.qst_amount_valid:
                metrics.qst_difference = diff
        
        if invoice_tax is not None:
            diff = abs(invoice_tax - extracted_tax)
            metrics.tax_amount_valid = diff <= self.TOLERANCE
            if not metrics.tax_amount_valid:
                metrics.tax_difference = diff
        
        # Total amount validation (subtotal + tax + shipping + handling - discount)
        if invoice_total is not None and invoice_subtotal is not None:
            shipping = self._parse_decimal(extracted_fields.get("shipping_amount", {}).get("value")) or Decimal("0")
            handling = self._parse_decimal(extracted_fields.get("handling_fee", {}).get("value")) or Decimal("0")
            discount = self._parse_decimal(extracted_fields.get("discount_amount", {}).get("value")) or Decimal("0")
            calculated_total = invoice_subtotal + (invoice_tax or Decimal("0")) + shipping + handling - discount
            diff = abs(invoice_total - calculated_total)
            metrics.total_amount_valid = diff <= self.TOLERANCE
            if not metrics.total_amount_valid:
                metrics.total_difference = diff
        
        self.aggregation_metrics[pdf_name] = metrics
    
    def _match_line_items(
        self,
        extracted: List[Dict[str, Any]],
        ground_truth: List[Dict[str, Any]],
    ) -> List[Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]]:
        """Match extracted line items with ground truth by line_number"""
        matched = []
        
        # Create lookup by line_number
        extracted_by_number = {item.get("line_number", i+1): item for i, item in enumerate(extracted)}
        gt_by_number = {item.get("line_number", i+1): item for i, item in enumerate(ground_truth)}
        
        all_numbers = set(extracted_by_number.keys()) | set(gt_by_number.keys())
        
        for line_number in sorted(all_numbers):
            extracted_item = extracted_by_number.get(line_number)
            gt_item = gt_by_number.get(line_number)
            matched.append((extracted_item, gt_item))
        
        return matched
    
    def _field_extracted(self, item: Dict[str, Any], field_name: str) -> bool:
        """Check if field was extracted"""
        value = self._get_field_value(item, field_name)
        return value is not None
    
    def _field_exists(self, item: Dict[str, Any], field_name: str) -> bool:
        """Check if field exists in ground truth"""
        value = self._get_field_value(item, field_name)
        return value is not None
    
    def _get_field_value(self, item: Dict[str, Any], field_name: str) -> Any:
        """Get field value from line item"""
        return item.get(field_name)
    
    def _values_match(self, extracted: Any, ground_truth: Any, field_name: str) -> bool:
        """Check if values match exactly"""
        if extracted is None and ground_truth is None:
            return True
        if extracted is None or ground_truth is None:
            return False
        
        # For numeric fields, compare as decimals
        if field_name in ["quantity", "unit_price", "amount", "tax_rate", "tax_amount", 
                          "gst_amount", "pst_amount", "qst_amount", "combined_tax"]:
            try:
                ext_dec = self._parse_decimal(extracted)
                gt_dec = self._parse_decimal(ground_truth)
                return ext_dec == gt_dec
            except (ValueError, TypeError, InvalidOperation):
                return str(extracted).strip() == str(ground_truth).strip()
        
        # For text fields, compare as strings
        return str(extracted).strip().lower() == str(ground_truth).strip().lower()
    
    def _tolerant_match(self, extracted: Any, ground_truth: Any, field_name: str) -> bool:
        """Check if values match within tolerance (for numeric fields)"""
        if field_name not in ["quantity", "unit_price", "amount", "tax_rate", "tax_amount",
                              "gst_amount", "pst_amount", "qst_amount", "combined_tax"]:
            return False
        
        try:
            ext_dec = self._parse_decimal(extracted)
            gt_dec = self._parse_decimal(ground_truth)
            diff = abs(ext_dec - gt_dec)
            return diff <= self.TOLERANCE
        except (ValueError, TypeError, InvalidOperation):
            return False
    
    def _calculate_similarity(self, extracted: str, ground_truth: str) -> float:
        """Calculate string similarity (0-1)"""
        if not extracted or not ground_truth:
            return 0.0
        
        extracted = str(extracted).strip().lower()
        ground_truth = str(ground_truth).strip().lower()
        
        if extracted == ground_truth:
            return 1.0
        
        # Use SequenceMatcher for similarity
        return difflib.SequenceMatcher(None, extracted, ground_truth).ratio()
    
    def _parse_decimal(self, value: Any) -> Optional[Decimal]:
        """Parse value to Decimal"""
        if value is None:
            return None
        if isinstance(value, Decimal):
            return value
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        if isinstance(value, str):
            try:
                return Decimal(value.strip())
            except (ValueError, InvalidOperation):
                return None
        return None
    
    def _compile_results(self) -> Dict[str, Any]:
        """Compile all metrics into results dictionary"""
        return {
            "field_metrics": {name: metrics.to_dict() for name, metrics in self.field_metrics.items()},
            "count_metrics": {name: metrics.to_dict() for name, metrics in self.count_metrics.items()},
            "aggregation_metrics": {name: metrics.to_dict() for name, metrics in self.aggregation_metrics.items()},
        }
