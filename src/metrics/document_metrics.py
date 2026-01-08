"""
Document-level metrics calculation for invoice extraction evaluation.

Supports:
- Document-level extraction rate
- Document-level accuracy/F1 (micro-averaged)
- All-required-fields correctness ("hard pass")
- Average confidence per document
- Error severity / business impact score
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from collections import defaultdict
from decimal import Decimal


@dataclass
class DocumentMetrics:
    """Metrics for a single document"""
    pdf_name: str
    
    # Extraction coverage
    fields_extracted: int = 0
    total_fields: int = 0
    extraction_rate: float = 0.0
    
    # Accuracy metrics (micro-averaged)
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    true_negatives: int = 0
    
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    accuracy: float = 0.0
    
    # Required fields correctness
    required_fields_correct: int = 0
    total_required_fields: int = 0
    all_required_fields_correct: bool = False
    
    # Confidence
    average_confidence: Optional[float] = None
    confidence_weighted_accuracy: Optional[float] = None
    
    # Error severity / business impact
    weighted_errors: float = 0.0
    weighted_f1: float = 0.0
    business_impact_score: float = 0.0
    
    def __post_init__(self):
        """Calculate derived metrics"""
        self._recalculate_metrics()
    
    def _recalculate_metrics(self):
        """Recalculate all derived metrics"""
        if self.total_fields > 0:
            self.extraction_rate = self.fields_extracted / self.total_fields
        
        # Micro-averaged precision/recall/F1
        total_positive = self.true_positives + self.false_positives
        if total_positive > 0:
            self.precision = self.true_positives / total_positive
        
        total_actual = self.true_positives + self.false_negatives
        if total_actual > 0:
            self.recall = self.true_positives / total_actual
        
        if self.precision + self.recall > 0:
            self.f1_score = 2 * (self.precision * self.recall) / (self.precision + self.recall)
        
        total = self.true_positives + self.false_positives + self.false_negatives + self.true_negatives
        if total > 0:
            self.accuracy = (self.true_positives + self.true_negatives) / total
        
        # Required fields correctness
        if self.total_required_fields > 0:
            self.all_required_fields_correct = (
                self.required_fields_correct == self.total_required_fields
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting"""
        return {
            "pdf_name": self.pdf_name,
            "fields_extracted": self.fields_extracted,
            "total_fields": self.total_fields,
            "extraction_rate": self.extraction_rate,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "true_negatives": self.true_negatives,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "accuracy": self.accuracy,
            "required_fields_correct": self.required_fields_correct,
            "total_required_fields": self.total_required_fields,
            "all_required_fields_correct": self.all_required_fields_correct,
            "average_confidence": self.average_confidence,
            "confidence_weighted_accuracy": self.confidence_weighted_accuracy,
            "weighted_errors": self.weighted_errors,
            "weighted_f1": self.weighted_f1,
            "business_impact_score": self.business_impact_score,
        }


