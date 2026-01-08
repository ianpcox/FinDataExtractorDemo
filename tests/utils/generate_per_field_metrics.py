"""
Generate comprehensive per-field metrics report from extraction results.

Supports:
- Precision/Recall/F1 per field
- Exact-match accuracy
- Value-tolerant accuracy
- String similarity scores
- Confidence calibration
"""

import sys
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.metrics.field_metrics import FieldMetricsCalculator
from src.metrics.ground_truth_loader import GroundTruthLoader
from src.metrics.document_metrics import DocumentMetricsCalculator, AggregateDocumentMetrics
from src.metrics.metrics_config import get_canonical_field_count, get_all_canonical_fields
from src.metrics.confidence_calibration import ConfidenceCalibrationCalculator
from src.metrics.line_item_metrics import LineItemMetricsCalculator

# Reconfigure stdout for Unicode
sys.stdout.reconfigure(encoding='utf-8')


def load_extraction_results(csv_path: str) -> List[Dict[str, Any]]:
    """Load extraction results from CSV"""
    df = pd.read_csv(csv_path)
    
    results = []
    for _, row in df.iterrows():
        pdf_name = row.get("pdf_name", "unknown")
        
        # Reconstruct extracted_fields structure
        extracted_fields = {}
        for col in df.columns:
            if col in ["pdf_name", "field_name", "extracted", "confidence", "value", "di_field_sources", "confidence_category", "false_negative"]:
                continue
            
            # Try to find field-specific columns
            if col.startswith("value_") or col.startswith("confidence_"):
                continue
        
        # For each row, we need to extract the field information
        field_name = row.get("field_name")
        if field_name:
            extracted_fields[field_name] = {
                "value": row.get("value"),
                "confidence": row.get("confidence"),
                "extracted": row.get("extracted", False),
            }
        
        result = {
            "pdf_name": pdf_name,
            "extracted_fields": extracted_fields,
        }
        results.append(result)
    
    return results


def load_extraction_results_grouped(csv_path: str) -> List[Dict[str, Any]]:
    """Load extraction results grouped by PDF"""
    df = pd.read_csv(csv_path)
    
    # Group by PDF
    pdf_groups = {}
    for _, row in df.iterrows():
        pdf_name = row.get("pdf_name", "unknown")
        field_name = row.get("field_name", "")
        
        if pdf_name not in pdf_groups:
            pdf_groups[pdf_name] = {
                "pdf_name": pdf_name,
                "extracted_fields": {},
            }
        
        value = row.get("value")
        confidence = row.get("confidence")
        extracted = row.get("extracted", False)
        
        # Handle None values
        if pd.isna(value):
            value = None
        if pd.isna(confidence):
            confidence = None
        
        pdf_groups[pdf_name]["extracted_fields"][field_name] = {
            "value": value,
            "confidence": confidence,
            "extracted": extracted,
        }
    
    return list(pdf_groups.values())


def get_all_field_names(csv_path: str) -> List[str]:
    """Get all unique field names from CSV"""
    df = pd.read_csv(csv_path)
    if "field_name" in df.columns:
        return sorted(df["field_name"].unique().tolist())
    return []


def generate_ground_truth_from_extraction(
    extracted_data: List[Dict[str, Any]],
    field_names: List[str],
) -> List[Dict[str, Any]]:
    """
    Generate ground truth format from extraction results.
    
    This is a placeholder - in real usage, you would load actual ground truth.
    For now, we'll use the extraction results as a baseline (not ideal, but
    allows the metrics framework to be tested).
    """
    gt_data = []
    
    for extracted in extracted_data:
        pdf_name = extracted.get("pdf_name", "unknown")
        gt_entry = {"pdf_name": pdf_name}
        
        for field_name in field_names:
            if "extracted_fields" in extracted and field_name in extracted["extracted_fields"]:
                field_data = extracted["extracted_fields"][field_name]
                if isinstance(field_data, dict):
                    value = field_data.get("value")
                    if value is not None:
                        gt_entry[field_name] = value
        
        gt_data.append(gt_entry)
    
    return gt_data


