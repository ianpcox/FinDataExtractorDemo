"""
Confidence calibration metrics - analyze whether confidence scores accurately reflect correctness.

Uses overall confidence alongside correctness to build calibration metrics.
"""

from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict
try:
    import numpy as np
except ImportError:
    # Fallback if numpy not available
    def corrcoef(x, y):
        """Simple correlation calculation without numpy"""
        if len(x) != len(y) or len(x) < 2:
            return [[1.0, 0.0], [0.0, 1.0]]
        
        mean_x = sum(x) / len(x)
        mean_y = sum(y) / len(y)
        
        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(len(x)))
        denom_x = sum((x[i] - mean_x) ** 2 for i in range(len(x)))
        denom_y = sum((y[i] - mean_y) ** 2 for i in range(len(y)))
        
        if denom_x == 0 or denom_y == 0:
            return [[1.0, 0.0], [0.0, 1.0]]
        
        corr = numerator / ((denom_x * denom_y) ** 0.5)
        return [[1.0, corr], [corr, 1.0]]
    
    class np:
        @staticmethod
        def corrcoef(x, y):
            result = corrcoef(x, y)
            return [[result[0][0], result[0][1]], [result[1][0], result[1][1]]]
        
        @staticmethod
        def isnan(x):
            return x != x