class DocumentMetricsCalculator:
    """Calculate document-level metrics from extraction results and ground truth"""
    
    def __init__(
        self,
        required_fields: Optional[List[str]] = None,
        field_weights: Optional[Dict[str, float]] = None,
        canonical_field_count: Optional[int] = None,
    ):
        """
        Initialize calculator.
        
        Args:
            required_fields: List of required field names (defaults to metrics_config.REQUIRED_FIELDS)
            field_weights: Dictionary mapping field_name -> weight (defaults to metrics_config.FIELD_WEIGHTS)
            canonical_field_count: Total canonical field count (defaults to metrics_config.CANONICAL_FIELD_COUNT)
        """
        from src.metrics.metrics_config import (
            REQUIRED_FIELDS,
            FIELD_WEIGHTS,
            CANONICAL_FIELD_COUNT,
            get_field_weight,
        )
        
        self.required_fields = required_fields or REQUIRED_FIELDS
        self.field_weights = field_weights or FIELD_WEIGHTS.copy()
        self.canonical_field_count = canonical_field_count or CANONICAL_FIELD_COUNT
        self.get_field_weight_func = get_field_weight if not field_weights else lambda f: self.field_weights.get(f, 1.0)
        # Default weight for fields not in weights dict
        self.default_weight = 1.0
    
    def get_field_weight(self, field_name: str) -> float:
        """Get importance weight for a field"""
        return self.get_field_weight_func(field_name)
    
    def calculate_metrics(
        self,
        extracted_data: List[Dict[str, Any]],
        ground_truth: List[Dict[str, Any]],
        field_names: List[str],
        field_metrics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, DocumentMetrics]:
        """
        Calculate document-level metrics.
        
        Args:
            extracted_data: List of extraction results
            ground_truth: List of ground truth values
            field_names: List of all field names
            field_metrics: Optional per-field metrics for reference
        
        Returns:
            Dictionary mapping pdf_name -> DocumentMetrics
        """
        documents = {}
        
        # Process each document
        for idx, (extracted, gt) in enumerate(zip(extracted_data, ground_truth)):
            pdf_name = extracted.get("pdf_name") or extracted.get("document_id") or f"doc_{idx}"
            
            doc_metrics = DocumentMetrics(pdf_name=pdf_name)
            # Use canonical field count as denominator (from canonical field coverage reports)
            doc_metrics.total_fields = self.canonical_field_count
            
            # Track confidence scores
            confidence_scores = []
            confidence_correct = []
            
            # Process each field
            for field_name in field_names:
                weight = self.get_field_weight(field_name)
                
                # Get extracted and ground truth values
                extracted_value = self._get_field_value(extracted, field_name)
                extracted_confidence = self._get_field_confidence(extracted, field_name)
                is_extracted = self._is_field_extracted(extracted, field_name)
                
                gt_value = self._get_field_value(gt, field_name)
                gt_exists = self._field_exists_in_gt(gt, field_name)
                
                # Update extraction rate
                if is_extracted:
                    doc_metrics.fields_extracted += 1
                    # Recalculate extraction rate
                    if doc_metrics.total_fields > 0:
                        doc_metrics.extraction_rate = doc_metrics.fields_extracted / doc_metrics.total_fields
                
                # Update confusion matrix
                if gt_exists and is_extracted:
                    # Check if value is correct (simplified - should use same logic as field metrics)
                    is_correct = self._values_match(extracted_value, gt_value, field_name)
                    if is_correct:
                        doc_metrics.true_positives += 1
                        # Track for required fields
                        if field_name in self.required_fields:
                            doc_metrics.required_fields_correct += 1
                    else:
                        doc_metrics.false_positives += 1
                        doc_metrics.false_negatives += 1
                        # Weighted errors
                        doc_metrics.weighted_errors += weight
                elif gt_exists and not is_extracted:
                    doc_metrics.false_negatives += 1
                    # Weighted errors
                    doc_metrics.weighted_errors += weight
                    # Required field missing
                    if field_name in self.required_fields:
                        pass  # Already counted in required_fields_correct
                elif not gt_exists and is_extracted:
                    doc_metrics.false_positives += 1
                    # Weighted errors (less weight for false positives on optional fields)
                    doc_metrics.weighted_errors += weight * 0.5
                else:  # not exists and not extracted
                    doc_metrics.true_negatives += 1
                
                # Track confidence
                if is_extracted and extracted_confidence is not None:
                    confidence_scores.append(extracted_confidence)
                    is_correct = self._values_match(extracted_value, gt_value, field_name) if gt_exists else False
                    confidence_correct.append(1.0 if is_correct else 0.0)
            
            # Calculate average confidence
            if confidence_scores:
                doc_metrics.average_confidence = sum(confidence_scores) / len(confidence_scores)
                
                # Confidence-weighted accuracy
                if confidence_correct:
                    weighted_sum = sum(
                        conf * correct for conf, correct in zip(confidence_scores, confidence_correct)
                    )
                    total_weight = sum(confidence_scores)
                    if total_weight > 0:
                        doc_metrics.confidence_weighted_accuracy = weighted_sum / total_weight
            
            # Calculate weighted F1
            total_weight = sum(self.get_field_weight(f) for f in field_names)
            if total_weight > 0:
                # Weighted precision and recall
                weighted_tp = sum(
                    self.get_field_weight(f) for f in field_names
                    if self._is_field_correct(extracted, gt, f)
                )
                weighted_fp = doc_metrics.weighted_errors * 0.5  # Approximate
                weighted_fn = doc_metrics.weighted_errors * 0.5  # Approximate
                
                if weighted_tp + weighted_fp > 0:
                    weighted_precision = weighted_tp / (weighted_tp + weighted_fp)
                else:
                    weighted_precision = 0.0
                
                if weighted_tp + weighted_fn > 0:
                    weighted_recall = weighted_tp / (weighted_tp + weighted_fn)
                else:
                    weighted_recall = 0.0
                
                if weighted_precision + weighted_recall > 0:
                    doc_metrics.weighted_f1 = (
                        2 * (weighted_precision * weighted_recall) / (weighted_precision + weighted_recall)
                    )
            
            # Business impact score (inverse of weighted errors, normalized)
            max_possible_errors = sum(self.get_field_weight(f) for f in field_names)
            if max_possible_errors > 0:
                doc_metrics.business_impact_score = 1.0 - (doc_metrics.weighted_errors / max_possible_errors)
                doc_metrics.business_impact_score = max(0.0, min(1.0, doc_metrics.business_impact_score))
            
            # Required fields
            doc_metrics.total_required_fields = len([
                f for f in self.required_fields if self._field_exists_in_gt(gt, f)
            ])
            
            documents[pdf_name] = doc_metrics
        
        return documents
    
    def _get_field_value(self, data: Dict[str, Any], field_name: str) -> Any:
        """Extract field value from data dictionary"""
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
        if isinstance(value, str):
            return value.strip() != ""
        if isinstance(value, (dict, list)):
            return len(value) > 0
        return True
    
    def _values_match(self, extracted: Any, gt: Any, field_name: str) -> bool:
        """Check if values match (simplified - should use same logic as field metrics)"""
        if extracted is None and gt is None:
            return True
        if extracted is None or gt is None:
            return False
        
        # Simple string comparison for now
        # In production, should use same matching logic as FieldMetricsCalculator
        return str(extracted).strip() == str(gt).strip()
    
    def _is_field_correct(self, extracted: Dict[str, Any], gt: Dict[str, Any], field_name: str) -> bool:
        """Check if field is correctly extracted"""
        extracted_value = self._get_field_value(extracted, field_name)
        gt_value = self._get_field_value(gt, field_name)
        is_extracted = self._is_field_extracted(extracted, field_name)
        gt_exists = self._field_exists_in_gt(gt, field_name)
        
        if gt_exists and is_extracted:
            return self._values_match(extracted_value, gt_value, field_name)
        elif not gt_exists and not is_extracted:
            return True  # Correctly not extracted
        else:
            return False  # Mismatch


