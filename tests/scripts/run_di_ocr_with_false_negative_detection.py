"""
DI OCR Test with False Negative Detection

Runs DI OCR extraction tests on specified PDFs, detects false negatives,
and generates a comprehensive report with process flow documentation.

Requirements:
- Azure Document Intelligence credentials configured
- test_di_ocr_extraction_standalone.py available
- false_negatives_detector.py available
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

from test_di_ocr_extraction_standalone import StandaloneDIOCRExtractor
from enhanced_false_negative_detector import detect_false_negatives_and_positives, generate_detection_report
from generate_confusion_matrices import generate_confusion_matrix_report


class DIOCRTesterWithFalseNegativeDetection:
    """Runs DI OCR tests and detects false negatives"""
    
    def __init__(self):
        """Initialize DI OCR extractor"""
        self.di_extractor = StandaloneDIOCRExtractor()
        self.test_results = []
        self.process_steps = []
    
    def log_process_step(self, step: str, description: str, status: str = "INFO"):
        """Log a process step"""
        self.process_steps.append({
            "step": step,
            "description": description,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        })
        print(f"[{status}] {step}: {description}")
    
    async def run_tests_on_pdfs(self, pdf_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Run DI OCR tests on multiple PDFs.
        
        Args:
            pdf_paths: List of paths to PDF files
            
        Returns:
            List of test results for each PDF
        """
        self.log_process_step("INITIALIZATION", "Initializing DI OCR extractor", "INFO")
        
        all_results = []
        
        for pdf_path in pdf_paths:
            pdf_name = os.path.basename(pdf_path)
            self.log_process_step("TEST_START", f"Starting test for {pdf_name}", "INFO")
            
            try:
                # Run DI OCR extraction
                self.log_process_step("EXTRACTION", f"Running DI OCR extraction for {pdf_name}", "INFO")
                result = await self.di_extractor.extract_from_pdf(pdf_path)
                result["pdf_path"] = pdf_path
                result["pdf_name"] = pdf_name
                all_results.append(result)
                self.log_process_step("EXTRACTION", f"DI OCR extraction completed for {pdf_name}", "SUCCESS")
                
            except Exception as e:
                self.log_process_step("EXTRACTION", f"DI OCR extraction failed for {pdf_name}: {e}", "ERROR")
                all_results.append({
                    "pdf_path": pdf_path,
                    "pdf_name": pdf_name,
                    "error": str(e),
                    "extracted_fields": {},
                    "canonical_fields_coverage": {}
                })
        
        return all_results
    
    def create_combined_dataframe(self, all_results: List[Dict[str, Any]], false_negatives_df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Create a combined DataFrame with extraction results and false negative detection.
        
        Args:
            all_results: List of test results for each PDF
            false_negatives_df: DataFrame with false negatives (optional)
            
        Returns:
            Combined DataFrame with false_negative boolean column
        """
        rows = []
        
        for result in all_results:
            if "error" in result:
                continue
            
            pdf_name = result["pdf_name"]
            extracted_fields = result.get("extracted_fields", {})
            
            # Create a set of false negative field names for this PDF
            fn_fields = set()
            if false_negatives_df is not None and len(false_negatives_df) > 0:
                pdf_fns = false_negatives_df[false_negatives_df["pdf_name"] == pdf_name]
                fn_fields = set(pdf_fns["field_name"].unique())
            
            for field_name, field_data in extracted_fields.items():
                # Skip line_items - handled separately with detailed structure
                if field_name == "line_items":
                    # Add line items as separate rows
                    line_items_value = field_data.get("value", [])
                    if isinstance(line_items_value, list):
                        for item in line_items_value:
                            if isinstance(item, dict):
                                rows.append({
                                    "pdf_name": pdf_name,
                                    "field_name": f"line_item_{item.get('line_number', 'unknown')}",
                                    "field_category": "line_item",
                                    "extracted": True,
                                    "value": f"Line {item.get('line_number')}: {item.get('description', '')[:50]}",
                                    "confidence": item.get("confidence"),
                                    "confidence_category": self._categorize_confidence(item.get("confidence")),
                                    "di_field_sources": ", ".join(field_data.get("di_field_sources", [])) if field_data.get("di_field_sources") else None,
                                    "false_negative": False,  # Line items handled separately
                                    "value_type": "LineItem",
                                    "line_number": item.get("line_number"),
                                    "line_item_amount": item.get("amount"),
                                    "line_item_quantity": item.get("quantity"),
                                    "line_item_unit_price": item.get("unit_price")
                                })
                    continue
                
                # Higher-level invoice fields
                is_false_negative = field_name in fn_fields
                
                rows.append({
                    "pdf_name": pdf_name,
                    "field_name": field_name,
                    "field_category": "invoice_field",
                    "extracted": field_data.get("extracted", False),
                    "value": str(field_data.get("value", ""))[:100] if field_data.get("value") else None,
                    "confidence": field_data.get("confidence"),
                    "confidence_category": field_data.get("confidence_category", "none"),
                    "di_field_sources": ", ".join(field_data.get("di_field_sources", [])) if field_data.get("di_field_sources") else None,
                    "false_negative": is_false_negative,
                    "value_type": type(field_data.get("value")).__name__ if field_data.get("value") is not None else "NoneType"
                })
        
        return pd.DataFrame(rows)
    
    def _categorize_confidence(self, confidence: float) -> str:
        """Categorize confidence score"""
        if confidence is None:
            return "none"
        if confidence >= 0.75:
            return "high"
        elif confidence >= 0.50:
            return "medium"
        else:
            return "low"
    
    def generate_comprehensive_report(self, all_results: List[Dict[str, Any]], false_negatives_df: pd.DataFrame = None, output_path: str = None) -> str:
        """
        Generate a comprehensive report with process flow and false negative analysis.
        
        Args:
            all_results: List of test results for each PDF
            false_negatives_df: DataFrame with false negatives (optional)
            output_path: Optional path to save report
            
        Returns:
            Report text
        """
        report = []
        report.append("# DI OCR Extraction Test Report with False Negative Detection")
        report.append("")
        report.append(f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        report.append(f"**PDFs Tested:** {len(all_results)}")
        report.append("")
        report.append("---")
        report.append("")
        
        # Process Flow Section
        report.append("## Process Flow")
        report.append("")
        report.append("This test executes the following steps in the end-to-end extraction process:")
        report.append("")
        report.append("### 1. Preprocessing")
        report.append("- **Step:** PDF file loading and validation")
        report.append("- **Description:** Load PDF file from disk, validate file format and size")
        report.append("- **Status:** ✅ Executed in test")
        report.append("")
        
        report.append("### 2. Document Intelligence OCR")
        report.append("- **Step:** Azure Document Intelligence API call")
        report.append("- **Description:** Send PDF to Azure DI service for OCR and field extraction")
        report.append("- **Status:** ✅ Executed in test (real Azure DI API)")
        report.append("- **Output:** Raw DI analysis result with fields and confidence scores")
        report.append("")
        
        report.append("### 3. Field Extraction")
        report.append("- **Step:** Map DI fields to canonical schema")
        report.append("- **Description:** Extract fields from DI result using FieldExtractor")
        report.append("- **Status:** ✅ Executed in test")
        report.append("- **Output:** Invoice object with canonical fields populated")
        report.append("- **Includes:** Higher-level invoice fields AND line items (new table structure)")
        report.append("")
        
        report.append("### 4. Confidence Calculation")
        report.append("- **Step:** Calculate field-level and overall confidence")
        report.append("- **Description:** Analyze confidence scores from DI, categorize as high/medium/low")
        report.append("- **Status:** ✅ Executed in test")
        report.append("- **Output:** Confidence scores and categories for each field")
        report.append("")
        
        report.append("### 5. Extraction Detection")
        report.append("- **Step:** Determine if fields are extracted")
        report.append("- **Description:** Check if field has non-empty value based on type")
        report.append("- **Status:** ✅ Executed in test")
        report.append("- **Output:** Boolean flag for each field indicating extraction status")
        report.append("")
        
        report.append("### 6. False Negative Detection")
        report.append("- **Step:** Identify potential false negatives")
        report.append("- **Description:** Find fields marked as not extracted but have values")
        report.append("- **Status:** ✅ Executed in test")
        report.append("- **Output:** List of potential false negatives with analysis")
        report.append("")
        
        report.append("### Steps NOT Executed in This Test")
        report.append("- ❌ **LLM Fallback:** Not executed (DI OCR only test)")
        report.append("- ❌ **Multimodal LLM:** Not executed (DI OCR only test)")
        report.append("- ❌ **Database Persistence:** Not executed (standalone test)")
        report.append("- ❌ **Validation:** Not executed (standalone test)")
        report.append("- ❌ **HITL Review:** Not executed (standalone test)")
        report.append("")
        report.append("---")
        report.append("")
        
        # Executive Summary
        report.append("## Executive Summary")
        report.append("")
        
        total_fields = 0
        total_extracted = 0
        total_false_negatives = 0
        
        for result in all_results:
            if "error" in result:
                continue
            coverage = result.get("canonical_fields_coverage", {})
            total_fields += coverage.get("total", 0)
            total_extracted += coverage.get("extracted", 0)
        
        if false_negatives_df is not None and len(false_negatives_df) > 0:
            total_false_negatives = len(false_negatives_df)
        
        report.append(f"- **Total PDFs Tested:** {len(all_results)}")
        report.append(f"- **Total Fields Available:** {total_fields}")
        report.append(f"- **Total Fields Extracted:** {total_extracted}")
        report.append(f"- **Overall Extraction Rate:** {(total_extracted / total_fields * 100) if total_fields > 0 else 0:.1f}%")
        report.append(f"- **False Negatives Detected:** {total_false_negatives}")
        report.append("")
        report.append("---")
        report.append("")
        
        # Results by PDF
        report.append("## Results by PDF")
        report.append("")
        
        for result in all_results:
            pdf_name = result["pdf_name"]
            report.append(f"### {pdf_name}")
            report.append("")
            
            if "error" in result:
                report.append(f"- **Status:** ❌ FAILED")
                report.append(f"- **Error:** {result['error']}")
                report.append("")
                continue
            
            coverage = result.get("canonical_fields_coverage", {})
            report.append(f"- **Extraction Rate:** {coverage.get('extraction_rate', 0):.1f}%")
            report.append(f"- **Fields Extracted:** {coverage.get('extracted', 0)}/{coverage.get('total', 0)}")
            report.append(f"- **High Confidence (>=0.75):** {coverage.get('high_confidence', 0)}")
            report.append(f"- **Medium Confidence (0.50-0.75):** {coverage.get('medium_confidence', 0)}")
            report.append(f"- **Low Confidence (<0.50):** {coverage.get('low_confidence', 0)}")
            report.append(f"- **Line Items:** {len(result.get('extracted_fields', {}).get('line_items', {}).get('value', []))}")
            report.append(f"- **Overall Confidence:** {result.get('extraction_confidence', 0):.3f}")
            report.append(f"- **DI Duration:** {result.get('di_duration_seconds', 0):.2f} seconds")
            
            # False negatives for this PDF
            if false_negatives_df is not None and len(false_negatives_df) > 0:
                pdf_fns = false_negatives_df[false_negatives_df["pdf_name"] == pdf_name]
                if len(pdf_fns) > 0:
                    report.append(f"- **False Negatives:** {len(pdf_fns)}")
                    report.append("")
                    report.append("  False negative fields:")
                    for _, fn_row in pdf_fns.iterrows():
                        value_preview = str(fn_row.get('di_value', ''))[:50] if pd.notna(fn_row.get('di_value')) else 'N/A'
                        conf = fn_row.get('di_confidence', 'N/A')
                        report.append(f"    - `{fn_row['field_name']}`: {value_preview} (confidence: {conf})")
            
            report.append("")
            report.append("---")
            report.append("")
        
        # False Negatives Analysis
        if false_negatives_df is not None and len(false_negatives_df) > 0:
            report.append("## False Negatives Analysis")
            report.append("")
            report.append(f"**Total False Negatives:** {len(false_negatives_df)}")
            report.append("")
            
            # By field
            report.append("### False Negatives by Field Name")
            report.append("")
            by_field = false_negatives_df.groupby('field_name').size().sort_values(ascending=False)
            report.append("| Field Name | Occurrences |")
            report.append("|------------|-------------|")
            for field, count in by_field.items():
                report.append(f"| `{field}` | {count} |")
            report.append("")
            
            # By PDF
            report.append("### False Negatives by PDF")
            report.append("")
            by_pdf = false_negatives_df.groupby('pdf_name').size().sort_values(ascending=False)
            report.append("| PDF Name | False Negatives |")
            report.append("|----------|----------------|")
            for pdf, count in by_pdf.items():
                report.append(f"| `{pdf}` | {count} |")
            report.append("")
            
            report.append("---")
            report.append("")
        
        # Line Items Summary
        report.append("## Line Items Summary")
        report.append("")
        report.append("Line items are extracted and structured for the new `line_items` table format.")
        report.append("")
        report.append("### Line Items Structure")
        report.append("")
        report.append("Each line item includes:")
        report.append("- `line_number`: Sequential line number")
        report.append("- `description`: Item description")
        report.append("- `quantity`: Quantity (if available)")
        report.append("- `unit_price`: Unit price (if available)")
        report.append("- `amount`: Line item total amount")
        report.append("- `tax_amount`: Tax amount for this line")
        report.append("- `gst_amount`: GST amount (if applicable)")
        report.append("- `pst_amount`: PST amount (if applicable)")
        report.append("- `qst_amount`: QST amount (if applicable)")
        report.append("- `confidence`: Extraction confidence score")
        report.append("")
        
        total_line_items = sum(
            len(result.get("extracted_fields", {}).get("line_items", {}).get("value", []))
            for result in all_results
            if "error" not in result
        )
        report.append(f"**Total Line Items Extracted:** {total_line_items}")
        report.append("")
        
        # Process Steps Log
        report.append("## Process Steps Log")
        report.append("")
        report.append("| Step | Description | Status | Timestamp |")
        report.append("|------|-------------|--------|-----------|")
        for step in self.process_steps:
            status_icon = "✅" if step["status"] == "SUCCESS" else "❌" if step["status"] == "ERROR" else "ℹ️"
            report.append(f"| {step['step']} | {step['description']} | {status_icon} {step['status']} | {step['timestamp']} |")
        report.append("")
        
        report.append("---")
        report.append("")
        report.append("## Confusion Matrix Analysis")
        report.append("")
        report.append("Detailed confusion matrix analysis has been generated. See:")
        report.append("- `confusion_matrix_per_pdf.csv` - Per-PDF confusion matrices")
        report.append("- `confusion_matrix_per_field.csv` - Per-field confusion matrices")
        report.append("- `confusion_matrix_overall.csv` - Overall confusion matrix")
        report.append("- `confusion_matrix_report.md` - Comprehensive confusion matrix report")
        report.append("")
        report.append("### Key Metrics")
        report.append("")
        report.append("**Confusion Matrix Categories:**")
        report.append("- **True Positive (TP):** Field correctly extracted with confidence")
        report.append("- **False Positive (FP):** Field extracted but with low/no confidence")
        report.append("- **False Negative (FN):** Field should be extracted (has confidence/DI source) but isn't")
        report.append("- **True Negative (TN):** Field correctly not extracted (no value, no confidence)")
        report.append("")
        report.append("**Performance Metrics:**")
        report.append("- **Precision:** TP / (TP + FP) - Of all extracted fields, how many are correct?")
        report.append("- **Recall:** TP / (TP + FN) - Of all extractable fields, how many were found?")
        report.append("- **F1 Score:** Harmonic mean of precision and recall")
        report.append("- **Accuracy:** (TP + TN) / Total - Overall correctness")
        report.append("")
        report.append("---")
        report.append("")
        report.append("**Report End**")
        
        report_text = "\n".join(report)
        
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report_text)
            print(f"\nReport saved to: {output_path}")
        
        return report_text


async def main():
    """Main test execution"""
    # PDF files to test
    pdf_files = [
        "data/sample_invoices/Raw/Raw_Basic/ACC012 4202092525.pdf",
        "data/sample_invoices/Raw/Raw_Basic/ANA005 90443097.pdf",
        "data/sample_invoices/Raw/Raw_Basic/HYD001 5160530790NOV2025.pdf",
        "data/sample_invoices/Raw/Raw_Basic/TEL006 4222600.pdf",
        "data/sample_invoices/Raw/Raw_Basic/ENB001 166574659065NOV2025.pdf"
    ]
    
    # Verify all PDFs exist
    missing_pdfs = [pdf for pdf in pdf_files if not os.path.exists(pdf)]
    if missing_pdfs:
        print(f"Error: Missing PDF files:")
        for pdf in missing_pdfs:
            print(f"  - {pdf}")
        return
    
    print(f"\n{'='*100}")
    print(f"DI OCR EXTRACTION TEST WITH FALSE NEGATIVE DETECTION")
    print(f"{'='*100}")
    print(f"Testing {len(pdf_files)} PDFs")
    print(f"PDFs: {', '.join([os.path.basename(pdf) for pdf in pdf_files])}")
    print(f"{'='*100}\n")
    
    try:
        # Initialize tester
        tester = DIOCRTesterWithFalseNegativeDetection()
        
        # Run tests
        all_results = await tester.run_tests_on_pdfs(pdf_files)
        
        # Create field-by-field DataFrame
        print(f"\n{'='*100}")
        print("CREATING FIELD-BY-FIELD DATAFRAME")
        print(f"{'='*100}\n")
        
        field_rows = []
        for result in all_results:
            if "error" in result:
                continue
            pdf_name = result["pdf_name"]
            extracted_fields = result.get("extracted_fields", {})
            for field_name, field_data in extracted_fields.items():
                field_rows.append({
                    "pdf_name": pdf_name,
                    "field_name": field_name,
                    "extracted": field_data.get("extracted", False),
                    "value": field_data.get("value"),
                    "confidence": field_data.get("confidence"),
                    "confidence_category": field_data.get("confidence_category", "none"),
                    "di_field_sources": ", ".join(field_data.get("di_field_sources", [])) if field_data.get("di_field_sources") else None
                })
        
        field_df = pd.DataFrame(field_rows)
        temp_csv = "di_ocr_field_details_temp.csv"
        field_df.to_csv(temp_csv, index=False)
        print(f"Temporary field details saved to: {temp_csv}")
        
        # Detect false negatives and false positives
        print(f"\n{'='*100}")
        print("DETECTING FALSE NEGATIVES AND FALSE POSITIVES")
        print(f"{'='*100}\n")
        
        false_negatives_df, false_positives_df, potential_false_negatives_df = detect_false_negatives_and_positives(temp_csv)
        
        if false_negatives_df is None:
            false_negatives_df = pd.DataFrame()
        if false_positives_df is None:
            false_positives_df = pd.DataFrame()
        if potential_false_negatives_df is None:
            potential_false_negatives_df = pd.DataFrame()
        
        print(f"Detection Results:")
        print(f"  - False Negatives: {len(false_negatives_df)}")
        print(f"  - Potential False Negatives: {len(potential_false_negatives_df)}")
        print(f"  - False Positives: {len(false_positives_df)}")
        
        # Combine all false negatives (actual + potential) for the combined DataFrame
        all_false_negatives_df = pd.concat([false_negatives_df, potential_false_negatives_df], ignore_index=True) if len(false_negatives_df) > 0 or len(potential_false_negatives_df) > 0 else pd.DataFrame()
        
        # Generate detection report
        generate_detection_report(false_negatives_df, false_positives_df, potential_false_negatives_df, output_path='false_negatives_report.csv')
        
        # Create combined DataFrame with false negative boolean
        print(f"\n{'='*100}")
        print("CREATING COMBINED DATAFRAME WITH FALSE NEGATIVE FLAG")
        print(f"{'='*100}\n")
        
        combined_df = tester.create_combined_dataframe(all_results, all_false_negatives_df)
        output_csv = "di_ocr_extraction_with_false_negatives.csv"
        combined_df.to_csv(output_csv, index=False)
        print(f"Combined results saved to: {output_csv}")
        print(f"Total rows: {len(combined_df)}")
        print(f"False negatives: {combined_df['false_negative'].sum()}")
        
        # Generate confusion matrices
        print(f"\n{'='*100}")
        print("GENERATING CONFUSION MATRICES")
        print(f"{'='*100}\n")
        
        try:
            from generate_confusion_matrices import generate_confusion_matrix_report
            generate_confusion_matrix_report(output_csv)
        except Exception as e:
            print(f"Warning: Could not generate confusion matrices: {e}")
        
        # Generate comprehensive report
        print(f"\n{'='*100}")
        print("GENERATING COMPREHENSIVE REPORT")
        print(f"{'='*100}\n")
        
        report_path = "di_ocr_test_report_with_false_negatives.md"
        # Combine all false negatives for the report
        report_false_negatives_df = pd.concat([false_negatives_df, potential_false_negatives_df], ignore_index=True) if len(false_negatives_df) > 0 or len(potential_false_negatives_df) > 0 else pd.DataFrame()
        report = tester.generate_comprehensive_report(all_results, report_false_negatives_df, output_path=report_path)
        
        # Clean up temporary file
        if os.path.exists(temp_csv):
            os.remove(temp_csv)
        
        print(f"\n{'='*100}")
        print("TEST COMPLETE")
        print(f"{'='*100}")
        print(f"Output files:")
        print(f"  - {output_csv}")
        print(f"  - {report_path}")
        print(f"  - false_negatives_report.csv (comprehensive detection report)")
        print(f"  - confusion_matrix_per_pdf.csv")
        print(f"  - confusion_matrix_per_field.csv")
        print(f"  - confusion_matrix_overall.csv")
        print(f"  - confusion_matrix_report.md")
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
