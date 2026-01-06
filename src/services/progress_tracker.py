"""Progress tracking service for invoice processing pipeline

Tracks progress for:
- Preprocessing
- Ingestion
- Extraction
- LLM Evaluation

Uses in-memory storage (thread-safe) for real-time progress tracking.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum
import asyncio
import logging

logger = logging.getLogger(__name__)


class ProcessingStep(str, Enum):
    """Processing steps in the pipeline"""
    PREPROCESSING = "preprocessing"
    INGESTION = "ingestion"
    EXTRACTION = "extraction"
    LLM_EVALUATION = "llm_evaluation"
    COMPLETE = "complete"


class ProgressTracker:
    """Thread-safe progress tracker for invoice processing"""
    
    _instance = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._progress: Dict[str, Dict[str, Any]] = {}
            cls._instance._lock = asyncio.Lock()
        return cls._instance
    
    async def start(self, invoice_id: str, step: ProcessingStep, message: str = "") -> None:
        """
        Start tracking progress for an invoice at a specific step
        
        Args:
            invoice_id: Invoice ID
            step: Processing step
            message: Optional status message
        """
        async with self._lock:
            if invoice_id not in self._progress:
                self._progress[invoice_id] = {
                    "invoice_id": invoice_id,
                    "current_step": step.value,
                    "progress_percentage": 0,
                    "status": "running",
                    "message": message,
                    "started_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat(),
                    "steps": {}
                }
            else:
                self._progress[invoice_id]["current_step"] = step.value
                self._progress[invoice_id]["message"] = message
                self._progress[invoice_id]["updated_at"] = datetime.utcnow().isoformat()
            
            # Initialize step tracking
            if step.value not in self._progress[invoice_id]["steps"]:
                self._progress[invoice_id]["steps"][step.value] = {
                    "status": "running",
                    "progress": 0,
                    "started_at": datetime.utcnow().isoformat()
                }
    
    async def update(
        self,
        invoice_id: str,
        progress_percentage: int,
        message: Optional[str] = None,
        step: Optional[ProcessingStep] = None
    ) -> None:
        """
        Update progress for an invoice
        
        Args:
            invoice_id: Invoice ID
            progress_percentage: Progress percentage (0-100)
            message: Optional status message
            step: Optional step (if updating different step)
        """
        async with self._lock:
            if invoice_id not in self._progress:
                logger.warning(f"Progress update for unknown invoice_id: {invoice_id}")
                return
            
            self._progress[invoice_id]["progress_percentage"] = max(0, min(100, progress_percentage))
            self._progress[invoice_id]["updated_at"] = datetime.utcnow().isoformat()
            
            if message:
                self._progress[invoice_id]["message"] = message
            
            if step:
                self._progress[invoice_id]["current_step"] = step.value
            
            # Update step progress
            current_step = step.value if step else self._progress[invoice_id]["current_step"]
            if current_step in self._progress[invoice_id]["steps"]:
                self._progress[invoice_id]["steps"][current_step]["progress"] = progress_percentage
                self._progress[invoice_id]["steps"][current_step]["updated_at"] = datetime.utcnow().isoformat()
    
    async def complete_step(
        self,
        invoice_id: str,
        step: ProcessingStep,
        message: Optional[str] = None
    ) -> None:
        """
        Mark a step as complete
        
        Args:
            invoice_id: Invoice ID
            step: Completed step
            message: Optional completion message
        """
        async with self._lock:
            if invoice_id not in self._progress:
                logger.warning(f"Step completion for unknown invoice_id: {invoice_id}")
                return
            
            if step.value in self._progress[invoice_id]["steps"]:
                self._progress[invoice_id]["steps"][step.value]["status"] = "complete"
                self._progress[invoice_id]["steps"][step.value]["progress"] = 100
                self._progress[invoice_id]["steps"][step.value]["completed_at"] = datetime.utcnow().isoformat()
            
            if message:
                self._progress[invoice_id]["message"] = message
            
            self._progress[invoice_id]["updated_at"] = datetime.utcnow().isoformat()
    
    async def complete(self, invoice_id: str, message: str = "Processing complete") -> None:
        """
        Mark processing as complete for an invoice
        
        Args:
            invoice_id: Invoice ID
            message: Completion message
        """
        async with self._lock:
            if invoice_id not in self._progress:
                logger.warning(f"Completion for unknown invoice_id: {invoice_id}")
                return
            
            self._progress[invoice_id]["status"] = "complete"
            self._progress[invoice_id]["current_step"] = ProcessingStep.COMPLETE.value
            self._progress[invoice_id]["progress_percentage"] = 100
            self._progress[invoice_id]["message"] = message
            self._progress[invoice_id]["updated_at"] = datetime.utcnow().isoformat()
            self._progress[invoice_id]["completed_at"] = datetime.utcnow().isoformat()
    
    async def error(self, invoice_id: str, error_message: str, step: Optional[ProcessingStep] = None) -> None:
        """
        Mark processing as error for an invoice
        
        Args:
            invoice_id: Invoice ID
            error_message: Error message
            step: Optional step where error occurred
        """
        async with self._lock:
            if invoice_id not in self._progress:
                logger.warning(f"Error for unknown invoice_id: {invoice_id}")
                return
            
            self._progress[invoice_id]["status"] = "error"
            self._progress[invoice_id]["message"] = error_message
            self._progress[invoice_id]["updated_at"] = datetime.utcnow().isoformat()
            
            if step and step.value in self._progress[invoice_id]["steps"]:
                self._progress[invoice_id]["steps"][step.value]["status"] = "error"
                self._progress[invoice_id]["steps"][step.value]["error"] = error_message
    
    async def get(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """
        Get progress for an invoice
        
        Args:
            invoice_id: Invoice ID
            
        Returns:
            Progress dictionary or None if not found
        """
        async with self._lock:
            return self._progress.get(invoice_id)
    
    async def clear(self, invoice_id: str) -> None:
        """
        Clear progress for an invoice (cleanup)
        
        Args:
            invoice_id: Invoice ID
        """
        async with self._lock:
            if invoice_id in self._progress:
                del self._progress[invoice_id]


# Global instance
progress_tracker = ProgressTracker()

