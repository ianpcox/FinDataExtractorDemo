"""Subtype-specific field extractors for invoice extensions"""

import logging
import re
from typing import Dict, Any, Optional, List
from datetime import date
from decimal import Decimal, InvalidOperation
from dateutil import parser as date_parser

from src.models.invoice_subtypes import (
    InvoiceSubtype,
    ShiftServiceExtension,
    PerDiemTravelExtension,
    TimesheetShift,
    TimesheetData,
)

logger = logging.getLogger(__name__)


class ShiftServiceExtractor:
    """Extractor for shift-based service invoice fields"""
    
    def extract(
        self,
        doc_intelligence_data: Dict[str, Any],
        invoice_text: Optional[str] = None
    ) -> Optional[ShiftServiceExtension]:
        """
        Extract shift service extension data from invoice
        
        Args:
            doc_intelligence_data: Document Intelligence extraction data
            invoice_text: Optional raw text content for pattern matching
            
        Returns:
            ShiftServiceExtension if data found, None otherwise
        """
        extension = ShiftServiceExtension()
        
        # Get text content for pattern matching
        if not invoice_text:
            invoice_text = self._extract_text_from_di_data(doc_intelligence_data)
        
        if not invoice_text:
            return None
        
        # Extract service location
        extension.service_location = self._extract_service_location(
            doc_intelligence_data, invoice_text
        )
        
        # Extract billing period
        period = self._extract_billing_period(invoice_text)
        if period:
            extension.billing_period_start = period.get("start")
            extension.billing_period_end = period.get("end")
        
        # Extract shift rate
        extension.shift_rate = self._extract_shift_rate(
            doc_intelligence_data, invoice_text
        )
        
        # Extract total shifts billed
        extension.total_shifts_billed = self._extract_total_shifts(
            doc_intelligence_data, invoice_text
        )
        
        # Extract minimum shifts per period
        extension.min_shifts_per_period = self._extract_min_shifts(invoice_text)
        
        # Only return if we found at least one field
        if any([
            extension.service_location,
            extension.billing_period_start,
            extension.shift_rate,
            extension.total_shifts_billed
        ]):
            return extension
        
        return None
    
    def _extract_text_from_di_data(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract text content from Document Intelligence data"""
        content = data.get("content", "")
        if content:
            return content
        
        # Try to reconstruct from fields
        fields = data.get("fields", {})
        text_parts = []
        for field_name, field_value in fields.items():
            if isinstance(field_value, dict):
                text_parts.append(field_value.get("content", ""))
            elif isinstance(field_value, str):
                text_parts.append(field_value)
        
        return " ".join(text_parts) if text_parts else None
    
    def _extract_service_location(
        self,
        di_data: Dict[str, Any],
        text: str
    ) -> Optional[str]:
        """Extract service location (site/branch/airport code)"""
        # Try Document Intelligence fields first
        location_fields = ["service_location", "location", "site", "airport", "branch"]
        for field in location_fields:
            value = di_data.get(field)
            if value:
                if isinstance(value, dict):
                    return value.get("content") or value.get("value")
                return str(value)
        
        # Pattern match in text
        patterns = [
            r"location[:\s]+([A-Z0-9]{3,10})",
            r"site[:\s]+([A-Z0-9]{3,10})",
            r"airport[:\s]+([A-Z]{3})",
            r"branch[:\s]+([A-Z0-9]{2,10})"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_billing_period(self, text: str) -> Optional[Dict[str, date]]:
        """Extract billing period start and end dates"""
        # Support multiple date formats: MM/DD/YYYY, MM-DD-YYYY, YYYY-MM-DD
        period_patterns = [
            r"period[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\s+to\s+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
            r"billing period[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\s+to\s+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
            r"billing period[:\s]+(\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})\s+to\s+(\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})",  # ISO format
            r"from\s+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\s+to\s+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
            r"from\s+(\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})\s+to\s+(\d{4}[\/\-]\d{1,2}[\/\-]\d{1,2})",  # ISO format
        ]
        
        for pattern in period_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    start_date = self._parse_date(match.group(1))
                    end_date = self._parse_date(match.group(2))
                    if start_date and end_date:
                        return {"start": start_date, "end": end_date}
                except Exception as e:
                    logger.debug(f"Error parsing period dates: {e}")
        
        return None
    
    def _extract_shift_rate(
        self,
        di_data: Dict[str, Any],
        text: str
    ) -> Optional[Decimal]:
        """Extract shift rate"""
        rate_fields = ["shift_rate", "rate", "per_shift", "shift_cost"]
        for field in rate_fields:
            value = di_data.get(field)
            if value:
                return self._parse_decimal(value)
        
        patterns = [
            r"shift\s+rate[:\s]+\$?(\d+(?:\.\d{2})?)",
            r"rate\s+per\s+shift[:\s]+\$?(\d+(?:\.\d{2})?)",
            r"per\s+shift[:\s]+\$?(\d+(?:\.\d{2})?)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self._parse_decimal(match.group(1))
        
        return None
    
    def _extract_total_shifts(
        self,
        di_data: Dict[str, Any],
        text: str
    ) -> Optional[int]:
        """Extract total shifts billed"""
        shift_fields = ["total_shifts", "shifts", "shift_count", "number_of_shifts"]
        for field in shift_fields:
            value = di_data.get(field)
            if value:
                try:
                    if isinstance(value, dict):
                        value = value.get("content") or value.get("value")
                    return int(float(str(value)))
                except (ValueError, TypeError):
                    continue
        
        patterns = [
            r"total\s+shifts?[:\s]+(\d+)",
            r"number\s+of\s+shifts?[:\s]+(\d+)",
            r"(\d+)\s+shifts?"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    def _extract_min_shifts(self, text: str) -> Optional[int]:
        """Extract minimum shifts per period"""
        patterns = [
            r"minimum\s+shifts?[:\s]+(\d+)",
            r"min\s+shifts?[:\s]+(\d+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string to date object"""
        if not date_str:
            return None
        
        try:
            dt = date_parser.parse(date_str)
            return dt.date()
        except Exception:
            try:
                parts = re.split(r'[\/\-]', date_str.strip())
                if len(parts) == 3:
                    month, day, year = map(int, parts)
                    if year < 100:
                        year += 2000
                    return date(year, month, day)
            except Exception:
                pass
        
        return None
    
    def _parse_decimal(self, value: Any) -> Optional[Decimal]:
        """Parse value to Decimal"""
        if value is None:
            return None
        
        try:
            if isinstance(value, dict):
                value = value.get("content") or value.get("value")
            
            if isinstance(value, (int, float)):
                return Decimal(str(value))
            
            if isinstance(value, str):
                cleaned = re.sub(r'[^\d.]', '', value)
                return Decimal(cleaned)
        except (InvalidOperation, ValueError, TypeError):
            pass
        
        return None


class PerDiemTravelExtractor:
    """Extractor for per-diem travel invoice fields"""
    
    def extract(
        self,
        doc_intelligence_data: Dict[str, Any],
        line_items: List[Dict[str, Any]],
        invoice_text: Optional[str] = None
    ) -> List[PerDiemTravelExtension]:
        """
        Extract per-diem travel extension data from invoice
        
        Args:
            doc_intelligence_data: Document Intelligence extraction data
            line_items: Invoice line items
            invoice_text: Optional raw text content
            
        Returns:
            List of PerDiemTravelExtension (one per line item)
        """
        extensions = []
        
        # Get text content
        if not invoice_text:
            invoice_text = self._extract_text_from_di_data(doc_intelligence_data)
        
        # Extract per-line travel data
        for line_item in line_items:
            extension = PerDiemTravelExtension()
            
            description = line_item.get("description", "")
            
            # Extract traveller information
            extension.traveller_id = self._extract_traveller_id(description)
            extension.traveller_name = self._extract_traveller_name(description)
            
            # Extract course/program information
            extension.programme_or_course_code = self._extract_course_code(description)
            
            # Extract locations
            extension.work_location = self._extract_work_location(description)
            extension.destination_location = self._extract_destination_location(description)
            
            # Extract dates
            dates = self._extract_travel_dates(description)
            if dates:
                extension.travel_from_date = dates.get("travel_from")
                extension.travel_to_date = dates.get("travel_to")
                extension.training_start_date = dates.get("training_start")
                extension.training_end_date = dates.get("training_end")
            
            # Extract rates and totals
            extension.daily_rate = self._extract_daily_rate(description)
            extension.travel_days = self._extract_travel_days(description)
            extension.line_total = self._extract_line_total(line_item)
            
            # Only add if we found meaningful data
            if any([
                extension.traveller_id,
                extension.traveller_name,
                extension.programme_or_course_code,
                extension.travel_from_date,
                extension.daily_rate
            ]):
                extensions.append(extension)
        
        return extensions
    
    def _extract_text_from_di_data(self, data: Dict[str, Any]) -> Optional[str]:
        """Extract text content from Document Intelligence data"""
        content = data.get("content", "")
        if content:
            return content
        
        fields = data.get("fields", {})
        text_parts = []
        for field_name, field_value in fields.items():
            if isinstance(field_value, dict):
                text_parts.append(field_value.get("content", ""))
            elif isinstance(field_value, str):
                text_parts.append(field_value)
        
        return " ".join(text_parts) if text_parts else None
    
    def _extract_traveller_id(self, description: str) -> Optional[str]:
        """Extract traveller ID (LMS or employee #)"""
        patterns = [
            r"employee[:\s]+#?([A-Z0-9]{4,10})",
            r"traveller[:\s]+id[:\s]+([A-Z0-9]{4,10})",
            r"lms[:\s]+id[:\s]+([A-Z0-9]{4,10})"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_traveller_name(self, description: str) -> Optional[str]:
        """Extract traveller name"""
        patterns = [
            r"traveller[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)",
            r"employee[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)",
            r"name[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_course_code(self, description: str) -> Optional[str]:
        """Extract programme or course code"""
        patterns = [
            r"course[:\s]+([A-Z0-9]{3,10})",
            r"programme?[:\s]+([A-Z0-9]{3,10})",
            r"program[:\s]+([A-Z0-9]{3,10})"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_work_location(self, description: str) -> Optional[str]:
        """Extract work location (home site)"""
        patterns = [
            r"work\s+location[:\s]+([A-Z0-9]{3,10})",
            r"home\s+site[:\s]+([A-Z0-9]{3,10})"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_destination_location(self, description: str) -> Optional[str]:
        """Extract destination location (training site)"""
        patterns = [
            r"destination[:\s]+([A-Z0-9]{3,10})",
            r"training\s+location[:\s]+([A-Z0-9]{3,10})",
            r"training\s+site[:\s]+([A-Z0-9]{3,10})"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_travel_dates(self, description: str) -> Optional[Dict[str, date]]:
        """Extract travel and training dates"""
        dates = {}
        
        # Travel dates
        travel_pattern = r"travel[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\s+to\s+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})"
        match = re.search(travel_pattern, description, re.IGNORECASE)
        if match:
            dates["travel_from"] = self._parse_date(match.group(1))
            dates["travel_to"] = self._parse_date(match.group(2))
        
        # Training dates
        training_pattern = r"training[:\s]+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\s+to\s+(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})"
        match = re.search(training_pattern, description, re.IGNORECASE)
        if match:
            dates["training_start"] = self._parse_date(match.group(1))
            dates["training_end"] = self._parse_date(match.group(2))
        
        return dates if dates else None
    
    def _extract_daily_rate(self, description: str) -> Optional[Decimal]:
        """Extract daily rate"""
        patterns = [
            r"daily\s+rate[:\s]+\$?(\d+(?:\.\d{2})?)",
            r"per\s+diem[:\s]+\$?(\d+(?:\.\d{2})?)",
            r"rate[:\s]+\$?(\d+(?:\.\d{2})?)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                try:
                    return Decimal(match.group(1))
                except (InvalidOperation, ValueError):
                    continue
        
        return None
    
    def _extract_travel_days(self, description: str) -> Optional[int]:
        """Extract travel days"""
        patterns = [
            r"travel\s+days?[:\s]+(\d+)",
            r"days?\s+travelled[:\s]+(\d+)",
            r"(\d+)\s+days?"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        
        return None
    
    def _extract_line_total(self, line_item: Dict[str, Any]) -> Optional[Decimal]:
        """Extract line total amount"""
        amount = line_item.get("amount") or line_item.get("total")
        if amount:
            try:
                if isinstance(amount, dict):
                    amount = amount.get("content") or amount.get("value")
                return Decimal(str(amount))
            except (InvalidOperation, ValueError, TypeError):
                pass
        return None
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse date string to date object"""
        if not date_str:
            return None
        
        try:
            dt = date_parser.parse(date_str)
            return dt.date()
        except Exception:
            try:
                parts = re.split(r'[\/\-]', date_str.strip())
                if len(parts) == 3:
                    month, day, year = map(int, parts)
                    if year < 100:
                        year += 2000
                    return date(year, month, day)
            except Exception:
                pass
        
        return None

