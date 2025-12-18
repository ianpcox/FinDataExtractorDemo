"""Decimal wire serialization utilities for contract stability"""

from decimal import Decimal, InvalidOperation
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)


def decimal_to_wire(d: Optional[Decimal]) -> Optional[str]:
    """
    Convert Decimal to wire-safe string representation.
    
    Args:
        d: Decimal value or None
        
    Returns:
        String representation without scientific notation, or None
        
    Examples:
        >>> decimal_to_wire(Decimal("123.45"))
        "123.45"
        >>> decimal_to_wire(Decimal("0.0000001"))
        "0.0000001"
        >>> decimal_to_wire(None)
        None
    """
    if d is None:
        return None
    
    # Use format with 'f' to avoid scientific notation
    # This preserves precision without E notation
    try:
        # Convert to string and normalize (remove trailing zeros after decimal)
        s = format(d, 'f')
        # Remove trailing zeros and decimal point if unnecessary
        if '.' in s:
            s = s.rstrip('0').rstrip('.')
        return s if s != '' else '0'
    except Exception as e:
        logger.warning(f"Failed to convert Decimal to wire format: {e}")
        return str(d)


def wire_to_decimal(x: Any) -> Optional[Decimal]:
    """
    Parse wire value to Decimal safely.
    
    Args:
        x: Wire value (None, str, int, float, or Decimal)
        
    Returns:
        Decimal value or None
        
    Examples:
        >>> wire_to_decimal("123.45")
        Decimal("123.45")
        >>> wire_to_decimal(123)
        Decimal("123")
        >>> wire_to_decimal(None)
        None
        >>> wire_to_decimal("")
        None
    """
    if x is None or x == "":
        return None
    
    if isinstance(x, Decimal):
        return x
    
    try:
        # Always convert via string to avoid float precision issues
        return Decimal(str(x))
    except (InvalidOperation, ValueError, TypeError) as e:
        logger.warning(f"Failed to parse value as Decimal: {x}, error: {e}")
        return None

