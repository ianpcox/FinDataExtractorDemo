"""Unit tests for ProgressTracker"""

import pytest
from unittest.mock import patch

from src.services.progress_tracker import ProgressTracker, ProcessingStep


@pytest.mark.unit
@pytest.mark.asyncio
class TestProgressTracker:
    """Test ProgressTracker"""

    async def test_start_tracking(self):
        """Test starting progress tracking"""
        tracker = ProgressTracker()
        await tracker.clear("test-invoice-1")  # Clean slate
        
        await tracker.start("test-invoice-1", ProcessingStep.EXTRACTION, "Starting extraction")
        
        progress = await tracker.get("test-invoice-1")
        
        assert progress is not None
        assert progress["invoice_id"] == "test-invoice-1"
        assert progress["current_step"] == ProcessingStep.EXTRACTION.value
        assert progress["status"] == "running"
        assert progress["message"] == "Starting extraction"
        assert progress["progress_percentage"] == 0

    async def test_update_progress(self):
        """Test updating progress"""
        tracker = ProgressTracker()
        await tracker.clear("test-invoice-2")
        
        await tracker.start("test-invoice-2", ProcessingStep.EXTRACTION)
        await tracker.update("test-invoice-2", 50, "Halfway done")
        
        progress = await tracker.get("test-invoice-2")
        
        assert progress["progress_percentage"] == 50
        assert progress["message"] == "Halfway done"

    async def test_update_progress_bounds(self):
        """Test progress percentage is bounded to 0-100"""
        tracker = ProgressTracker()
        await tracker.clear("test-invoice-3")
        
        await tracker.start("test-invoice-3", ProcessingStep.EXTRACTION)
        
        # Test negative
        await tracker.update("test-invoice-3", -10)
        progress = await tracker.get("test-invoice-3")
        assert progress["progress_percentage"] == 0
        
        # Test over 100
        await tracker.update("test-invoice-3", 150)
        progress = await tracker.get("test-invoice-3")
        assert progress["progress_percentage"] == 100

    async def test_complete_step(self):
        """Test completing a step"""
        tracker = ProgressTracker()
        await tracker.clear("test-invoice-4")
        
        await tracker.start("test-invoice-4", ProcessingStep.EXTRACTION)
        await tracker.complete_step("test-invoice-4", ProcessingStep.EXTRACTION, "Extraction complete")
        
        progress = await tracker.get("test-invoice-4")
        
        assert progress["steps"][ProcessingStep.EXTRACTION.value]["status"] == "complete"
        assert progress["steps"][ProcessingStep.EXTRACTION.value]["progress"] == 100

    async def test_complete_processing(self):
        """Test completing entire processing"""
        tracker = ProgressTracker()
        await tracker.clear("test-invoice-5")
        
        await tracker.start("test-invoice-5", ProcessingStep.EXTRACTION)
        await tracker.complete("test-invoice-5", "All done")
        
        progress = await tracker.get("test-invoice-5")
        
        assert progress["status"] == "complete"
        assert progress["current_step"] == ProcessingStep.COMPLETE.value
        assert progress["progress_percentage"] == 100
        assert progress["message"] == "All done"
        assert "completed_at" in progress

    async def test_error_tracking(self):
        """Test tracking errors"""
        tracker = ProgressTracker()
        await tracker.clear("test-invoice-6")
        
        await tracker.start("test-invoice-6", ProcessingStep.EXTRACTION)
        await tracker.error("test-invoice-6", "Extraction failed", ProcessingStep.EXTRACTION)
        
        progress = await tracker.get("test-invoice-6")
        
        assert progress["status"] == "error"
        assert progress["message"] == "Extraction failed"
        assert progress["steps"][ProcessingStep.EXTRACTION.value]["status"] == "error"

    async def test_get_nonexistent_invoice(self):
        """Test getting progress for nonexistent invoice"""
        tracker = ProgressTracker()
        
        progress = await tracker.get("nonexistent-invoice")
        
        assert progress is None

    async def test_update_nonexistent_invoice(self):
        """Test updating progress for nonexistent invoice"""
        tracker = ProgressTracker()
        
        # Should not raise exception, just log warning
        await tracker.update("nonexistent-invoice", 50)

    async def test_clear_progress(self):
        """Test clearing progress"""
        tracker = ProgressTracker()
        
        await tracker.start("test-invoice-7", ProcessingStep.EXTRACTION)
        await tracker.clear("test-invoice-7")
        
        progress = await tracker.get("test-invoice-7")
        assert progress is None

    async def test_multiple_steps_tracking(self):
        """Test tracking multiple steps"""
        tracker = ProgressTracker()
        await tracker.clear("test-invoice-8")
        
        await tracker.start("test-invoice-8", ProcessingStep.INGESTION)
        await tracker.complete_step("test-invoice-8", ProcessingStep.INGESTION)
        
        await tracker.start("test-invoice-8", ProcessingStep.EXTRACTION)
        await tracker.update("test-invoice-8", 75, step=ProcessingStep.EXTRACTION)
        
        progress = await tracker.get("test-invoice-8")
        
        assert progress["current_step"] == ProcessingStep.EXTRACTION.value
        assert progress["steps"][ProcessingStep.INGESTION.value]["status"] == "complete"
        assert progress["steps"][ProcessingStep.EXTRACTION.value]["progress"] == 75

    async def test_singleton_instance(self):
        """Test ProgressTracker is a singleton"""
        tracker1 = ProgressTracker()
        tracker2 = ProgressTracker()
        
        assert tracker1 is tracker2
        assert tracker1._instance is tracker2._instance

    async def test_concurrent_updates(self):
        """Test concurrent progress updates"""
        tracker = ProgressTracker()
        await tracker.clear("test-invoice-9")
        
        await tracker.start("test-invoice-9", ProcessingStep.EXTRACTION)
        
        # Simulate concurrent updates
        import asyncio
        await asyncio.gather(
            tracker.update("test-invoice-9", 25),
            tracker.update("test-invoice-9", 50),
            tracker.update("test-invoice-9", 75),
        )
        
        progress = await tracker.get("test-invoice-9")
        
        # Should handle concurrent updates gracefully
        assert progress is not None
        assert 0 <= progress["progress_percentage"] <= 100
