"""
Performance benchmarks for large invoices with many line items.

This test suite measures:
1. Extraction performance (time, memory)
2. Database save/load performance
3. Line item processing performance
4. Aggregation validation performance
5. Scalability with increasing line item counts

Requirements:
- Azure Document Intelligence credentials (for real extraction tests)
- Tests can run with mocks for pure performance testing
"""

import pytest
import time
import os
import sys
from pathlib import Path
from datetime import datetime
from decimal import Decimal
from uuid import uuid4
from typing import Dict, List, Any
import tracemalloc

from src.extraction.extraction_service import ExtractionService
from src.extraction.document_intelligence_client import DocumentIntelligenceClient
from src.extraction.field_extractor import FieldExtractor
from src.ingestion.file_handler import FileHandler
from src.models.invoice import Invoice, LineItem, InvoiceState
from src.services.db_service import DatabaseService
from src.validation.aggregation_validator import AggregationValidator
from src.config import settings


class PerformanceMetrics:
    """Container for performance metrics"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.memory_start = None
        self.memory_end = None
        self.memory_peak = None
        self.operations = []
    
    def start(self):
        """Start performance tracking"""
        self.start_time = time.perf_counter()
        tracemalloc.start()
        self.memory_start = tracemalloc.take_snapshot()
    
    def stop(self):
        """Stop performance tracking"""
        self.end_time = time.perf_counter()
        self.memory_end = tracemalloc.take_snapshot()
        self.memory_peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
    
    @property
    def elapsed_time(self) -> float:
        """Get elapsed time in seconds"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0.0
    
    @property
    def memory_delta(self) -> int:
        """Get memory delta in bytes"""
        if self.memory_start and self.memory_end:
            top_stats = self.memory_end.compare_to(self.memory_start, 'lineno')
            total = sum(stat.size_diff for stat in top_stats)
            return total
        return 0
    
    def add_operation(self, name: str, duration: float):
        """Add a timed operation"""
        self.operations.append({
            "name": name,
            "duration": duration,
            "duration_ms": duration * 1000
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "elapsed_time": self.elapsed_time,
            "elapsed_time_ms": self.elapsed_time * 1000,
            "memory_delta_bytes": self.memory_delta,
            "memory_delta_mb": self.memory_delta / (1024 * 1024),
            "memory_peak_bytes": self.memory_peak,
            "memory_peak_mb": self.memory_peak / (1024 * 1024) if self.memory_peak else 0,
            "operations": self.operations
        }


def create_large_invoice(line_item_count: int = 100) -> Invoice:
    """Create a test invoice with many line items"""
    invoice = Invoice(
        id=str(uuid4()),
        file_path=f"test/large_invoice_{line_item_count}.pdf",
        file_name=f"large_invoice_{line_item_count}.pdf",
        upload_date=datetime.utcnow(),
        status="extracted",
        invoice_number=f"INV-{line_item_count}",
        invoice_date=datetime.utcnow().date(),
        vendor_name="Test Vendor",
        total_amount=Decimal("0"),
        currency="CAD",
        line_items=[]
    )
    
    # Create line items
    subtotal = Decimal("0")
    for i in range(1, line_item_count + 1):
        quantity = Decimal(str(i))
        unit_price = Decimal("10.00")
        amount = quantity * unit_price
        subtotal += amount
        
        line_item = LineItem(
            line_number=i,
            description=f"Test Item {i} - Performance Benchmark",
            quantity=quantity,
            unit_price=unit_price,
            amount=amount,
            confidence=0.9,
            tax_rate=Decimal("0.13"),
            tax_amount=amount * Decimal("0.13"),
            gst_amount=amount * Decimal("0.05"),
            pst_amount=amount * Decimal("0.08"),
        )
        invoice.line_items.append(line_item)
    
    # Set invoice totals
    invoice.subtotal = subtotal
    invoice.tax_amount = subtotal * Decimal("0.13")
    invoice.gst_amount = subtotal * Decimal("0.05")
    invoice.pst_amount = subtotal * Decimal("0.08")
    invoice.total_amount = subtotal + invoice.tax_amount
    
    return invoice


@pytest.mark.integration
@pytest.mark.performance
@pytest.mark.slow
class TestLargeInvoicePerformance:
    """Performance benchmarks for large invoices"""
    
    @pytest.mark.parametrize("line_item_count", [10, 50, 100, 200, 500])
    def test_line_item_creation_performance(self, line_item_count):
        """Benchmark line item creation performance"""
        metrics = PerformanceMetrics()
        metrics.start()
        
        invoice = create_large_invoice(line_item_count)
        
        metrics.stop()
        
        assert len(invoice.line_items) == line_item_count
        assert invoice.subtotal is not None
        
        results = metrics.to_dict()
        print(f"\n=== Line Item Creation Performance ({line_item_count} items) ===")
        print(f"Time: {results['elapsed_time_ms']:.2f} ms")
        print(f"Memory: {results['memory_delta_mb']:.2f} MB")
        print(f"Peak Memory: {results['memory_peak_mb']:.2f} MB")
        print(f"Time per item: {results['elapsed_time_ms'] / line_item_count:.4f} ms/item")
        
        # Performance assertions (adjust thresholds as needed)
        assert results['elapsed_time_ms'] < 1000, f"Creation took too long: {results['elapsed_time_ms']} ms"
        assert results['memory_delta_mb'] < 100, f"Memory usage too high: {results['memory_delta_mb']} MB"
    
    @pytest.mark.parametrize("line_item_count", [10, 50, 100, 200, 500])
    @pytest.mark.asyncio
    async def test_aggregation_validation_performance(self, line_item_count):
        """Benchmark aggregation validation performance"""
        invoice = create_large_invoice(line_item_count)
        
        metrics = PerformanceMetrics()
        metrics.start()
        
        validation_summary = AggregationValidator.get_validation_summary(invoice)
        
        metrics.stop()
        
        assert validation_summary["all_valid"] is True
        assert validation_summary["total_validations"] == 6
        
        results = metrics.to_dict()
        print(f"\n=== Aggregation Validation Performance ({line_item_count} items) ===")
        print(f"Time: {results['elapsed_time_ms']:.2f} ms")
        print(f"Memory: {results['memory_delta_mb']:.2f} MB")
        print(f"Time per validation: {results['elapsed_time_ms'] / 6:.4f} ms/validation")
        print(f"Time per item: {results['elapsed_time_ms'] / line_item_count:.4f} ms/item")
        
        # Performance assertions
        assert results['elapsed_time_ms'] < 500, f"Validation took too long: {results['elapsed_time_ms']} ms"
    
    @pytest.mark.parametrize("line_item_count", [10, 50, 100, 200, 500])
    @pytest.mark.asyncio
    async def test_database_save_performance(self, db_session, line_item_count):
        """Benchmark database save performance with line items"""
        invoice = create_large_invoice(line_item_count)
        
        metrics = PerformanceMetrics()
        metrics.start()
        
        await DatabaseService.save_invoice(invoice, db=db_session)
        
        metrics.stop()
        
        # Verify save
        saved_invoice = await DatabaseService.get_invoice(invoice.id, db=db_session)
        assert saved_invoice is not None
        assert len(saved_invoice.line_items) == line_item_count
        
        results = metrics.to_dict()
        print(f"\n=== Database Save Performance ({line_item_count} items) ===")
        print(f"Time: {results['elapsed_time_ms']:.2f} ms")
        print(f"Memory: {results['memory_delta_mb']:.2f} MB")
        print(f"Time per item: {results['elapsed_time_ms'] / line_item_count:.4f} ms/item")
        
        # Performance assertions (database saves can be slower)
        assert results['elapsed_time_ms'] < 5000, f"Save took too long: {results['elapsed_time_ms']} ms"
    
    @pytest.mark.parametrize("line_item_count", [10, 50, 100, 200, 500])
    @pytest.mark.asyncio
    async def test_database_load_performance(self, db_session, line_item_count):
        """Benchmark database load performance with line items"""
        invoice = create_large_invoice(line_item_count)
        await DatabaseService.save_invoice(invoice, db=db_session)
        
        metrics = PerformanceMetrics()
        metrics.start()
        
        loaded_invoice = await DatabaseService.get_invoice(invoice.id, db=db_session)
        
        metrics.stop()
        
        assert loaded_invoice is not None
        assert len(loaded_invoice.line_items) == line_item_count
        
        results = metrics.to_dict()
        print(f"\n=== Database Load Performance ({line_item_count} items) ===")
        print(f"Time: {results['elapsed_time_ms']:.2f} ms")
        print(f"Memory: {results['memory_delta_mb']:.2f} MB")
        print(f"Time per item: {results['elapsed_time_ms'] / line_item_count:.4f} ms/item")
        
        # Performance assertions
        assert results['elapsed_time_ms'] < 2000, f"Load took too long: {results['elapsed_time_ms']} ms"
    
    @pytest.mark.parametrize("line_item_count", [10, 50, 100, 200])
    def test_line_item_serialization_performance(self, line_item_count):
        """Benchmark line item serialization (to JSON/dict) performance"""
        invoice = create_large_invoice(line_item_count)
        
        metrics = PerformanceMetrics()
        metrics.start()
        
        # Serialize to dict
        invoice_dict = invoice.model_dump(mode="json")
        
        metrics.stop()
        
        assert "line_items" in invoice_dict
        assert len(invoice_dict["line_items"]) == line_item_count
        
        results = metrics.to_dict()
        print(f"\n=== Line Item Serialization Performance ({line_item_count} items) ===")
        print(f"Time: {results['elapsed_time_ms']:.2f} ms")
        print(f"Memory: {results['memory_delta_mb']:.2f} MB")
        print(f"Time per item: {results['elapsed_time_ms'] / line_item_count:.4f} ms/item")
        
        # Performance assertions
        assert results['elapsed_time_ms'] < 1000, f"Serialization took too long: {results['elapsed_time_ms']} ms"
    
    @pytest.mark.parametrize("line_item_count", [10, 50, 100, 200])
    def test_line_item_sum_calculation_performance(self, line_item_count):
        """Benchmark line item sum calculations"""
        invoice = create_large_invoice(line_item_count)
        
        metrics = PerformanceMetrics()
        metrics.start()
        
        # Calculate various sums
        sum_amounts = sum(item.amount for item in invoice.line_items)
        sum_gst = sum(item.gst_amount or Decimal("0") for item in invoice.line_items)
        sum_pst = sum(item.pst_amount or Decimal("0") for item in invoice.line_items)
        sum_tax = sum(item.tax_amount or Decimal("0") for item in invoice.line_items)
        
        metrics.stop()
        
        assert sum_amounts == invoice.subtotal
        assert abs(sum_gst - invoice.gst_amount) <= Decimal("0.01")
        assert abs(sum_pst - invoice.pst_amount) <= Decimal("0.01")
        
        results = metrics.to_dict()
        print(f"\n=== Line Item Sum Calculation Performance ({line_item_count} items) ===")
        print(f"Time: {results['elapsed_time_ms']:.2f} ms")
        print(f"Memory: {results['memory_delta_mb']:.2f} MB")
        print(f"Time per item: {results['elapsed_time_ms'] / line_item_count:.4f} ms/item")
        
        # Performance assertions
        assert results['elapsed_time_ms'] < 100, f"Sum calculation took too long: {results['elapsed_time_ms']} ms"
    
    @pytest.mark.asyncio
    async def test_full_extraction_pipeline_performance(self, db_session):
        """Benchmark full extraction pipeline with large invoice"""
        # Create a large invoice
        invoice = create_large_invoice(100)
        
        metrics = PerformanceMetrics()
        
        # Simulate extraction pipeline steps
        print("\n=== Full Extraction Pipeline Performance (100 items) ===")
        
        # Step 1: Create invoice
        metrics.start()
        await DatabaseService.save_invoice(invoice, db=db_session)
        metrics.stop()
        create_time = metrics.elapsed_time_ms
        print(f"1. Invoice Creation: {create_time:.2f} ms")
        
        # Step 2: Load invoice
        metrics.start()
        loaded = await DatabaseService.get_invoice(invoice.id, db=db_session)
        metrics.stop()
        load_time = metrics.elapsed_time_ms
        print(f"2. Invoice Load: {load_time:.2f} ms")
        
        # Step 3: Aggregation validation
        metrics.start()
        validation = AggregationValidator.get_validation_summary(loaded)
        metrics.stop()
        validation_time = metrics.elapsed_time_ms
        print(f"3. Aggregation Validation: {validation_time:.2f} ms")
        
        # Step 4: Serialization
        metrics.start()
        serialized = loaded.model_dump(mode="json")
        metrics.stop()
        serialization_time = metrics.elapsed_time_ms
        print(f"4. Serialization: {serialization_time:.2f} ms")
        
        total_time = create_time + load_time + validation_time + serialization_time
        print(f"\nTotal Pipeline Time: {total_time:.2f} ms")
        print(f"Average per item: {total_time / 100:.4f} ms/item")
        
        assert validation["all_valid"] is True
        assert total_time < 10000, f"Pipeline took too long: {total_time} ms"
    
    @pytest.mark.parametrize("concurrent_invoices", [1, 5, 10])
    @pytest.mark.asyncio
    async def test_concurrent_invoice_processing(self, db_session, concurrent_invoices):
        """Benchmark concurrent invoice processing"""
        import asyncio
        
        line_item_count = 50
        invoices = [create_large_invoice(line_item_count) for _ in range(concurrent_invoices)]
        
        metrics = PerformanceMetrics()
        metrics.start()
        
        # Process all invoices concurrently
        tasks = [DatabaseService.save_invoice(inv, db=db_session) for inv in invoices]
        await asyncio.gather(*tasks)
        
        metrics.stop()
        
        # Verify all saved
        for invoice in invoices:
            loaded = await DatabaseService.get_invoice(invoice.id, db=db_session)
            assert loaded is not None
            assert len(loaded.line_items) == line_item_count
        
        results = metrics.to_dict()
        print(f"\n=== Concurrent Processing Performance ({concurrent_invoices} invoices, {line_item_count} items each) ===")
        print(f"Total Time: {results['elapsed_time_ms']:.2f} ms")
        print(f"Time per invoice: {results['elapsed_time_ms'] / concurrent_invoices:.2f} ms/invoice")
        print(f"Throughput: {concurrent_invoices / (results['elapsed_time'] / 60):.2f} invoices/minute")
        print(f"Memory: {results['memory_delta_mb']:.2f} MB")
        
        # Performance assertions
        assert results['elapsed_time_ms'] < 30000, f"Concurrent processing took too long: {results['elapsed_time_ms']} ms"


@pytest.mark.integration
@pytest.mark.performance
@pytest.mark.slow
class TestLargeInvoiceScalability:
    """Scalability tests for very large invoices"""
    
    @pytest.mark.parametrize("line_item_count", [1000, 2000, 5000])
    def test_very_large_invoice_creation(self, line_item_count):
        """Test creation of very large invoices"""
        metrics = PerformanceMetrics()
        metrics.start()
        
        invoice = create_large_invoice(line_item_count)
        
        metrics.stop()
        
        assert len(invoice.line_items) == line_item_count
        
        results = metrics.to_dict()
        print(f"\n=== Very Large Invoice Creation ({line_item_count} items) ===")
        print(f"Time: {results['elapsed_time_ms']:.2f} ms")
        print(f"Memory: {results['memory_delta_mb']:.2f} MB")
        print(f"Peak Memory: {results['memory_peak_mb']:.2f} MB")
        print(f"Time per item: {results['elapsed_time_ms'] / line_item_count:.4f} ms/item")
        
        # For very large invoices, be more lenient
        assert results['elapsed_time_ms'] < 10000, f"Creation took too long: {results['elapsed_time_ms']} ms"
    
    @pytest.mark.parametrize("line_item_count", [1000, 2000, 5000])
    @pytest.mark.asyncio
    async def test_very_large_invoice_validation(self, line_item_count):
        """Test aggregation validation with very large invoices"""
        invoice = create_large_invoice(line_item_count)
        
        metrics = PerformanceMetrics()
        metrics.start()
        
        validation_summary = AggregationValidator.get_validation_summary(invoice)
        
        metrics.stop()
        
        assert validation_summary["all_valid"] is True
        
        results = metrics.to_dict()
        print(f"\n=== Very Large Invoice Validation ({line_item_count} items) ===")
        print(f"Time: {results['elapsed_time_ms']:.2f} ms")
        print(f"Memory: {results['memory_delta_mb']:.2f} MB")
        print(f"Time per item: {results['elapsed_time_ms'] / line_item_count:.4f} ms/item")
        
        # For very large invoices, validation should still be fast
        assert results['elapsed_time_ms'] < 2000, f"Validation took too long: {results['elapsed_time_ms']} ms"
