"""
Enhanced False Negative and False Positive Detector

Detects:
1. False Negatives: Fields that should be extracted but aren't (have confidence/DI source but no value)
2. False Positives: Fields marked as extracted but shouldn't be (need manual validation)
3. Potential False Negatives: Fields with confidence scores but empty values
"""

import pandas as pd
import sys
from pathlib import Path

def detect_false_negatives_and_positives(csv_path='di_ocr_extraction_with_false_negatives.csv'):
    """
    Detect false negatives and false positives in extraction results.
    
    Args:
        csv_path: Path to the extraction results CSV
        
    Returns:
        Tuple of (false_negatives_df, false_positives_df, potential_false_negatives_df)
    """
    if not Path(csv_path).exists():
        print(f"Error: {csv_path} not found")
        return None, None, None
    
    df = pd.read_csv(csv_path)
    
    false_negatives = []
    potential_false_negatives = []
    
    for _, row in df.iterrows():
        extracted = row.get('extracted', False)
        value = row.get('value')
        confidence = row.get('confidence')
        di_sources = row.get('di_field_sources')
        confidence_category = row.get('confidence_category', 'none')
        
        # Check if value exists (not None, not empty string, not 'None')
        has_value = pd.notna(value) and str(value).strip() not in ['', 'None', 'nan', 'NaN']
        
        # False Negative Type 1: Has confidence/DI source but marked as not extracted and has value
        if not extracted and has_value:
            false_negatives.append({
                'pdf_name': row['pdf_name'],
                'field_name': row['field_name'],
                'extracted': extracted,
                'value': value,
                'confidence': confidence,
                'confidence_category': confidence_category,
                'di_field_sources': di_sources,
                'type': 'has_value_not_extracted',
                'reason': 'Field has value but marked as not extracted'
            })
        
        # Potential False Negative: Has confidence/DI source but no value
        # This suggests DI found something but it didn't map correctly
        elif not extracted and not has_value:
            if (pd.notna(confidence) and confidence > 0) or (pd.notna(di_sources) and str(di_sources).strip() not in ['', 'None']):
                potential_false_negatives.append({
                    'pdf_name': row['pdf_name'],
                    'field_name': row['field_name'],
                    'extracted': extracted,
                    'value': value,
                    'confidence': confidence,
                    'confidence_category': confidence_category,
                    'di_field_sources': di_sources,
                    'type': 'has_confidence_no_value',
                    'reason': 'DI found field (has confidence/DI source) but value is empty - possible mapping issue'
                })
    
    false_negatives_df = pd.DataFrame(false_negatives)
    potential_false_negatives_df = pd.DataFrame(potential_false_negatives)
    
    # False Positives would require manual validation against PDFs
    # For now, we'll flag fields that are extracted but might be questionable
    # (e.g., extracted=True but confidence is low or None)
    false_positives = []
    for _, row in df.iterrows():
        extracted = row.get('extracted', False)
        value = row.get('value')
        confidence = row.get('confidence')
        confidence_category = row.get('confidence_category', 'none')
        
        if extracted:
            # Flag if extracted but no confidence or very low confidence
            if pd.isna(confidence) or (confidence is not None and confidence < 0.5):
                false_positives.append({
                    'pdf_name': row['pdf_name'],
                    'field_name': row['field_name'],
                    'extracted': extracted,
                    'value': value,
                    'confidence': confidence,
                    'confidence_category': confidence_category,
                    'type': 'low_confidence_extracted',
                    'reason': 'Field marked as extracted but has low or no confidence - needs validation'
                })
    
    false_positives_df = pd.DataFrame(false_positives)
    
    return false_negatives_df, false_positives_df, potential_false_negatives_df

