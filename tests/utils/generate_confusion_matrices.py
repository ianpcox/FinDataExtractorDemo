"""
Generate Confusion Matrices for DI OCR Extraction Tests

Creates confusion matrices for:
1. Per PDF (overall extraction quality per document)
2. Per Field (how well each field is extracted across all PDFs)
3. Overall (aggregate across all PDFs)

Confusion Matrix Categories:
- True Positive (TP): Field extracted and should be extracted (has value, high confidence)
- False Positive (FP): Field extracted but shouldn't be (extracted=True but low/no confidence or wrong)
- False Negative (FN): Field should be extracted but isn't (has confidence/DI source but no value)
- True Negative (TN): Field correctly not extracted (no value, no confidence, no DI source)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys
from typing import Dict, Tuple

def calculate_confusion_matrix_for_pdf(df: pd.DataFrame, pdf_name: str) -> Dict[str, int]:
    """
    Calculate confusion matrix for a single PDF.
    
    Args:
        df: DataFrame with extraction results
        pdf_name: Name of the PDF
        
    Returns:
        Dictionary with TP, FP, FN, TN counts
    """
    pdf_df = df[df['pdf_name'] == pdf_name].copy()
    
    tp = 0  # True Positive: extracted=True, has value, has confidence
    fp = 0  # False Positive: extracted=True but low/no confidence or questionable
    fn = 0  # False Negative: extracted=False but has confidence/DI source (should be extracted)
    tn = 0  # True Negative: extracted=False, no value, no confidence, no DI source
    
    for _, row in pdf_df.iterrows():
        extracted = row.get('extracted', False)
        value = row.get('value')
        confidence = row.get('confidence')
        di_sources = row.get('di_field_sources', '')
        confidence_category = row.get('confidence_category', 'none')
        
        has_value = pd.notna(value) and str(value).strip() not in ['', 'None', 'nan', 'NaN']
        has_confidence = pd.notna(confidence) and confidence > 0
        has_di_source = pd.notna(di_sources) and str(di_sources).strip() not in ['', 'None']
        is_high_confidence = confidence_category in ['high', 'medium']
        
        if extracted:
            if has_value and (has_confidence or is_high_confidence):
                tp += 1  # Correctly extracted with confidence
            else:
                fp += 1  # Extracted but questionable (no/low confidence)
        else:
            if has_confidence or has_di_source:
                fn += 1  # Should be extracted (DI found it) but wasn't
            else:
                tn += 1  # Correctly not extracted (nothing found)
    
    return {
        'pdf_name': pdf_name,
        'TP': tp,
        'FP': fp,
        'FN': fn,
        'TN': tn,
        'Total': len(pdf_df),
        'Precision': tp / (tp + fp) if (tp + fp) > 0 else 0,
        'Recall': tp / (tp + fn) if (tp + fn) > 0 else 0,
        'F1_Score': 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) > 0 else 0,
        'Accuracy': (tp + tn) / (tp + fp + fn + tn) if (tp + fp + fn + tn) > 0 else 0
    }

def calculate_confusion_matrix_for_field(df: pd.DataFrame, field_name: str) -> Dict[str, int]:
    """
    Calculate confusion matrix for a single field across all PDFs.
    
    Args:
        df: DataFrame with extraction results
        field_name: Name of the field
        
    Returns:
        Dictionary with TP, FP, FN, TN counts
    """
    field_df = df[df['field_name'] == field_name].copy()
    
    tp = 0
    fp = 0
    fn = 0
    tn = 0
    
    for _, row in field_df.iterrows():
        extracted = row.get('extracted', False)
        value = row.get('value')
        confidence = row.get('confidence')
        di_sources = row.get('di_field_sources', '')
        confidence_category = row.get('confidence_category', 'none')
        
        has_value = pd.notna(value) and str(value).strip() not in ['', 'None', 'nan', 'NaN']
        has_confidence = pd.notna(confidence) and confidence > 0
        has_di_source = pd.notna(di_sources) and str(di_sources).strip() not in ['', 'None']
        is_high_confidence = confidence_category in ['high', 'medium']
        
        if extracted:
            if has_value and (has_confidence or is_high_confidence):
                tp += 1
            else:
                fp += 1
        else:
            if has_confidence or has_di_source:
                fn += 1
            else:
                tn += 1
    
    return {
        'field_name': field_name,
        'TP': tp,
        'FP': fp,
        'FN': fn,
        'TN': tn,
        'Total': len(field_df),
        'Precision': tp / (tp + fp) if (tp + fp) > 0 else 0,
        'Recall': tp / (tp + fn) if (tp + fn) > 0 else 0,
        'F1_Score': 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) > 0 else 0,
        'Accuracy': (tp + tn) / (tp + fp + fn + tn) if (tp + fp + fn + tn) > 0 else 0
    }

def calculate_overall_confusion_matrix(df: pd.DataFrame) -> Dict[str, int]:
    """
    Calculate overall confusion matrix across all PDFs and fields.
    
    Args:
        df: DataFrame with extraction results
        
    Returns:
        Dictionary with TP, FP, FN, TN counts
    """
    tp = 0
    fp = 0
    fn = 0
    tn = 0
    
    for _, row in df.iterrows():
        extracted = row.get('extracted', False)
        value = row.get('value')
        confidence = row.get('confidence')
        di_sources = row.get('di_field_sources', '')
        confidence_category = row.get('confidence_category', 'none')
        
        has_value = pd.notna(value) and str(value).strip() not in ['', 'None', 'nan', 'NaN']
        has_confidence = pd.notna(confidence) and confidence > 0
        has_di_source = pd.notna(di_sources) and str(di_sources).strip() not in ['', 'None']
        is_high_confidence = confidence_category in ['high', 'medium']
        
        if extracted:
            if has_value and (has_confidence or is_high_confidence):
                tp += 1
            else:
                fp += 1
        else:
            if has_confidence or has_di_source:
                fn += 1
            else:
                tn += 1
    
    return {
        'TP': tp,
        'FP': fp,
        'FN': fn,
        'TN': tn,
        'Total': len(df),
        'Precision': tp / (tp + fp) if (tp + fp) > 0 else 0,
        'Recall': tp / (tp + fn) if (tp + fn) > 0 else 0,
        'F1_Score': 2 * tp / (2 * tp + fp + fn) if (2 * tp + fp + fn) > 0 else 0,
        'Accuracy': (tp + tn) / (tp + fp + fn + tn) if (tp + fp + fn + tn) > 0 else 0
    }

def format_confusion_matrix(tp: int, fp: int, fn: int, tn: int) -> str:
    """
    Format confusion matrix as a markdown table.
    
    Args:
        tp, fp, fn, tn: Confusion matrix values
        
    Returns:
        Formatted markdown table
    """
    return f"""