@dataclass
class ConfidenceCalibrationMetrics:
    """Confidence calibration metrics for a set of documents"""
    # Binned calibration data
    bins: Dict[str, Dict[str, float]]  # bin -> {"mean_confidence": float, "mean_correctness": float, "samples": int}
    
    # Overall calibration metrics
    expected_calibration_error: float = 0.0
    max_calibration_error: float = 0.0
    calibration_slope: float = 0.0
    
    def __init__(self):
        self.bins = defaultdict(lambda: {"mean_confidence": 0.0, "mean_correctness": 0.0, "samples": 0})
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting"""
        return {
            "bins": dict(self.bins),
            "expected_calibration_error": self.expected_calibration_error,
            "max_calibration_error": self.max_calibration_error,
            "calibration_slope": self.calibration_slope,
        }


class ConfidenceCalibrationCalculator:
    """Calculate confidence calibration metrics"""
    
    def __init__(self, bin_edges: Optional[List[float]] = None):
        """
        Initialize calculator.
        
        Args:
            bin_edges: Confidence bin edges (default: [0.0, 0.5, 0.7, 0.8, 0.9, 1.0])
        """
        self.bin_edges = bin_edges or [0.0, 0.5, 0.7, 0.8, 0.9, 1.0]
    
    def calculate_calibration(
        self,
        documents: List[Dict[str, Any]],
        ground_truth: List[Dict[str, Any]],
        field_names: List[str],
    ) -> ConfidenceCalibrationMetrics:
        """
        Calculate confidence calibration metrics.
        
        Args:
            documents: List of extraction results with overall_confidence
            ground_truth: List of ground truth values
            field_names: List of all field names
        
        Returns:
            ConfidenceCalibrationMetrics
        """
        metrics = ConfidenceCalibrationMetrics()
        
        # Collect confidence and correctness pairs
        confidence_correctness_pairs = []
        
        for doc, gt in zip(documents, ground_truth):
            # Get overall confidence from document
            overall_confidence = self._get_overall_confidence(doc)
            if overall_confidence is None:
                continue
            
            # Calculate document-level correctness
            correctness = self._calculate_document_correctness(doc, gt, field_names)
            
            confidence_correctness_pairs.append((overall_confidence, correctness))
        
        if not confidence_correctness_pairs:
            return metrics
        
        # Bin the data
        for conf, correct in confidence_correctness_pairs:
            bin_key = self._get_bin_key(conf)
            bin_data = metrics.bins[bin_key]
            bin_data["mean_confidence"] = (bin_data["mean_confidence"] * bin_data["samples"] + conf) / (bin_data["samples"] + 1)
            bin_data["mean_correctness"] = (bin_data["mean_correctness"] * bin_data["samples"] + correct) / (bin_data["samples"] + 1)
            bin_data["samples"] += 1
        
        # Calculate calibration errors
        confidences = [c for c, _ in confidence_correctness_pairs]
        correctnesses = [cr for _, cr in confidence_correctness_pairs]
        
        if len(confidences) > 1:
            # Expected Calibration Error (ECE)
            ece = 0.0
            total_samples = len(confidences)
            
            for bin_key, bin_data in metrics.bins.items():
                if bin_data["samples"] > 0:
                    bin_weight = bin_data["samples"] / total_samples
                    bin_error = abs(bin_data["mean_confidence"] - bin_data["mean_correctness"])
                    ece += bin_weight * bin_error
            
            metrics.expected_calibration_error = ece
            
            # Max Calibration Error (MCE)
            max_error = max(
                abs(bin_data["mean_confidence"] - bin_data["mean_correctness"])
                for bin_data in metrics.bins.values()
                if bin_data["samples"] > 0
            )
            metrics.max_calibration_error = max_error
            
            # Calibration Slope (correlation between confidence and correctness)
            if len(set(confidences)) > 1:
                try:
                    correlation = np.corrcoef(confidences, correctnesses)[0, 1]
                    metrics.calibration_slope = correlation if not np.isnan(correlation) else 0.0
                except Exception:
                    metrics.calibration_slope = 0.0
        
        return metrics
    
    def _get_overall_confidence(self, doc: Dict[str, Any]) -> Optional[float]:
        """Extract overall confidence from document"""
        # Check for overall_confidence field
        if "overall_confidence" in doc:
            return doc.get("overall_confidence")
        
        # Check for extraction_confidence
        if "extraction_confidence" in doc:
            return doc.get("extraction_confidence")
        
        # Calculate from field confidences
        if "extracted_fields" in doc:
            confidences = []
            for field_data in doc["extracted_fields"].values():
                if isinstance(field_data, dict):
                    conf = field_data.get("confidence")
                    if conf is not None:
                        confidences.append(conf)
            
            if confidences:
                return sum(confidences) / len(confidences)
        
        return None
    
    def _calculate_document_correctness(self, doc: Dict[str, Any], gt: Dict[str, Any], field_names: List[str]) -> float:
        """Calculate document-level correctness (0.0 to 1.0)"""
        correct = 0
        total = 0
        
        for field_name in field_names:
            extracted_value = self._get_field_value(doc, field_name)
            gt_value = self._get_field_value(gt, field_name)
            is_extracted = self._is_field_extracted(doc, field_name)
            gt_exists = self._field_exists_in_gt(gt, field_name)
            
            if gt_exists:
                total += 1
                if is_extracted and self._values_match(extracted_value, gt_value, field_name):
                    correct += 1
            elif not gt_exists and not is_extracted:
                total += 1
                correct += 1  # Correctly not extracted
        
        if total == 0:
            return 0.0
        
        return correct / total
    
    def _get_field_value(self, data: Dict[str, Any], field_name: str) -> Any:
        """Extract field value from data dictionary"""
        if "extracted_fields" in data and field_name in data["extracted_fields"]:
            field_data = data["extracted_fields"][field_name]
            if isinstance(field_data, dict):
                return field_data.get("value")
            return field_data
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
        """Check if values match (simplified)"""
        if extracted is None and gt is None:
            return True
        if extracted is None or gt is None:
            return False
        return str(extracted).strip() == str(gt).strip()
    
    def _get_bin_key(self, confidence: float) -> str:
        """Get bin key for confidence value"""
        for i in range(len(self.bin_edges) - 1):
            if self.bin_edges[i] <= confidence < self.bin_edges[i + 1]:
                return f"{self.bin_edges[i]:.1f}-{self.bin_edges[i+1]:.1f}"
        
        # Handle edge case
        if confidence >= self.bin_edges[-1]:
            return f"{self.bin_edges[-2]:.1f}-{self.bin_edges[-1]:.1f}"
        
        return f"{self.bin_edges[0]:.1f}-{self.bin_edges[1]:.1f}"
