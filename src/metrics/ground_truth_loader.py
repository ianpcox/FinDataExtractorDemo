"""
Ground truth data loader for invoice extraction evaluation.

Supports loading ground truth from:
- CSV files
- JSON files
- Python dictionaries
"""

from typing import Dict, Any, List, Optional
import csv
import json
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class GroundTruthLoader:
    """Load and manage ground truth data for evaluation"""
    
    def __init__(self, ground_truth_path: Optional[str] = None):
        """
        Initialize ground truth loader.
        
        Args:
            ground_truth_path: Path to ground truth file (CSV or JSON)
        """
        self.ground_truth_path = ground_truth_path
        self.ground_truth_data: Dict[str, Dict[str, Any]] = {}
        
        if ground_truth_path and os.path.exists(ground_truth_path):
            self.load(ground_truth_path)
    
    def load(self, path: str) -> None:
        """Load ground truth from file"""
        path_obj = Path(path)
        
        if path_obj.suffix.lower() == '.csv':
            self._load_csv(path)
        elif path_obj.suffix.lower() == '.json':
            self._load_json(path)
        else:
            raise ValueError(f"Unsupported ground truth format: {path_obj.suffix}")
    
    def _load_csv(self, path: str) -> None:
        """Load ground truth from CSV file"""
        # Expected format:
        # pdf_name,field_name,value,exists
        # or
        # pdf_name,field1,field2,field3,...
        
        with open(path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                pdf_name = row.get("pdf_name") or row.get("document_id")
                if not pdf_name:
                    continue
                
                if pdf_name not in self.ground_truth_data:
                    self.ground_truth_data[pdf_name] = {}
                
                # Check if format is field_name,value,exists
                if "field_name" in row:
                    field_name = row["field_name"]
                    value = row.get("value", "")
                    exists = row.get("exists", "true").lower() == "true"
                    
                    if exists and value:
                        self.ground_truth_data[pdf_name][field_name] = self._parse_value(value)
                else:
                    # Format is pdf_name,field1,field2,...
                    for field_name, value in row.items():
                        if field_name == "pdf_name" or field_name == "document_id":
                            continue
                        
                        if value and value.strip():
                            self.ground_truth_data[pdf_name][field_name] = self._parse_value(value)
    
    def _load_json(self, path: str) -> None:
        """Load ground truth from JSON file"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Expected format: {pdf_name: {field_name: value, ...}, ...}
        if isinstance(data, dict):
            for pdf_name, fields in data.items():
                self.ground_truth_data[pdf_name] = {}
                for field_name, value in fields.items():
                    if value is not None:
                        self.ground_truth_data[pdf_name][field_name] = value
    
    def _parse_value(self, value: str) -> Any:
        """Parse a string value to appropriate type"""
        if not value or value.strip() == "":
            return None
        
        value = value.strip()
        
        # Try to parse as number
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass
        
        # Try to parse as boolean
        if value.lower() in ('true', 'false'):
            return value.lower() == 'true'
        
        # Return as string
        return value
    
    def get_ground_truth(self, pdf_name: str) -> Dict[str, Any]:
        """Get ground truth for a specific PDF"""
        return self.ground_truth_data.get(pdf_name, {})
    
    def get_all_ground_truth(self) -> Dict[str, Dict[str, Any]]:
        """Get all ground truth data"""
        return self.ground_truth_data
    
    def has_ground_truth(self, pdf_name: str) -> bool:
        """Check if ground truth exists for a PDF"""
        return pdf_name in self.ground_truth_data
    
    def get_field_value(self, pdf_name: str, field_name: str) -> Any:
        """Get ground truth value for a specific field"""
        pdf_gt = self.ground_truth_data.get(pdf_name, {})
        return pdf_gt.get(field_name)
    
    def field_exists(self, pdf_name: str, field_name: str) -> bool:
        """Check if field exists in ground truth"""
        value = self.get_field_value(pdf_name, field_name)
        if value is None:
            return False
        
        if isinstance(value, str):
            return value.strip() != ""
        if isinstance(value, (dict, list)):
            return len(value) > 0
        return True
    
    def convert_extraction_to_ground_truth_format(
        self,
        extracted_data: List[Dict[str, Any]],
        field_names: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Convert extraction results to ground truth format for comparison.
        
        This is used when we don't have explicit ground truth but want to
        compare extraction results in a standardized format.
        """
        gt_format = []
        
        for extracted in extracted_data:
            pdf_name = extracted.get("pdf_name") or extracted.get("document_id", "unknown")
            gt_entry = {"pdf_name": pdf_name}
            
            for field_name in field_names:
                value = self._get_field_value_from_extraction(extracted, field_name)
                if value is not None:
                    gt_entry[field_name] = value
            
            gt_format.append(gt_entry)
        
        return gt_format
    
    def _get_field_value_from_extraction(self, extracted: Dict[str, Any], field_name: str) -> Any:
        """Extract field value from extraction result"""
        if "extracted_fields" in extracted and field_name in extracted["extracted_fields"]:
            field_data = extracted["extracted_fields"][field_name]
            if isinstance(field_data, dict):
                return field_data.get("value")
            return field_data
        return None