class AggregateDocumentMetrics:
    """Aggregate metrics across all documents"""
    
    def __init__(self, document_metrics: Dict[str, DocumentMetrics]):
        """Initialize with document metrics"""
        self.document_metrics = document_metrics
        self._calculate_aggregates()
    
    def _calculate_aggregates(self):
        """Calculate aggregate statistics"""
        if not self.document_metrics:
            return
        
        docs = list(self.document_metrics.values())
        
        # Extraction rate
        self.mean_extraction_rate = sum(d.extraction_rate for d in docs) / len(docs)
        self.median_extraction_rate = sorted([d.extraction_rate for d in docs])[len(docs) // 2]
        
        # Accuracy metrics (macro-averaged)
        self.mean_precision = sum(d.precision for d in docs) / len(docs)
        self.mean_recall = sum(d.recall for d in docs) / len(docs)
        self.mean_f1 = sum(d.f1_score for d in docs) / len(docs)
        self.mean_accuracy = sum(d.accuracy for d in docs) / len(docs)
        
        # Required fields correctness
        self.hard_pass_count = sum(1 for d in docs if d.all_required_fields_correct)
        self.hard_pass_rate = self.hard_pass_count / len(docs) if docs else 0.0
        
        # Confidence
        confidences = [d.average_confidence for d in docs if d.average_confidence is not None]
        self.mean_confidence = sum(confidences) / len(confidences) if confidences else None
        
        # Business impact
        self.mean_business_impact_score = sum(d.business_impact_score for d in docs) / len(docs)
        self.mean_weighted_f1 = sum(d.weighted_f1 for d in docs) / len(docs)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting"""
        return {
            "total_documents": len(self.document_metrics),
            "mean_extraction_rate": self.mean_extraction_rate,
            "median_extraction_rate": self.median_extraction_rate,
            "mean_precision": self.mean_precision,
            "mean_recall": self.mean_recall,
            "mean_f1": self.mean_f1,
            "mean_accuracy": self.mean_accuracy,
            "hard_pass_count": self.hard_pass_count,
            "hard_pass_rate": self.hard_pass_rate,
            "mean_confidence": self.mean_confidence,
            "mean_business_impact_score": self.mean_business_impact_score,
            "mean_weighted_f1": self.mean_weighted_f1,
        }