def generate_metrics_report(
    extracted_data: List[Dict[str, Any]],
    ground_truth: List[Dict[str, Any]],
    field_names: List[str],
    output_path: str = "per_field_metrics_report.md",
) -> Dict[str, Any]:
    """Generate comprehensive per-field metrics report"""
    
    calculator = FieldMetricsCalculator(
        numeric_tolerance=0.01,
        numeric_percentage_tolerance=0.001,
        date_tolerance_days=0,
    )
    
    # Calculate field-level metrics
    metrics = calculator.calculate_metrics(extracted_data, ground_truth, field_names)
    
    # Calculate document-level metrics
    # Use canonical field count from canonical field coverage reports as denominator
    canonical_field_count = get_canonical_field_count()
    doc_calculator = DocumentMetricsCalculator(canonical_field_count=canonical_field_count)
    doc_metrics = doc_calculator.calculate_metrics(
        extracted_data, ground_truth, field_names, field_metrics=metrics
    )
    aggregate_metrics = AggregateDocumentMetrics(doc_metrics)
    
    # Calculate confidence calibration metrics
    calibration_calculator = ConfidenceCalibrationCalculator()
    calibration_metrics = calibration_calculator.calculate_calibration(
        extracted_data, ground_truth, field_names
    )
    
    # Calculate line item metrics
    line_item_calculator = LineItemMetricsCalculator()
    # Convert ground truth to dict format
    gt_dict = {gt.get("pdf_name", "unknown"): gt for gt in ground_truth}
    line_item_metrics = line_item_calculator.calculate_metrics(extracted_data, gt_dict)
    
    # Generate report
    report_lines = [
        "# Comprehensive Extraction Metrics Report",
        "",
        "This report provides comprehensive per-field and document-level evaluation metrics for invoice extraction.",
        "",
        "## Summary",
        "",
        f"**Total Canonical Fields:** {canonical_field_count} (from canonical field coverage reports)",
        f"**Fields Evaluated:** {len(field_names)}",
        f"**Total Documents:** {len(extracted_data)}",
        "",
        "### Document-Level Summary",
        "",
        f"- **Mean Extraction Rate:** {aggregate_metrics.mean_extraction_rate:.1%} (fields extracted / {canonical_field_count} canonical fields)",
        f"- **Median Extraction Rate:** {aggregate_metrics.median_extraction_rate:.1%}",
        f"- **Mean Document Accuracy:** {aggregate_metrics.mean_accuracy:.3f}",
        f"- **Mean Document F1 Score:** {aggregate_metrics.mean_f1:.3f}",
        f"- **Hard Pass Rate (All Required Fields Correct):** {aggregate_metrics.hard_pass_rate:.1%} ({aggregate_metrics.hard_pass_count}/{len(extracted_data)} documents)",
        f"- **Mean Overall Confidence:** {aggregate_metrics.mean_confidence:.3f}" if aggregate_metrics.mean_confidence else "- **Mean Overall Confidence:** N/A",
        f"- **Mean Business Impact Score:** {aggregate_metrics.mean_business_impact_score:.3f}",
        f"- **Mean Weighted F1:** {aggregate_metrics.mean_weighted_f1:.3f}",
        "",
        "### Confidence Calibration",
        "",
        f"- **Expected Calibration Error (ECE):** {calibration_metrics.expected_calibration_error:.3f} (lower is better, 0.0 = perfectly calibrated)",
        f"- **Max Calibration Error (MCE):** {calibration_metrics.max_calibration_error:.3f}",
        f"- **Calibration Slope:** {calibration_metrics.calibration_slope:.3f} (correlation between confidence and correctness)",
        "",
        "#### Confidence Calibration by Bin",
        "",
        "| Confidence Bin | Mean Confidence | Mean Correctness | Samples | Calibration Gap |",
        "|----------------|-----------------|------------------|---------|-----------------|",
    ]
    
    # Add calibration bins
    for bin_key in sorted(calibration_metrics.bins.keys(), reverse=True):
        bin_data = calibration_metrics.bins[bin_key]
        gap = abs(bin_data["mean_confidence"] - bin_data["mean_correctness"])
        report_lines.append(
            f"| {bin_key} | "
            f"{bin_data['mean_confidence']:.3f} | "
            f"{bin_data['mean_correctness']:.3f} | "
            f"{bin_data['samples']} | "
            f"{gap:.3f} |"
        )
    
    report_lines.extend([
        "",
        "**Interpretation:**",
        "- **Well-calibrated:** Mean correctness ≈ Mean confidence (gap < 0.1)",
        "- **Overconfident:** Mean correctness < Mean confidence (gap > 0.1, correctness lower)",
        "- **Underconfident:** Mean correctness > Mean confidence (gap > 0.1, correctness higher)",
        "",
        "## Document-Level Metrics",
        "",
        "| PDF Name | Extraction Rate | Accuracy | F1 Score | All Required Fields | Avg Confidence | Business Impact |",
        "|----------|----------------|----------|----------|---------------------|----------------|-----------------|",
    ])
    
    # Add document-level metrics table
    for pdf_name in sorted(doc_metrics.keys()):
        doc = doc_metrics[pdf_name]
        conf_str = f"{doc.average_confidence:.3f}" if doc.average_confidence else "N/A"
        report_lines.append(
            f"| {pdf_name} | "
            f"{doc.extraction_rate:.1%} | "
            f"{doc.accuracy:.3f} | "
            f"{doc.f1_score:.3f} | "
            f"{'✓' if doc.all_required_fields_correct else '✗'} ({doc.required_fields_correct}/{doc.total_required_fields}) | "
            f"{conf_str} | "
            f"{doc.business_impact_score:.3f} |"
        )
    
    report_lines.extend([
        "",
        "## Per-Field Metrics",
        "",
        "### Metrics Per Field",
        "",
        "| Field Name | Precision | Recall | F1 Score | Accuracy | Exact Match | Tolerant Match | Mean Similarity |",
        "|------------|-----------|--------|----------|----------|-------------|----------------|-----------------|",
    ])
    
    # Sort fields by F1 score (descending)
    sorted_fields = sorted(metrics.items(), key=lambda x: x[1].f1_score, reverse=True)
    
    for field_name, field_metrics in sorted_fields:
        report_lines.append(
            f"| {field_name} | "
            f"{field_metrics.precision:.3f} | "
            f"{field_metrics.recall:.3f} | "
            f"{field_metrics.f1_score:.3f} | "
            f"{field_metrics.accuracy:.3f} | "
            f"{field_metrics.exact_match_accuracy:.3f} | "
            f"{field_metrics.tolerant_match_accuracy:.3f} | "
            f"{field_metrics.mean_similarity:.3f} |"
        )
    
    report_lines.extend([
        "",
        "## Detailed Metrics",
        "",
    ])
    
    for field_name, field_metrics in sorted_fields:
        report_lines.extend([
            f"### {field_name}",
            "",
            f"- **True Positives:** {field_metrics.true_positives}",
            f"- **False Positives:** {field_metrics.false_positives}",
            f"- **False Negatives:** {field_metrics.false_negatives}",
            f"- **True Negatives:** {field_metrics.true_negatives}",
            f"- **Precision:** {field_metrics.precision:.3f}",
            f"- **Recall:** {field_metrics.recall:.3f}",
            f"- **F1 Score:** {field_metrics.f1_score:.3f}",
            f"- **Accuracy:** {field_metrics.accuracy:.3f}",
            f"- **Exact Match Accuracy:** {field_metrics.exact_match_accuracy:.3f}",
            f"- **Tolerant Match Accuracy:** {field_metrics.tolerant_match_accuracy:.3f}",
            f"- **Mean Similarity:** {field_metrics.mean_similarity:.3f}",
            f"- **Total Documents:** {field_metrics.total_documents}",
            "",
        ])
        
        # Confidence calibration
        if field_metrics.confidence_bins:
            report_lines.append("#### Confidence Calibration")
            report_lines.append("")
            report_lines.append("| Confidence Bin | Samples | Mean Correctness |")
            report_lines.append("|----------------|---------|------------------|")
            
            for bin_key in sorted(field_metrics.confidence_bins.keys(), reverse=True):
                samples = field_metrics.confidence_bins[bin_key]
                mean_correctness = sum(samples) / len(samples) if samples else 0.0
                report_lines.append(f"| {bin_key} | {len(samples)} | {mean_correctness:.3f} |")
            
            report_lines.append("")
    
    # Add Line Item Metrics Section
    report_lines.extend([
        "",
        "## Line Item Metrics",
        "",
        "### Line Item Count Metrics",
        "",
        "| PDF Name | Extracted Count | Ground Truth Count | Count Match | Count Difference | Count Accuracy |",
        "|----------|-----------------|-------------------|-------------|------------------|----------------|",
    ])
    
    # Add count metrics
    count_metrics_dict = line_item_metrics.get("count_metrics", {})
    for pdf_name in sorted(count_metrics_dict.keys()):
        count_metrics = count_metrics_dict[pdf_name]
        report_lines.append(
            f"| {pdf_name} | "
            f"{count_metrics['extracted_count']} | "
            f"{count_metrics['ground_truth_count']} | "
            f"{'Yes' if count_metrics['count_match'] else 'No'} | "
            f"{count_metrics['count_difference']} | "
            f"{count_metrics['count_accuracy']:.3f} |"
        )
    
    # Calculate aggregate count metrics
    if count_metrics_dict:
        total_extracted = sum(m['extracted_count'] for m in count_metrics_dict.values())
        total_gt = sum(m['ground_truth_count'] for m in count_metrics_dict.values())
        total_match = sum(1 for m in count_metrics_dict.values() if m['count_match'])
        mean_accuracy = sum(m['count_accuracy'] for m in count_metrics_dict.values()) / len(count_metrics_dict)
        
        report_lines.extend([
            "",
            f"**Summary:**",
            f"- Total Extracted Line Items: {total_extracted}",
            f"- Total Ground Truth Line Items: {total_gt}",
            f"- Documents with Matching Count: {total_match}/{len(count_metrics_dict)} ({total_match/len(count_metrics_dict)*100:.1f}%)",
            f"- Mean Count Accuracy: {mean_accuracy:.3f}",
            "",
            "### Line Item Field Metrics",
            "",
            "| Field Name | Precision | Recall | F1 Score | Accuracy | Exact Match | Tolerant Match | Mean Similarity |",
            "|------------|-----------|--------|----------|----------|-------------|----------------|-----------------|",
        ])
        
        # Add field metrics
        field_metrics_dict = line_item_metrics.get("field_metrics", {})
        sorted_li_fields = sorted(field_metrics_dict.items(), key=lambda x: x[1].get("f1_score", 0), reverse=True)
        
        for field_name, field_metrics in sorted_li_fields:
            if field_metrics.get("total_line_items", 0) > 0:  # Only show fields with data
                report_lines.append(
                    f"| {field_name} | "
                    f"{field_metrics.get('precision', 0):.3f} | "
                    f"{field_metrics.get('recall', 0):.3f} | "
                    f"{field_metrics.get('f1_score', 0):.3f} | "
                    f"{field_metrics.get('accuracy', 0):.3f} | "
                    f"{field_metrics.get('exact_match_accuracy', 0):.3f} | "
                    f"{field_metrics.get('tolerant_match_accuracy', 0):.3f} | "
                    f"{field_metrics.get('mean_similarity', 0):.3f} |"
                )
        
        # Add aggregation metrics
        report_lines.extend([
            "",
            "### Aggregation Validation Metrics",
            "",
            "| PDF Name | Subtotal Valid | GST Valid | PST Valid | QST Valid | Tax Valid | Total Valid | All Valid | Validation Score |",
            "|----------|----------------|-----------|-----------|-----------|-----------|-------------|-----------|------------------|",
        ])
        
        agg_metrics_dict = line_item_metrics.get("aggregation_metrics", {})
        for pdf_name in sorted(agg_metrics_dict.keys()):
            agg_metrics = agg_metrics_dict[pdf_name]
            report_lines.append(
                f"| {pdf_name} | "
                f"{'Yes' if agg_metrics.get('subtotal_valid') else 'No'} | "
                f"{'Yes' if agg_metrics.get('gst_amount_valid') else 'No'} | "
                f"{'Yes' if agg_metrics.get('pst_amount_valid') else 'No'} | "
                f"{'Yes' if agg_metrics.get('qst_amount_valid') else 'No'} | "
                f"{'Yes' if agg_metrics.get('tax_amount_valid') else 'No'} | "
                f"{'Yes' if agg_metrics.get('total_amount_valid') else 'No'} | "
                f"{'Yes' if agg_metrics.get('all_valid') else 'No'} | "
                f"{agg_metrics.get('validation_score', 0):.3f} |"
            )
        
        # Calculate aggregate aggregation metrics
        if agg_metrics_dict:
            all_valid_count = sum(1 for m in agg_metrics_dict.values() if m.get('all_valid'))
            mean_validation_score = sum(m.get('validation_score', 0) for m in agg_metrics_dict.values()) / len(agg_metrics_dict)
            
            report_lines.extend([
                "",
                f"**Summary:**",
                f"- Documents with All Validations Passed: {all_valid_count}/{len(agg_metrics_dict)} ({all_valid_count/len(agg_metrics_dict)*100:.1f}%)",
                f"- Mean Validation Score: {mean_validation_score:.3f}",
                "",
            ])
    
    # Save report
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    # Save CSVs
    # Field-level metrics CSV
    field_csv_data = []
    for field_name, field_metrics in sorted_fields:
        field_csv_data.append(field_metrics.to_dict())
    
    field_csv_df = pd.DataFrame(field_csv_data)
    field_csv_path = output_path.replace('.md', '_field_metrics.csv')
    field_csv_df.to_csv(field_csv_path, index=False)
    
    # Document-level metrics CSV
    doc_csv_data = []
    for pdf_name in sorted(doc_metrics.keys()):
        doc_csv_data.append(doc_metrics[pdf_name].to_dict())
    
    doc_csv_df = pd.DataFrame(doc_csv_data)
    doc_csv_path = output_path.replace('.md', '_document_metrics.csv')
    doc_csv_df.to_csv(doc_csv_path, index=False)
    
    # Aggregate metrics CSV
    agg_csv_data = [aggregate_metrics.to_dict()]
    agg_csv_df = pd.DataFrame(agg_csv_data)
    agg_csv_path = output_path.replace('.md', '_aggregate_metrics.csv')
    agg_csv_df.to_csv(agg_csv_path, index=False)
    
    # Confidence calibration CSV
    cal_dict = calibration_metrics.to_dict()
    # Flatten bins for CSV
    cal_csv_data = []
    for bin_key, bin_data in cal_dict["bins"].items():
        cal_csv_data.append({
            "confidence_bin": bin_key,
            "mean_confidence": bin_data["mean_confidence"],
            "mean_correctness": bin_data["mean_correctness"],
            "samples": bin_data["samples"],
            "calibration_gap": abs(bin_data["mean_confidence"] - bin_data["mean_correctness"]),
        })
    # Add overall metrics
    if cal_csv_data:
        cal_csv_data[0].update({
            "expected_calibration_error": cal_dict["expected_calibration_error"],
            "max_calibration_error": cal_dict["max_calibration_error"],
            "calibration_slope": cal_dict["calibration_slope"],
        })
    cal_csv_df = pd.DataFrame(cal_csv_data)
    cal_csv_path = output_path.replace('.md', '_confidence_calibration.csv')
    cal_csv_df.to_csv(cal_csv_path, index=False)
    
    # Line item metrics CSVs
    if line_item_metrics:
        # Count metrics CSV
        count_csv_data = list(line_item_metrics.get("count_metrics", {}).values())
        if count_csv_data:
            count_csv_df = pd.DataFrame(count_csv_data)
            count_csv_path = output_path.replace('.md', '_line_item_count_metrics.csv')
            count_csv_df.to_csv(count_csv_path, index=False)
            print(f"Line item count metrics CSV saved to: {count_csv_path}")
        
        # Field metrics CSV
        field_li_csv_data = list(line_item_metrics.get("field_metrics", {}).values())
        if field_li_csv_data:
            field_li_csv_df = pd.DataFrame(field_li_csv_data)
            field_li_csv_path = output_path.replace('.md', '_line_item_field_metrics.csv')
            field_li_csv_df.to_csv(field_li_csv_path, index=False)
            print(f"Line item field metrics CSV saved to: {field_li_csv_path}")
        
        # Aggregation metrics CSV
        agg_li_csv_data = list(line_item_metrics.get("aggregation_metrics", {}).values())
        if agg_li_csv_data:
            agg_li_csv_df = pd.DataFrame(agg_li_csv_data)
            agg_li_csv_path = output_path.replace('.md', '_line_item_aggregation_metrics.csv')
            agg_li_csv_df.to_csv(agg_li_csv_path, index=False)
            print(f"Line item aggregation metrics CSV saved to: {agg_li_csv_path}")
    
    print(f"Metrics report saved to: {output_path}")
    print(f"Field metrics CSV saved to: {field_csv_path}")
    print(f"Document metrics CSV saved to: {doc_csv_path}")
    print(f"Aggregate metrics CSV saved to: {agg_csv_path}")
    print(f"Confidence calibration CSV saved to: {cal_csv_path}")
    
    return {
        "field_metrics": metrics,
        "document_metrics": doc_metrics,
        "line_item_metrics": line_item_metrics,
        "aggregate_metrics": aggregate_metrics,
    }


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate per-field metrics report")
    parser.add_argument(
        "--extraction-csv",
        required=True,
        help="Path to extraction results CSV",
    )
    parser.add_argument(
        "--ground-truth",
        help="Path to ground truth file (CSV or JSON). If not provided, will use extraction results as baseline.",
    )
    parser.add_argument(
        "--output",
        default="per_field_metrics_report.md",
        help="Output report path",
    )
    
    args = parser.parse_args()
    
    # Load extraction results
    print(f"Loading extraction results from: {args.extraction_csv}")
    extracted_data = load_extraction_results_grouped(args.extraction_csv)
    field_names = get_all_field_names(args.extraction_csv)
    
    print(f"Loaded {len(extracted_data)} documents")
    print(f"Found {len(field_names)} fields")
    
    # Load ground truth
    if args.ground_truth and Path(args.ground_truth).exists():
        print(f"Loading ground truth from: {args.ground_truth}")
        loader = GroundTruthLoader(args.ground_truth)
        ground_truth = []
        for extracted in extracted_data:
            pdf_name = extracted.get("pdf_name")
            gt_entry = {"pdf_name": pdf_name}
            gt_entry.update(loader.get_ground_truth(pdf_name))
            ground_truth.append(gt_entry)
    else:
        print("No ground truth provided. Using extraction results as baseline (for testing only).")
        ground_truth = generate_ground_truth_from_extraction(extracted_data, field_names)
    
    # Generate metrics
    print("Calculating metrics...")
    results = generate_metrics_report(extracted_data, ground_truth, field_names, args.output)
    
    print(f"\nField metrics calculated for {len(results['field_metrics'])} fields")
    print(f"Document metrics calculated for {len(results['document_metrics'])} documents")
    print(f"Hard pass rate: {results['aggregate_metrics'].hard_pass_rate:.1%}")
    print(f"Mean extraction rate: {results['aggregate_metrics'].mean_extraction_rate:.1%}")
    print("Report generation complete!")


if __name__ == "__main__":
    main()
