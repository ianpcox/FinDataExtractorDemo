"""Invoice subtype definitions and schema extensions"""

from typing import Dict, Any, Optional, List
from enum import Enum
from pydantic import BaseModel, Field
from datetime import date
from decimal import Decimal


class InvoiceSubtype(str, Enum):
    """Invoice subtypes"""
    STANDARD_INVOICE = "STANDARD_INVOICE"
    SHIFT_SERVICE_INVOICE = "SHIFT_SERVICE_INVOICE"
    PER_DIEM_TRAVEL_INVOICE = "PER_DIEM_TRAVEL_INVOICE"


class ShiftServiceExtension(BaseModel):
    """Extension data for shift-based service invoices"""
    service_location: Optional[str] = None
    billing_period_start: Optional[date] = None
    billing_period_end: Optional[date] = None
    shift_rate: Optional[Decimal] = None
    total_shifts_billed: Optional[int] = None
    min_shifts_per_period: Optional[int] = None


class TimesheetShift(BaseModel):
    """Individual shift entry from timesheet"""
    date: date
    worker_name: str
    shift_number: int
    time_in: Optional[str] = None
    time_out: Optional[str] = None


class TimesheetData(BaseModel):
    """Timesheet supporting document data"""
    representative_name: Optional[str] = None
    signature_present: bool = False
    comments: Optional[str] = None
    shifts: List[TimesheetShift] = Field(default_factory=list)


class PerDiemTravelExtension(BaseModel):
    """Extension data for per-diem travel invoices"""
    traveller_id: Optional[str] = None
    traveller_name: Optional[str] = None
    programme_or_course_code: Optional[str] = None
    work_location: Optional[str] = None
    destination_location: Optional[str] = None
    travel_from_date: Optional[date] = None
    travel_to_date: Optional[date] = None
    training_start_date: Optional[date] = None
    training_end_date: Optional[date] = None
    travel_days: Optional[int] = None
    daily_rate: Optional[Decimal] = None
    line_total: Optional[Decimal] = None


class InvoiceExtensions(BaseModel):
    """Container for invoice subtype-specific extensions"""
    shift_service: Optional[ShiftServiceExtension] = None
    per_diem_travel: Optional[List[PerDiemTravelExtension]] = None
    timesheet_data: Optional[TimesheetData] = None


def create_extension_from_data(
    subtype: InvoiceSubtype,
    data: Dict[str, Any]
) -> InvoiceExtensions:
    """
    Create extension object from raw data
    
    Args:
        subtype: Invoice subtype
        data: Raw extension data dictionary
        
    Returns:
        InvoiceExtensions instance
    """
    extensions = InvoiceExtensions()
    
    if subtype == InvoiceSubtype.SHIFT_SERVICE_INVOICE:
        extensions.shift_service = ShiftServiceExtension(**data.get("shift_service", {}))
    elif subtype == InvoiceSubtype.PER_DIEM_TRAVEL_INVOICE:
        travel_data = data.get("per_diem_travel", [])
        if isinstance(travel_data, list):
            extensions.per_diem_travel = [
                PerDiemTravelExtension(**item) for item in travel_data
            ]
        elif isinstance(travel_data, dict):
            extensions.per_diem_travel = [PerDiemTravelExtension(**travel_data)]
    
    return extensions

