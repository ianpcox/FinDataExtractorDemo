"""
Per-field metrics calculation for invoice extraction evaluation.

Supports:
- Precision/Recall/F1 per field
- Exact-match accuracy
- Value-tolerant accuracy (numeric/date fields)
- String similarity scoring
- Confidence calibration
"""

from typing import Dict, Any, Optional, List, Tuple
from decimal import Decimal, InvalidOperation
from datetime import date, datetime
from dataclasses import dataclass
from collections import defaultdict
import difflib
try:
    from dateutil.parser import parse as parse_date
except ImportError:
    # Fallback to datetime parsing if dateutil not available
    def parse_date(value):
        from datetime import datetime
        if isinstance(value, str):
            # Try common date formats
            formats = [
                "%Y-%m-%d",
                "%Y/%m/%d",
                "%m/%d/%Y",
                "%d/%m/%Y",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt)
                except ValueError:
                    continue
        return None


@dataclass
class FieldMetrics:
    """Metrics for a single field across all documents"""
    field_name: str
    # Confusion matrix components
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    true_negatives: int = 0
    
    # Accuracy metrics
    exact_match_count: int = 0
    tolerant_match_count: int = 0
    total_documents: int = 0
    
    # Similarity metrics
    similarity_scores: List[float] = None
    
    # Confidence calibration
    confidence_bins: Dict[str, List[float]] = None  # bin -> [correctness ratios]
    
    def __post_init__(self):
        if self.similarity_scores is None:
            self.similarity_scores = []
        if self.confidence_bins is None:
            self.confidence_bins = defaultdict(list)
    
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
        """Exact match accuracy: exact matches / total documents"""
        if self.total_documents == 0:
            return 0.0
        return self.exact_match_count / self.total_documents
    
    @property
    def tolerant_match_accuracy(self) -> float:
        """Tolerant match accuracy: tolerant matches / total documents"""
        if self.total_documents == 0:
            return 0.0
        return self.tolerant_match_count / self.total_documents
    
    @property
    def mean_similarity(self) -> float:
        """Mean string similarity score"""
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
            "exact_match_accuracy": self.exact_match_accuracy,
            "tolerant_match_accuracy": self.tolerant_match_accuracy,
            "mean_similarity": self.mean_similarity,
            "total_documents": self.total_documents,
            "similarity_samples": len(self.similarity_scores),
        }


