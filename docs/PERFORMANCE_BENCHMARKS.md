# Performance Benchmarks for Large Invoices

## Overview

The performance benchmark suite (`test_large_invoice_performance.py`) measures and validates the performance characteristics of the invoice extraction system when processing large invoices with many line items.

## Test Suite

### Location
`tests/integration/test_large_invoice_performance.py`

### Test Classes

1. **`TestLargeInvoicePerformance`**: Standard performance tests
2. **`TestLargeInvoiceScalability`**: Scalability tests for very large invoices

## Benchmark Categories

### 1. Line Item Creation Performance
**Test**: `test_line_item_creation_performance`

**What it measures**:
- Time to create invoices with varying line item counts (10, 50, 100, 200, 500)
- Memory usage during creation
- Time per line item

**Metrics**:
- Total creation time (ms)
- Memory delta (MB)
- Peak memory (MB)
- Time per item (ms/item)

**Performance Targets**:
- Creation time < 1000 ms for 500 items
- Memory delta < 100 MB
- Time per item < 2 ms/item

### 2. Aggregation Validation Performance
**Test**: `test_aggregation_validation_performance`

**What it measures**:
- Time to validate aggregations for invoices with many line items
- Memory usage during validation
- Validation throughput

**Metrics**:
- Total validation time (ms)
- Time per validation check
- Time per line item

**Performance Targets**:
- Validation time < 500 ms for 500 items
- Time per item < 1 ms/item

### 3. Database Save Performance
**Test**: `test_database_save_performance`

**What it measures**:
- Time to save invoices with line items to database
- Memory usage during save
- Database write throughput

**Metrics**:
- Total save time (ms)
- Time per line item
- Memory usage

**Performance Targets**:
- Save time < 5000 ms for 500 items
- Time per item < 10 ms/item

### 4. Database Load Performance
**Test**: `test_database_load_performance`

**What it measures**:
- Time to load invoices with line items from database
- Memory usage during load
- Database read throughput

**Metrics**:
- Total load time (ms)
- Time per line item
- Memory usage

**Performance Targets**:
- Load time < 2000 ms for 500 items
- Time per item < 4 ms/item

### 5. Line Item Serialization Performance
**Test**: `test_line_item_serialization_performance`

**What it measures**:
- Time to serialize invoices with line items to JSON/dict
- Memory usage during serialization
- Serialization throughput

**Metrics**:
- Total serialization time (ms)
- Time per line item
- Memory usage

**Performance Targets**:
- Serialization time < 1000 ms for 200 items
- Time per item < 5 ms/item

### 6. Line Item Sum Calculation Performance
**Test**: `test_line_item_sum_calculation_performance`

**What it measures**:
- Time to calculate sums across line items (amounts, taxes)
- Memory usage during calculations
- Calculation throughput

**Metrics**:
- Total calculation time (ms)
- Time per line item
- Memory usage

**Performance Targets**:
- Calculation time < 100 ms for 200 items
- Time per item < 0.5 ms/item

### 7. Full Extraction Pipeline Performance
**Test**: `test_full_extraction_pipeline_performance`

**What it measures**:
- End-to-end performance of complete extraction pipeline
- Breakdown of time by pipeline stage
- Overall throughput

**Pipeline Stages**:
1. Invoice creation
2. Invoice load
3. Aggregation validation
4. Serialization

**Metrics**:
- Time per stage (ms)
- Total pipeline time (ms)
- Time per line item
- Overall throughput

**Performance Targets**:
- Total pipeline time < 10000 ms for 100 items
- Time per item < 100 ms/item

### 8. Concurrent Invoice Processing
**Test**: `test_concurrent_invoice_processing`

**What it measures**:
- Performance when processing multiple invoices concurrently
- Throughput (invoices/minute)
- Memory usage under concurrent load
- Scalability with increasing concurrency

**Metrics**:
- Total processing time (ms)
- Time per invoice (ms)
- Throughput (invoices/minute)
- Memory usage

**Performance Targets**:
- Processing time < 30000 ms for 10 concurrent invoices (50 items each)
- Throughput > 20 invoices/minute

### 9. Very Large Invoice Scalability
**Tests**: `test_very_large_invoice_creation`, `test_very_large_invoice_validation`

