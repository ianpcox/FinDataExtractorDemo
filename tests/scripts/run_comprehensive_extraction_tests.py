"""
Comprehensive Extraction Test Suite

Runs DI OCR, Base LLM, and Multimodal LLM extraction tests against multiple PDFs
and generates consolidated reports and CSV outputs.

Requirements:
- Azure OpenAI credentials configured
- Azure Document Intelligence credentials configured
- PyMuPDF installed for multimodal tests
"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
import pandas as pd
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import standalone test modules
from test_di_ocr_extraction_standalone import StandaloneDIOCRExtractor
from test_llm_extraction_standalone import StandaloneLLMExtractor
from test_multimodal_llm_extraction_standalone import StandaloneMultimodalExtractor


class ComprehensiveTestRunner:
    """Runs comprehensive extraction tests across multiple PDFs"""
    
    def __init__(self):
        """Initialize test runners"""
        self.di_extractor = StandaloneDIOCRExtractor()
        self.llm_extractor = StandaloneLLMExtractor()
        self.multimodal_extractor = StandaloneMultimodalExtractor()
        
        self.test_results = []
    
    async def run_tests_on_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Run all three extraction methods on a single PDF.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with results from all three extraction methods
        """
        pdf_name = os.path.basename(pdf_path)
        print(f"\n{'='*100}")
        print(f"TESTING: {pdf_name}")
        print(f"{'='*100}\n")
        
        results = {
            "pdf_path": pdf_path,
            "pdf_name": pdf_name,
            "timestamp": datetime.utcnow().isoformat(),
            "di_ocr": None,
            "base_llm": None,
            "multimodal_llm": None
        }
        
        # Test 1: DI OCR Only
        print(f"\n{'-'*100}")
        print(f"TEST 1: DI OCR EXTRACTION")
        print(f"{'-'*100}\n")
        try:
            di_results = await self.di_extractor.extract_from_pdf(pdf_path)
            results["di_ocr"] = di_results
            print(f"[OK] DI OCR completed: {di_results.get('canonical_fields_coverage', {}).get('extraction_rate', 0):.1f}% extraction rate")
        except Exception as e:
            print(f"[FAIL] DI OCR failed: {e}")
            results["di_ocr"] = {"error": str(e)}
        
        # Test 2: Base LLM (Text-based)
        print(f"\n{'-'*100}")
        print(f"TEST 2: BASE LLM EXTRACTION")
        print(f"{'-'*100}\n")
        try:
            llm_results = await self.llm_extractor.extract_from_pdf(pdf_path)
            results["base_llm"] = llm_results
            print(f"[OK] Base LLM completed: {llm_results.get('canonical_fields_coverage', {}).get('extraction_rate', 0):.1f}% extraction rate")
        except Exception as e:
            print(f"[FAIL] Base LLM failed: {e}")
            results["base_llm"] = {"error": str(e)}
        
        # Test 3: Multimodal LLM
        print(f"\n{'-'*100}")
        print(f"TEST 3: MULTIMODAL LLM EXTRACTION")
        print(f"{'-'*100}\n")
        try:
            multimodal_results = await self.multimodal_extractor.extract_from_pdf(pdf_path)
            results["multimodal_llm"] = multimodal_results
            print(f"[OK] Multimodal LLM completed: {multimodal_results.get('canonical_fields_coverage', {}).get('extraction_rate', 0):.1f}% extraction rate")
        except Exception as e:
            print(f"[FAIL] Multimodal LLM failed: {e}")
            results["multimodal_llm"] = {"error": str(e)}
        
        return results
    
    def generate_comparison_dataframe(self, all_results: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Generate a comparison DataFrame showing extraction results across all PDFs and methods.
        
        Args:
            all_results: List of test results for each PDF
            
        Returns:
            DataFrame with comparison data
        """
        rows = []
        
        for result in all_results:
            pdf_name = result["pdf_name"]
            
            # DI OCR results
            if result["di_ocr"] and "error" not in result["di_ocr"]:
                di_coverage = result["di_ocr"].get("canonical_fields_coverage", {})
                rows.append({
                    "pdf_name": pdf_name,
                    "extraction_method": "DI OCR",
                    "total_fields": di_coverage.get("total", 0),
                    "extracted": di_coverage.get("extracted", 0),
                    "missing": di_coverage.get("missing", 0),
                    "extraction_rate": di_coverage.get("extraction_rate", 0),
                    "high_confidence": di_coverage.get("high_confidence", 0),
                    "medium_confidence": di_coverage.get("medium_confidence", 0),
                    "low_confidence": di_coverage.get("low_confidence", 0),
                    "overall_confidence": result["di_ocr"].get("extraction_confidence", 0),
                    "duration_seconds": result["di_ocr"].get("di_duration_seconds", 0),
                    "status": "success"
                })
            else:
                rows.append({
                    "pdf_name": pdf_name,
                    "extraction_method": "DI OCR",
                    "total_fields": 0,
                    "extracted": 0,
                    "missing": 0,
                    "extraction_rate": 0,
                    "high_confidence": 0,
                    "medium_confidence": 0,
                    "low_confidence": 0,
                    "overall_confidence": 0,
                    "duration_seconds": 0,
                    "status": "failed"
                })
            
            # Base LLM results
            if result["base_llm"] and "error" not in result["base_llm"]:
                llm_coverage = result["base_llm"].get("canonical_fields_coverage", {})
                rows.append({
                    "pdf_name": pdf_name,
                    "extraction_method": "Base LLM",
                    "total_fields": llm_coverage.get("total", 0),
                    "extracted": llm_coverage.get("extracted", 0),
                    "missing": llm_coverage.get("missing", 0),
                    "extraction_rate": llm_coverage.get("extraction_rate", 0),
                    "high_confidence": 0,  # LLM doesn't track this separately
                    "medium_confidence": 0,
                    "low_confidence": 0,
                    "overall_confidence": result["base_llm"].get("extraction_confidence", 0),
                    "duration_seconds": 0,  # Not tracked in LLM test
                    "status": "success"
                })
            else:
                rows.append({
                    "pdf_name": pdf_name,
                    "extraction_method": "Base LLM",
                    "total_fields": 0,
                    "extracted": 0,
                    "missing": 0,
                    "extraction_rate": 0,
                    "high_confidence": 0,
                    "medium_confidence": 0,
                    "low_confidence": 0,
                    "overall_confidence": 0,
                    "duration_seconds": 0,
                    "status": "failed"
                })
            
            # Multimodal LLM results
            if result["multimodal_llm"] and "error" not in result["multimodal_llm"]:
                multimodal_coverage = result["multimodal_llm"].get("canonical_fields_coverage", {})
                rows.append({
                    "pdf_name": pdf_name,
                    "extraction_method": "Multimodal LLM",
                    "total_fields": multimodal_coverage.get("total", 0),
                    "extracted": multimodal_coverage.get("extracted", 0),
                    "missing": multimodal_coverage.get("missing", 0),
                    "extraction_rate": multimodal_coverage.get("extraction_rate", 0),
                    "high_confidence": 0,  # Multimodal doesn't track this separately
                    "medium_confidence": 0,
                    "low_confidence": 0,
                    "overall_confidence": result["multimodal_llm"].get("extraction_confidence", 0),
                    "duration_seconds": 0,  # Not tracked in multimodal test
                    "status": "success"
                })
            else:
                rows.append({
                    "pdf_name": pdf_name,
                    "extraction_method": "Multimodal LLM",
                    "total_fields": 0,
                    "extracted": 0,
                    "missing": 0,
                    "extraction_rate": 0,
                    "high_confidence": 0,
                    "medium_confidence": 0,
                    "low_confidence": 0,
                    "overall_confidence": 0,
                    "duration_seconds": 0,
                    "status": "failed"
                })
        
        return pd.DataFrame(rows)
    
    def generate_field_by_field_dataframe(self, all_results: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Generate a detailed DataFrame showing field-by-field extraction across all PDFs and methods.
        
        Args:
            all_results: List of test results for each PDF
            
        Returns:
            DataFrame with field-by-field data
        """
        from src.extraction.extraction_service import CANONICAL_FIELDS
        
        rows = []
        
        for result in all_results:
            pdf_name = result["pdf_name"]
            
            # Process each canonical field
            for field_name in sorted(CANONICAL_FIELDS):
                row = {
                    "pdf_name": pdf_name,
                    "field_name": field_name
                }
                
                # DI OCR
                if result["di_ocr"] and "error" not in result["di_ocr"]:
                    di_field = result["di_ocr"]["extracted_fields"].get(field_name, {})
                    row["di_extracted"] = di_field.get("extracted", False)
                    row["di_value"] = str(di_field.get("value", ""))[:50] if di_field.get("value") else None
                    row["di_confidence"] = di_field.get("confidence")
                else:
                    row["di_extracted"] = False
                    row["di_value"] = None
                    row["di_confidence"] = None
                
                # Base LLM
                if result["base_llm"] and "error" not in result["base_llm"]:
                    llm_field = result["base_llm"]["extracted_fields"].get(field_name, {})
                    row["llm_extracted"] = llm_field.get("extracted", False)
                    row["llm_value"] = str(llm_field.get("value", ""))[:50] if llm_field.get("value") else None
                    row["llm_confidence"] = llm_field.get("confidence")
                    row["llm_source"] = "LLM" if llm_field.get("extracted_by_llm") else ("DI" if llm_field.get("extracted_by_di") else None)
                else:
                    row["llm_extracted"] = False
                    row["llm_value"] = None
                    row["llm_confidence"] = None
                    row["llm_source"] = None
                
                # Multimodal LLM
                if result["multimodal_llm"] and "error" not in result["multimodal_llm"]:
                    multimodal_field = result["multimodal_llm"]["extracted_fields"].get(field_name, {})
                    row["multimodal_extracted"] = multimodal_field.get("extracted", False)
                    row["multimodal_value"] = str(multimodal_field.get("value", ""))[:50] if multimodal_field.get("value") else None
                    row["multimodal_confidence"] = multimodal_field.get("confidence")
                else:
                    row["multimodal_extracted"] = False
                    row["multimodal_value"] = None
                    row["multimodal_confidence"] = None
                
                # Best extraction (any method that extracted it)
                row["best_extracted"] = row["di_extracted"] or row["llm_extracted"] or row["multimodal_extracted"]
                
                rows.append(row)
        
        return pd.DataFrame(rows)
    
    def generate_test_report(self, all_results: List[Dict[str, Any]], output_path: str = None):
        """
        Generate a comprehensive test report.
        
        Args:
            all_results: List of test results for each PDF
            output_path: Optional path to save report
        """
        report = []
        report.append("# Comprehensive Extraction Test Report")
        report.append("")
        report.append(f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        report.append(f"**PDFs Tested:** {len(all_results)}")
        report.append("")
        report.append("---")
        report.append("")
        
        # Summary table
        report.append("## Executive Summary")
        report.append("")
        report.append("| PDF | DI OCR | Base LLM | Multimodal LLM | Best Overall |")
        report.append("|-----|--------|----------|----------------|--------------|")
        
        for result in all_results:
            pdf_name = result["pdf_name"]
            
            # Get extraction rates
            di_rate = 0
            if result["di_ocr"] and "error" not in result["di_ocr"]:
                di_rate = result["di_ocr"].get("canonical_fields_coverage", {}).get("extraction_rate", 0)
            
            llm_rate = 0
            if result["base_llm"] and "error" not in result["base_llm"]:
                llm_rate = result["base_llm"].get("canonical_fields_coverage", {}).get("extraction_rate", 0)
            
            multimodal_rate = 0
            if result["multimodal_llm"] and "error" not in result["multimodal_llm"]:
                multimodal_rate = result["multimodal_llm"].get("canonical_fields_coverage", {}).get("extraction_rate", 0)
            
            best_rate = max(di_rate, llm_rate, multimodal_rate)
            
            di_status = f"{di_rate:.1f}%" if di_rate > 0 else "FAIL"
            llm_status = f"{llm_rate:.1f}%" if llm_rate > 0 else "FAIL"
            multimodal_status = f"{multimodal_rate:.1f}%" if multimodal_rate > 0 else "FAIL"
            best_status = f"{best_rate:.1f}%" if best_rate > 0 else "FAIL"
            
            report.append(f"| {pdf_name} | {di_status} | {llm_status} | {multimodal_status} | {best_status} |")
        
        report.append("")
        
        # Detailed results for each PDF
        for result in all_results:
            pdf_name = result["pdf_name"]
            report.append(f"## {pdf_name}")
            report.append("")
            
            # DI OCR Results
            if result["di_ocr"] and "error" not in result["di_ocr"]:
                di_coverage = result["di_ocr"].get("canonical_fields_coverage", {})
                report.append("### DI OCR Results")
                report.append(f"- **Extraction Rate:** {di_coverage.get('extraction_rate', 0):.1f}%")
                report.append(f"- **Fields Extracted:** {di_coverage.get('extracted', 0)}/{di_coverage.get('total', 0)}")
                report.append(f"- **Overall Confidence:** {result['di_ocr'].get('extraction_confidence', 0):.3f}")
                report.append(f"- **Duration:** {result['di_ocr'].get('di_duration_seconds', 0):.2f} seconds")
                report.append("")
            else:
                report.append("### DI OCR Results")
                report.append("- **Status:** FAILED")
                if result["di_ocr"]:
                    report.append(f"- **Error:** {result['di_ocr'].get('error', 'Unknown error')}")
                report.append("")
            
            # Base LLM Results
            if result["base_llm"] and "error" not in result["base_llm"]:
                llm_coverage = result["base_llm"].get("canonical_fields_coverage", {})
                report.append("### Base LLM Results")
                report.append(f"- **Extraction Rate:** {llm_coverage.get('extraction_rate', 0):.1f}%")
                report.append(f"- **Fields Extracted:** {llm_coverage.get('extracted', 0)}/{llm_coverage.get('total', 0)}")
                report.append(f"- **LLM Improved Fields:** {llm_coverage.get('llm_extracted', 0)}")
                report.append(f"- **Overall Confidence:** {result['base_llm'].get('extraction_confidence', 0):.3f}")
                report.append(f"- **LLM Success:** {result['base_llm'].get('llm_success', False)}")
                report.append("")
            else:
                report.append("### Base LLM Results")
                report.append("- **Status:** FAILED")
                if result["base_llm"]:
                    report.append(f"- **Error:** {result['base_llm'].get('error', 'Unknown error')}")
                report.append("")
            
            # Multimodal LLM Results
            if result["multimodal_llm"] and "error" not in result["multimodal_llm"]:
                multimodal_coverage = result["multimodal_llm"].get("canonical_fields_coverage", {})
                report.append("### Multimodal LLM Results")
                report.append(f"- **Extraction Rate:** {multimodal_coverage.get('extraction_rate', 0):.1f}%")
                report.append(f"- **Fields Extracted:** {multimodal_coverage.get('extracted', 0)}/{multimodal_coverage.get('total', 0)}")
                report.append(f"- **Overall Confidence:** {result['multimodal_llm'].get('extraction_confidence', 0):.3f}")
                report.append(f"- **Multimodal LLM Used:** {result['multimodal_llm'].get('multimodal_llm_triggered', False)}")
                report.append(f"- **Multimodal LLM Success:** {result['multimodal_llm'].get('multimodal_llm_success', False)}")
                report.append("")
            else:
                report.append("### Multimodal LLM Results")
                report.append("- **Status:** FAILED")
                if result["multimodal_llm"]:
                    report.append(f"- **Error:** {result['multimodal_llm'].get('error', 'Unknown error')}")
                report.append("")
            
            report.append("---")
            report.append("")
        
        # Method comparison
        report.append("## Method Comparison")
        report.append("")
        report.append("### Average Extraction Rates by Method")
        report.append("")
        
        di_rates = []
        llm_rates = []
        multimodal_rates = []
        
        for result in all_results:
            if result["di_ocr"] and "error" not in result["di_ocr"]:
                di_rates.append(result["di_ocr"].get("canonical_fields_coverage", {}).get("extraction_rate", 0))
            if result["base_llm"] and "error" not in result["base_llm"]:
                llm_rates.append(result["base_llm"].get("canonical_fields_coverage", {}).get("extraction_rate", 0))
            if result["multimodal_llm"] and "error" not in result["multimodal_llm"]:
                multimodal_rates.append(result["multimodal_llm"].get("canonical_fields_coverage", {}).get("extraction_rate", 0))
        
        if di_rates:
            avg_di = sum(di_rates) / len(di_rates)
            report.append(f"- **DI OCR Average:** {avg_di:.1f}% ({len(di_rates)} PDFs)")
        if llm_rates:
            avg_llm = sum(llm_rates) / len(llm_rates)
            report.append(f"- **Base LLM Average:** {avg_llm:.1f}% ({len(llm_rates)} PDFs)")
        if multimodal_rates:
            avg_multimodal = sum(multimodal_rates) / len(multimodal_rates)
            report.append(f"- **Multimodal LLM Average:** {avg_multimodal:.1f}% ({len(multimodal_rates)} PDFs)")
        
        report.append("")
        report.append("---")
        report.append("")
        report.append("**Report End**")
        
        report_text = "\n".join(report)
        
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report_text)
            print(f"\nTest report saved to: {output_path}")
        
        return report_text


async def main():
    """Main test execution"""
    # PDF files to test
    pdf_files = [
        "data/sample_invoices/Raw/Raw_Basic/ANA005 90443097.pdf",
        "data/sample_invoices/Raw/Raw_Basic/HYD001 5160530790NOV2025.pdf",
        "data/sample_invoices/Raw/Raw_Basic/TEL006 4222600.pdf"
    ]
    
    # Verify all PDFs exist
    missing_pdfs = [pdf for pdf in pdf_files if not os.path.exists(pdf)]
    if missing_pdfs:
        print(f"Error: Missing PDF files:")
        for pdf in missing_pdfs:
            print(f"  - {pdf}")
        return
    
    print(f"\n{'='*100}")
    print(f"COMPREHENSIVE EXTRACTION TEST SUITE")
    print(f"{'='*100}")
    print(f"Testing {len(pdf_files)} PDFs with 3 extraction methods")
    print(f"PDFs: {', '.join([os.path.basename(pdf) for pdf in pdf_files])}")
    print(f"{'='*100}\n")
    
    try:
        # Initialize test runner
        runner = ComprehensiveTestRunner()
        
        # Run tests on each PDF
        all_results = []
        for pdf_path in pdf_files:
            result = await runner.run_tests_on_pdf(pdf_path)
            all_results.append(result)
        
        # Generate comparison DataFrame
        print(f"\n{'='*100}")
        print("GENERATING COMPARISON REPORTS")
        print(f"{'='*100}\n")
        
        comparison_df = runner.generate_comparison_dataframe(all_results)
        comparison_csv = "comprehensive_extraction_comparison.csv"
        comparison_df.to_csv(comparison_csv, index=False)
        print(f"Comparison DataFrame saved to: {comparison_csv}")
        print("\nComparison Summary:")
        print(comparison_df.to_string(index=False))
        
        # Generate field-by-field DataFrame
        field_df = runner.generate_field_by_field_dataframe(all_results)
        field_csv = "comprehensive_extraction_field_details.csv"
        field_df.to_csv(field_csv, index=False)
        print(f"\nField-by-field DataFrame saved to: {field_csv}")
        print(f"Total rows: {len(field_df)}")
        
        # Generate test report
        report_path = "comprehensive_extraction_test_report.md"
        report = runner.generate_test_report(all_results, output_path=report_path)
        
        # Print summary statistics
        print(f"\n{'='*100}")
        print("SUMMARY STATISTICS")
        print(f"{'='*100}\n")
        
        for result in all_results:
            pdf_name = result["pdf_name"]
            print(f"\n{pdf_name}:")
            
            if result["di_ocr"] and "error" not in result["di_ocr"]:
                di_rate = result["di_ocr"].get("canonical_fields_coverage", {}).get("extraction_rate", 0)
                print(f"  DI OCR: {di_rate:.1f}%")
            
            if result["base_llm"] and "error" not in result["base_llm"]:
                llm_rate = result["base_llm"].get("canonical_fields_coverage", {}).get("extraction_rate", 0)
                print(f"  Base LLM: {llm_rate:.1f}%")
            
            if result["multimodal_llm"] and "error" not in result["multimodal_llm"]:
                multimodal_rate = result["multimodal_llm"].get("canonical_fields_coverage", {}).get("extraction_rate", 0)
                print(f"  Multimodal LLM: {multimodal_rate:.1f}%")
        
        print(f"\n{'='*100}")
        print("TEST COMPLETE")
        print(f"{'='*100}")
        print(f"Output files:")
        print(f"  - {comparison_csv}")
        print(f"  - {field_csv}")
        print(f"  - {report_path}")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