class FieldMetricsCalculator:
    """Calculate per-field metrics from extraction results and ground truth"""
    
    def __init__(
        self,
        numeric_tolerance: float = 0.01,
        numeric_percentage_tolerance: float = 0.001,  # 0.1%
        date_tolerance_days: int = 0,
    ):
        """
        Initialize calculator with tolerances.
        
        Args:
            numeric_tolerance: Absolute tolerance for numeric comparisons
            numeric_percentage_tolerance: Percentage tolerance for numeric comparisons
            date_tolerance_days: Days tolerance for date comparisons
        """
        self.numeric_tolerance = numeric_tolerance
        self.numeric_percentage_tolerance = numeric_percentage_tolerance
        self.date_tolerance_days = date_tolerance_days
    
    def calculate_metrics(
        self,
        extracted_data: List[Dict[str, Any]],
        ground_truth: List[Dict[str, Any]],
        field_names: List[str],
    ) -> Dict[str, FieldMetrics]:
        """
        Calculate per-field metrics from extracted data and ground truth.
        
        Args:
            extracted_data: List of extraction results, each with field_name, value, confidence, extracted
            ground_truth: List of ground truth values, each with field_name, value, exists
            field_names: List of all field names to evaluate
        
        Returns:
            Dictionary mapping field_name -> FieldMetrics
        """
        metrics = {field_name: FieldMetrics(field_name=field_name) for field_name in field_names}
        
        # Group by document (assuming both lists are aligned by document)
        # For now, assume they're aligned by index
        for idx, (extracted, gt) in enumerate(zip(extracted_data, ground_truth)):
            doc_id = extracted.get("pdf_name") or extracted.get("document_id") or str(idx)
            
            # Process each field
            for field_name in field_names:
                field_metrics = metrics[field_name]
                field_metrics.total_documents += 1
                
                # Get extracted and ground truth values
                extracted_value = self._get_field_value(extracted, field_name)
                extracted_confidence = self._get_field_confidence(extracted, field_name)
                is_extracted = self._is_field_extracted(extracted, field_name)
                
                gt_value = self._get_field_value(gt, field_name)
                gt_exists = self._field_exists_in_gt(gt, field_name)
                
                # Update confusion matrix
                if gt_exists and is_extracted:
                    # Check if value is correct
                    is_correct = self._values_match(extracted_value, gt_value, field_name)
                    if is_correct:
                        field_metrics.true_positives += 1
                    else:
                        field_metrics.false_positives += 1
                        field_metrics.false_negatives += 1  # Also a false negative (wrong value)
                elif gt_exists and not is_extracted:
                    field_metrics.false_negatives += 1
                elif not gt_exists and is_extracted:
                    field_metrics.false_positives += 1
                else:  # not exists and not extracted
                    field_metrics.true_negatives += 1
                
                # Calculate exact match
                if gt_exists:
                    if self._values_exact_match(extracted_value, gt_value, field_name):
                        field_metrics.exact_match_count += 1
                    
                    # Calculate tolerant match
                    if self._values_tolerant_match(extracted_value, gt_value, field_name):
                        field_metrics.tolerant_match_count += 1
                    
                    # Calculate similarity for text fields
                    if self._is_text_field(field_name):
                        similarity = self._calculate_similarity(extracted_value, gt_value)
                        if similarity is not None:
                            field_metrics.similarity_scores.append(similarity)
                
                # Confidence calibration
                if is_extracted and extracted_confidence is not None:
                    bin_key = self._get_confidence_bin(extracted_confidence)
                    is_correct = self._values_match(extracted_value, gt_value, field_name) if gt_exists else False
                    field_metrics.confidence_bins[bin_key].append(1.0 if is_correct else 0.0)
        
        return metrics
    
    def _get_field_value(self, data: Dict[str, Any], field_name: str) -> Any:
        """Extract field value from data dictionary"""
        # Check direct field access
        if field_name in data:
            return data[field_name]
        
        # Check nested structure (e.g., extracted_fields[field_name].value)
        if "extracted_fields" in data and field_name in data["extracted_fields"]:
            field_data = data["extracted_fields"][field_name]
            if isinstance(field_data, dict):
                return field_data.get("value")
            return field_data
        
        return None
    
    def _get_field_confidence(self, data: Dict[str, Any], field_name: str) -> Optional[float]:
        """Extract field confidence from data dictionary"""
        if "extracted_fields" in data and field_name in data["extracted_fields"]:
            field_data = data["extracted_fields"][field_name]
            if isinstance(field_data, dict):
                return field_data.get("confidence")
        return None
    
    def _is_field_extracted(self, data: Dict[str, Any], field_name: str) -> bool:
        """Check if field is marked as extracted"""
        if "extracted_fields" in data and field_name in data["extracted_fields"]:
            field_data = data["extracted_fields"][field_name]
            if isinstance(field_data, dict):
                return field_data.get("extracted", False)
        return False
    
    def _field_exists_in_gt(self, gt: Dict[str, Any], field_name: str) -> bool:
        """Check if field exists in ground truth"""
        value = self._get_field_value(gt, field_name)
        if value is None:
            return False
        
        # Check if value is non-empty
        if isinstance(value, str):
            return value.strip() != ""
        if isinstance(value, (dict, list)):
            return len(value) > 0
        return True
    
    def _values_exact_match(self, extracted: Any, gt: Any, field_name: str) -> bool:
        """Check if values exactly match"""
        if extracted is None and gt is None:
            return True
        if extracted is None or gt is None:
            return False
        
        # Handle Address objects
        if isinstance(extracted, dict) and isinstance(gt, dict):
            if "street" in extracted or "street" in gt:
                # Address comparison
                return self._addresses_match(extracted, gt, exact=True)
        
        # Handle dates
        if self._is_date_field(field_name):
            return self._dates_match(extracted, gt, tolerance_days=0)
        
        # Handle decimals
        if self._is_numeric_field(field_name):
            return self._decimals_match(extracted, gt, tolerance=0.0)
        
        # String comparison
        return str(extracted).strip() == str(gt).strip()
    
    def _values_tolerant_match(self, extracted: Any, gt: Any, field_name: str) -> bool:
        """Check if values match within tolerance"""
        if extracted is None and gt is None:
            return True
        if extracted is None or gt is None:
            return False
        
        # Handle Address objects
        if isinstance(extracted, dict) and isinstance(gt, dict):
            if "street" in extracted or "street" in gt:
                # Address comparison with similarity threshold
                similarity = self._calculate_similarity(extracted, gt)
                return similarity is not None and similarity >= 0.8
        
        # Handle dates
        if self._is_date_field(field_name):
            return self._dates_match(extracted, gt, tolerance_days=self.date_tolerance_days)
        
        # Handle decimals
        if self._is_numeric_field(field_name):
            return self._decimals_match(extracted, gt, tolerance=self.numeric_tolerance, percentage_tolerance=self.numeric_percentage_tolerance)
        
        # String similarity
        similarity = self._calculate_similarity(extracted, gt)
        return similarity is not None and similarity >= 0.9
    
    def _values_match(self, extracted: Any, gt: Any, field_name: str) -> bool:
        """Check if values match (uses tolerant matching)"""
        return self._values_tolerant_match(extracted, gt, field_name)
    
    def _addresses_match(self, addr1: Dict, addr2: Dict, exact: bool = False) -> bool:
        """Compare two address dictionaries"""
        fields = ["street", "city", "province", "postal_code", "country"]
        matches = 0
        total = 0
        
        for field in fields:
            val1 = addr1.get(field)
            val2 = addr2.get(field)
            
            if val1 is None and val2 is None:
                continue
            
            total += 1
            if val1 and val2:
                if exact:
                    if str(val1).strip().lower() == str(val2).strip().lower():
                        matches += 1
                else:
                    similarity = self._string_similarity(str(val1), str(val2))
                    if similarity >= 0.8:
                        matches += 1
        
        if total == 0:
            return True  # Both addresses are empty
        
        if exact:
            return matches == total
        else:
            return matches / total >= 0.7  # At least 70% of fields match
    
    def _dates_match(self, date1: Any, date2: Any, tolerance_days: int = 0) -> bool:
        """Compare two dates with optional tolerance"""
        try:
            d1 = self._parse_date(date1)
            d2 = self._parse_date(date2)
            
            if d1 is None or d2 is None:
                return False
            
            diff = abs((d1 - d2).days)
            return diff <= tolerance_days
        except Exception:
            return False
    
    def _decimals_match(
        self,
        dec1: Any,
        dec2: Any,
        tolerance: float = 0.01,
        percentage_tolerance: float = 0.001,
    ) -> bool:
        """Compare two decimal values with tolerance"""
        try:
            d1 = self._parse_decimal(dec1)
            d2 = self._parse_decimal(dec2)
            
            if d1 is None or d2 is None:
                return False
            
            # Absolute tolerance
            abs_diff = abs(float(d1 - d2))
            if abs_diff <= tolerance:
                return True
            
            # Percentage tolerance
            if d2 != 0:
                pct_diff = abs_diff / abs(float(d2))
                if pct_diff <= percentage_tolerance:
                    return True
            
            return False
        except Exception:
            return False
    
    def _calculate_similarity(self, val1: Any, val2: Any) -> Optional[float]:
        """Calculate similarity between two values"""
        if val1 is None or val2 is None:
            return None
        
        # For addresses, use address-specific comparison
        if isinstance(val1, dict) and isinstance(val2, dict):
            if "street" in val1 or "street" in val2:
                return self._address_similarity(val1, val2)
        
        # For strings, use string similarity
        return self._string_similarity(str(val1), str(val2))
    
    def _address_similarity(self, addr1: Dict, addr2: Dict) -> float:
        """Calculate similarity between two addresses"""
        fields = ["street", "city", "province", "postal_code", "country"]
        similarities = []
        
        for field in fields:
            val1 = addr1.get(field)
            val2 = addr2.get(field)
            
            if val1 is None and val2 is None:
                similarities.append(1.0)
            elif val1 is None or val2 is None:
                similarities.append(0.0)
            else:
                similarities.append(self._string_similarity(str(val1), str(val2)))
        
        if not similarities:
            return 0.0
        
        return sum(similarities) / len(similarities)
    
    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate normalized string similarity (0.0 to 1.0)"""
        s1 = s1.strip().lower()
        s2 = s2.strip().lower()
        
        if s1 == s2:
            return 1.0
        
        if not s1 or not s2:
            return 0.0
        
        # Use SequenceMatcher for similarity
        return difflib.SequenceMatcher(None, s1, s2).ratio()
    
    def _parse_date(self, value: Any) -> Optional[date]:
        """Parse a date value"""
        if value is None:
            return None
        
        if isinstance(value, date):
            return value
        
        if isinstance(value, datetime):
            return value.date()
        
        if isinstance(value, str):
            try:
                parsed = parse_date(value)
                if isinstance(parsed, datetime):
                    return parsed.date()
                return parsed
            except Exception:
                return None
        
        return None
    
    def _parse_decimal(self, value: Any) -> Optional[Decimal]:
        """Parse a decimal value"""
        if value is None:
            return None
        
        if isinstance(value, Decimal):
            return value
        
        if isinstance(value, (int, float)):
            return Decimal(str(value))
        
        if isinstance(value, str):
            try:
                cleaned = value.replace("$", "").replace(",", "").strip()
                return Decimal(cleaned)
            except (ValueError, InvalidOperation):
                return None
        
        return None
    
    def _is_date_field(self, field_name: str) -> bool:
        """Check if field is a date field"""
        date_fields = ["invoice_date", "due_date", "shipping_date", "delivery_date", "period_start", "period_end"]
        return field_name in date_fields
    
    def _is_numeric_field(self, field_name: str) -> bool:
        """Check if field is a numeric field"""
        numeric_fields = [
            "subtotal", "tax_amount", "total_amount", "discount_amount", "shipping_amount",
            "handling_fee", "deposit_amount", "gst_amount", "gst_rate", "hst_amount", "hst_rate",
            "qst_amount", "qst_rate", "pst_amount", "pst_rate",
        ]
        return field_name in numeric_fields
    
    def _is_text_field(self, field_name: str) -> bool:
        """Check if field is a text field (for similarity scoring)"""
        text_fields = [
            "vendor_name", "customer_name", "invoice_number", "po_number",
            "vendor_address", "bill_to_address", "remit_to_address",
        ]
        return field_name in text_fields
    
    def _get_confidence_bin(self, confidence: float) -> str:
        """Get confidence bin for calibration"""
        if confidence >= 0.9:
            return "0.9-1.0"
        elif confidence >= 0.8:
            return "0.8-0.9"
        elif confidence >= 0.7:
            return "0.7-0.8"
        elif confidence >= 0.5:
            return "0.5-0.7"
        else:
            return "0.0-0.5"