def generate_detection_report(false_negatives_df, false_positives_df, potential_false_negatives_df, output_path='false_negatives_report.csv'):
    """
    Generate a comprehensive false negative/positive detection report.
    
    Args:
        false_negatives_df: DataFrame with false negatives
        false_positives_df: DataFrame with false positives
        potential_false_negatives_df: DataFrame with potential false negatives
        output_path: Path to save the report
    """
    all_issues = []
    
    # Add false negatives
    if false_negatives_df is not None and len(false_negatives_df) > 0:
        for _, row in false_negatives_df.iterrows():
            all_issues.append({
                'pdf_name': row['pdf_name'],
                'field_name': row['field_name'],
                'issue_type': 'FALSE_NEGATIVE',
                'extracted': row['extracted'],
                'value': row['value'],
                'confidence': row['confidence'],
                'confidence_category': row['confidence_category'],
                'di_field_sources': row.get('di_field_sources', ''),
                'reason': row['reason']
            })
    
    # Add potential false negatives
    if potential_false_negatives_df is not None and len(potential_false_negatives_df) > 0:
        for _, row in potential_false_negatives_df.iterrows():
            all_issues.append({
                'pdf_name': row['pdf_name'],
                'field_name': row['field_name'],
                'issue_type': 'POTENTIAL_FALSE_NEGATIVE',
                'extracted': row['extracted'],
                'value': row['value'],
                'confidence': row['confidence'],
                'confidence_category': row['confidence_category'],
                'di_field_sources': row.get('di_field_sources', ''),
                'reason': row['reason']
            })
    
    # Add false positives
    if false_positives_df is not None and len(false_positives_df) > 0:
        for _, row in false_positives_df.iterrows():
            all_issues.append({
                'pdf_name': row['pdf_name'],
                'field_name': row['field_name'],
                'issue_type': 'FALSE_POSITIVE',
                'extracted': row['extracted'],
                'value': row['value'],
                'confidence': row['confidence'],
                'confidence_category': row['confidence_category'],
                'di_field_sources': '',
                'reason': row['reason']
            })
    
    if all_issues:
        report_df = pd.DataFrame(all_issues)
        report_df.to_csv(output_path, index=False)
        print(f"Report saved to: {output_path}")
        print(f"Total issues found: {len(report_df)}")
        print(f"  - False Negatives: {len(false_negatives_df) if false_negatives_df is not None and len(false_negatives_df) > 0 else 0}")
        print(f"  - Potential False Negatives: {len(potential_false_negatives_df) if potential_false_negatives_df is not None and len(potential_false_negatives_df) > 0 else 0}")
        print(f"  - False Positives: {len(false_positives_df) if false_positives_df is not None and len(false_positives_df) > 0 else 0}")
        return report_df
    else:
        # Create empty report with headers
        empty_df = pd.DataFrame(columns=['pdf_name', 'field_name', 'issue_type', 'extracted', 'value', 'confidence', 'confidence_category', 'di_field_sources', 'reason'])
        empty_df.to_csv(output_path, index=False)
        print(f"No issues found. Empty report saved to: {output_path}")
        return empty_df

def main():
    """Main function."""
    csv_path = sys.argv[1] if len(sys.argv) > 1 else 'di_ocr_extraction_with_false_negatives.csv'
    
    print(f"Analyzing false negatives and false positives in: {csv_path}")
    print("="*80)
    
    false_negatives_df, false_positives_df, potential_false_negatives_df = detect_false_negatives_and_positives(csv_path)
    
    print(f"\nDetection Results:")
    print(f"  False Negatives: {len(false_negatives_df) if false_negatives_df is not None and len(false_negatives_df) > 0 else 0}")
    print(f"  Potential False Negatives: {len(potential_false_negatives_df) if potential_false_negatives_df is not None and len(potential_false_negatives_df) > 0 else 0}")
    print(f"  False Positives: {len(false_positives_df) if false_positives_df is not None and len(false_positives_df) > 0 else 0}")
    
    # Show examples
    if false_negatives_df is not None and len(false_negatives_df) > 0:
        print(f"\nExample False Negatives (first 5):")
        for idx, row in false_negatives_df.head(5).iterrows():
            print(f"  {row['pdf_name']} - {row['field_name']}: value='{row['value']}', confidence={row['confidence']}")
    
    if potential_false_negatives_df is not None and len(potential_false_negatives_df) > 0:
        print(f"\nExample Potential False Negatives (first 5):")
        for idx, row in potential_false_negatives_df.head(5).iterrows():
            print(f"  {row['pdf_name']} - {row['field_name']}: confidence={row['confidence']}, DI source={row.get('di_field_sources', 'N/A')}")
    
    # Generate report
    report_df = generate_detection_report(false_negatives_df, false_positives_df, potential_false_negatives_df)
    
    return report_df

if __name__ == "__main__":
    main()