**What it measures**:
- Performance with very large invoices (1000, 2000, 5000 line items)
- Memory usage at scale
- Scalability characteristics

**Metrics**:
- Creation/validation time (ms)
- Memory usage (MB)
- Time per item (ms/item)
- Peak memory (MB)

**Performance Targets**:
- Creation time < 10000 ms for 5000 items
- Validation time < 2000 ms for 5000 items
- Memory usage < 500 MB for 5000 items

## Running Benchmarks

### Run All Performance Tests
```bash
pytest tests/integration/test_large_invoice_performance.py -v -m performance
```

### Run Specific Test
```bash
pytest tests/integration/test_large_invoice_performance.py::TestLargeInvoicePerformance::test_line_item_creation_performance -v
```

### Run with Output
```bash
pytest tests/integration/test_large_invoice_performance.py -v -m performance -s
```

### Run Scalability Tests Only
```bash
pytest tests/integration/test_large_invoice_performance.py::TestLargeInvoiceScalability -v
```

### Run with Benchmark Script
```bash
python scripts/run_performance_benchmarks.py
```

### Run with JSON Output (requires pytest-json-report)
```bash
pip install pytest-json-report
pytest tests/integration/test_large_invoice_performance.py -v -m performance --json-report --json-report-file=benchmark_results.json
```

## Performance Metrics

### PerformanceMetrics Class

The `PerformanceMetrics` class tracks:
- **Elapsed Time**: Total execution time in seconds and milliseconds
- **Memory Delta**: Change in memory usage (bytes and MB)
- **Peak Memory**: Peak memory usage during execution (bytes and MB)
- **Operations**: List of timed operations with durations

### Example Output

```
=== Line Item Creation Performance (100 items) ===
Time: 45.23 ms
Memory: 2.15 MB
Peak Memory: 15.32 MB
Time per item: 0.4523 ms/item

=== Aggregation Validation Performance (100 items) ===
Time: 12.45 ms
Memory: 0.85 MB
Time per validation: 2.075 ms/validation
Time per item: 0.1245 ms/item
```

## Performance Targets Summary

| Operation | Line Items | Target Time | Target Memory |
|-----------|------------|-------------|---------------|
| Creation | 500 | < 1000 ms | < 100 MB |
| Validation | 500 | < 500 ms | < 50 MB |
| Database Save | 500 | < 5000 ms | < 200 MB |
| Database Load | 500 | < 2000 ms | < 100 MB |
| Serialization | 200 | < 1000 ms | < 50 MB |
| Sum Calculation | 200 | < 100 ms | < 10 MB |
| Full Pipeline | 100 | < 10000 ms | < 300 MB |
| Concurrent (10 invoices) | 50 each | < 30000 ms | < 500 MB |
| Very Large Creation | 5000 | < 10000 ms | < 500 MB |
| Very Large Validation | 5000 | < 2000 ms | < 200 MB |

## Interpreting Results

### Good Performance
- Operations complete within target times
- Memory usage is reasonable
- Linear or sub-linear scaling with line item count
- Concurrent processing shows good throughput

### Performance Issues
- Operations exceed target times significantly
- Memory usage grows exponentially
- Poor scaling with line item count
- Concurrent processing shows contention

### Optimization Opportunities
1. **Database**: Optimize queries, add indexes, batch operations
2. **Memory**: Reduce object creation, use generators, clear caches
3. **Serialization**: Use faster serialization libraries, cache results
4. **Validation**: Parallelize validation checks, optimize calculations
5. **Concurrency**: Improve database connection pooling, reduce locking

## Continuous Monitoring

### Integration with CI/CD
- Run benchmarks on every release
- Track performance trends over time
- Alert on performance regressions
- Compare against baseline metrics

### Performance Regression Detection
- Compare current results against baseline
- Flag significant performance degradation (> 20%)
- Track performance trends over time
- Generate performance reports

## Future Enhancements

1. **Automated Reporting**: Generate HTML/PDF performance reports
2. **Trend Analysis**: Track performance over time
3. **Baseline Comparison**: Compare against historical baselines
4. **Profiling Integration**: Integrate with profiling tools (cProfile, py-spy)
5. **Real PDF Benchmarks**: Test with actual large PDF files
6. **Distributed Testing**: Test performance across multiple machines
7. **Load Testing**: Simulate production load patterns
