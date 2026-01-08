"""
Performance benchmark runner for large invoices.

This script runs performance benchmarks and generates a report.
Can be run standalone or via pytest.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
import json
from datetime import datetime


def run_benchmarks(output_file: str = None):
    """Run performance benchmarks and optionally save results"""
    
    # Run pytest with performance markers
    args = [
        "tests/integration/test_large_invoice_performance.py",
        "-v",
        "-m", "performance",
        "--tb=short",
        "-s",  # Show print statements
    ]
    
    if output_file:
        args.extend(["--json-report", "--json-report-file", output_file])
    
    exit_code = pytest.main(args)
    
    return exit_code


def generate_report(results_file: str = None):
    """Generate a performance report from benchmark results"""
    
    if not results_file or not os.path.exists(results_file):
        print("No results file provided or file not found")
        return
    
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    print("\n" + "="*80)
    print("PERFORMANCE BENCHMARK REPORT")
    print("="*80)
    print(f"Generated: {datetime.now().isoformat()}")
    print()
    
    # Process and display results
    # This would parse pytest-json-report format
    # For now, just indicate report generation
    print("Report generation from JSON results would go here")
    print("(Requires pytest-json-report plugin)")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run performance benchmarks for large invoices")
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for JSON results (requires pytest-json-report)"
    )
    parser.add_argument(
        "--report",
        type=str,
        help="Generate report from JSON results file"
    )
    
    args = parser.parse_args()
    
    if args.report:
        generate_report(args.report)
    else:
        exit_code = run_benchmarks(args.output)
        sys.exit(exit_code)