|                | Predicted: Extracted | Predicted: Not Extracted | Total |
|----------------|---------------------|-------------------------|-------|
| **Actual: Extracted** | {tp:>3} (TP) | {fn:>3} (FN) | {tp + fn:>3} |
| **Actual: Not Extracted** | {fp:>3} (FP) | {tn:>3} (TN) | {fp + tn:>3} |
| **Total** | {tp + fp:>3} | {fn + tn:>3} | {tp + fp + fn + tn:>3} |
"""

def generate_confusion_matrix_report(csv_path: str = 'di_ocr_extraction_with_false_negatives.csv'):
    """
    Generate comprehensive confusion matrix report.
    
    Args:
        csv_path: Path to extraction results CSV
    """
    if not Path(csv_path).exists():
        print(f"Error: {csv_path} not found")
        return
    
    df = pd.read_csv(csv_path)
    
    # Get unique PDFs and fields
    pdfs = df['pdf_name'].unique()
    fields = df['field_name'].unique()
    
    print("="*80)
    print("CONFUSION MATRIX ANALYSIS")
    print("="*80)
    
    # 1. Per-PDF Confusion Matrices
    print("\n1. PER-PDF CONFUSION MATRICES")
    print("-"*80)
    pdf_matrices = []
    for pdf_name in sorted(pdfs):
        matrix = calculate_confusion_matrix_for_pdf(df, pdf_name)
        pdf_matrices.append(matrix)
        print(f"\n{pdf_name}:")
        print(f"  TP: {matrix['TP']}, FP: {matrix['FP']}, FN: {matrix['FN']}, TN: {matrix['TN']}")
        print(f"  Precision: {matrix['Precision']:.3f}, Recall: {matrix['Recall']:.3f}, F1: {matrix['F1_Score']:.3f}, Accuracy: {matrix['Accuracy']:.3f}")
    
    pdf_df = pd.DataFrame(pdf_matrices)
    pdf_df.to_csv('confusion_matrix_per_pdf.csv', index=False)
    print(f"\nPer-PDF matrices saved to: confusion_matrix_per_pdf.csv")
    
    # 2. Per-Field Confusion Matrices
    print("\n2. PER-FIELD CONFUSION MATRICES")
    print("-"*80)
    field_matrices = []
    for field_name in sorted(fields):
        matrix = calculate_confusion_matrix_for_field(df, field_name)
        field_matrices.append(matrix)
    
    field_df = pd.DataFrame(field_matrices)
    field_df = field_df.sort_values('F1_Score', ascending=False)
    field_df.to_csv('confusion_matrix_per_field.csv', index=False)
    print(f"Per-Field matrices saved to: confusion_matrix_per_field.csv")
    
    # Show top and bottom performing fields
    print("\nTop 10 Fields by F1 Score:")
    for _, row in field_df.head(10).iterrows():
        print(f"  {row['field_name']:<30} F1: {row['F1_Score']:.3f}, Precision: {row['Precision']:.3f}, Recall: {row['Recall']:.3f}")
    
    print("\nBottom 10 Fields by F1 Score:")
    for _, row in field_df.tail(10).iterrows():
        print(f"  {row['field_name']:<30} F1: {row['F1_Score']:.3f}, Precision: {row['Precision']:.3f}, Recall: {row['Recall']:.3f}")
    
    # 3. Overall Confusion Matrix
    print("\n3. OVERALL CONFUSION MATRIX")
    print("-"*80)
    overall = calculate_overall_confusion_matrix(df)
    print(f"\nOverall Results:")
    print(f"  TP: {overall['TP']}, FP: {overall['FP']}, FN: {overall['FN']}, TN: {overall['TN']}")
    print(f"  Precision: {overall['Precision']:.3f}")
    print(f"  Recall: {overall['Recall']:.3f}")
    print(f"  F1 Score: {overall['F1_Score']:.3f}")
    print(f"  Accuracy: {overall['Accuracy']:.3f}")
    print(format_confusion_matrix(overall['TP'], overall['FP'], overall['FN'], overall['TN']))
    
    # Save overall matrix
    overall_df = pd.DataFrame([overall])
    overall_df.to_csv('confusion_matrix_overall.csv', index=False)
    print(f"Overall matrix saved to: confusion_matrix_overall.csv")
    
    # 4. Generate Markdown Report
    report = []
    report.append("# Confusion Matrix Analysis Report")
    report.append("")
    report.append("## Overall Confusion Matrix")
    report.append("")
    report.append(format_confusion_matrix(overall['TP'], overall['FP'], overall['FN'], overall['TN']))
    report.append("")
    report.append(f"- **Precision:** {overall['Precision']:.3f} (TP / (TP + FP))")
    report.append(f"- **Recall:** {overall['Recall']:.3f} (TP / (TP + FN))")
    report.append(f"- **F1 Score:** {overall['F1_Score']:.3f} (harmonic mean of precision and recall)")
    report.append(f"- **Accuracy:** {overall['Accuracy']:.3f} ((TP + TN) / Total)")
    report.append("")
    report.append("## Per-PDF Confusion Matrices")
    report.append("")
    for pdf_name in sorted(pdfs):
        matrix = calculate_confusion_matrix_for_pdf(df, pdf_name)
        report.append(f"### {pdf_name}")
        report.append("")
        report.append(format_confusion_matrix(matrix['TP'], matrix['FP'], matrix['FN'], matrix['TN']))
        report.append(f"- **Precision:** {matrix['Precision']:.3f}")
        report.append(f"- **Recall:** {matrix['Recall']:.3f}")
        report.append(f"- **F1 Score:** {matrix['F1_Score']:.3f}")
        report.append(f"- **Accuracy:** {matrix['Accuracy']:.3f}")
        report.append("")
    
    report.append("## Per-Field Confusion Matrices (Top 20 by F1 Score)")
    report.append("")
    report.append("| Field Name | TP | FP | FN | TN | Precision | Recall | F1 Score | Accuracy |")
    report.append("|------------|----|----|----|----|-----------|--------|----------|----------|")
    for _, row in field_df.head(20).iterrows():
        report.append(f"| `{row['field_name']}` | {row['TP']} | {row['FP']} | {row['FN']} | {row['TN']} | {row['Precision']:.3f} | {row['Recall']:.3f} | {row['F1_Score']:.3f} | {row['Accuracy']:.3f} |")
    
    report.append("")
    report.append("## Per-Field Confusion Matrices (Bottom 20 by F1 Score)")
    report.append("")
    report.append("| Field Name | TP | FP | FN | TN | Precision | Recall | F1 Score | Accuracy |")
    report.append("|------------|----|----|----|----|-----------|--------|----------|----------|")
    for _, row in field_df.tail(20).iterrows():
        report.append(f"| `{row['field_name']}` | {row['TP']} | {row['FP']} | {row['FN']} | {row['TN']} | {row['Precision']:.3f} | {row['Recall']:.3f} | {row['F1_Score']:.3f} | {row['Accuracy']:.3f} |")
    
    report_text = "\n".join(report)
    with open('confusion_matrix_report.md', 'w', encoding='utf-8') as f:
        f.write(report_text)
    print(f"\nConfusion matrix report saved to: confusion_matrix_report.md")
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)

if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else 'di_ocr_extraction_with_false_negatives.csv'
    generate_confusion_matrix_report(csv_path)
