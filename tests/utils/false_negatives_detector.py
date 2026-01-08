"""
False Negatives Detector

Identifies potential false negatives in extraction test results by finding
fields that are marked as not extracted but have values from at least one method.
"""

import pandas as pd
import sys
from pathlib import Path

def identify_false_negatives(csv_path='comprehensive_extraction_field_details.csv'):
    """
    Identify potential false negatives in extraction results.
    
    Args:
        csv_path: Path to the field details CSV file
        
    Returns:
        DataFrame with potential false negatives
    """
    if not Path(csv_path).exists():
        print(f"Error: {csv_path} not found")
        return None
    
    df = pd.read_csv(csv_path)
    
    false_negatives = []
    
    for _, row in df.iterrows():
        # Check which extraction status column exists
        extracted_col = None
        if 'best_extracted' in df.columns:
            extracted_col = 'best_extracted'
        elif 'extracted' in df.columns:
            extracted_col = 'extracted'
        else:
            # No extraction column found, skip
            continue
        
        if row[extracted_col] == False:
            # Check if any extraction method found a value
            has_di_value = False
            has_llm_value = False
            has_multimodal_value = False
            
            # Check DI value
            if 'di_value' in df.columns:
                has_di_value = pd.notna(row['di_value']) and str(row['di_value']).strip() not in ['', 'None', 'nan']
            elif 'value' in df.columns:
                has_di_value = pd.notna(row['value']) and str(row['value']).strip() not in ['', 'None', 'nan']
            
            # Check LLM value
            if 'llm_value' in df.columns:
                has_llm_value = pd.notna(row['llm_value']) and str(row['llm_value']).strip() not in ['', 'None', 'nan']
            
            # Check Multimodal value
            if 'multimodal_value' in df.columns:
                has_multimodal_value = pd.notna(row['multimodal_value']) and str(row['multimodal_value']).strip() not in ['', 'None', 'nan']
            
            if has_di_value or has_llm_value or has_multimodal_value:
                fn_row = {
                    'pdf_name': row['pdf_name'],
                    'field_name': row['field_name'],
                    'extracted': row[extracted_col],
                    'has_di_value': has_di_value,
                    'has_llm_value': has_llm_value,
                    'has_multimodal_value': has_multimodal_value,
                }
                
                # Add available columns
                if 'di_extracted' in df.columns:
                    fn_row['di_extracted'] = row['di_extracted']
                if 'di_value' in df.columns:
                    fn_row['di_value'] = row['di_value']
                elif 'value' in df.columns:
                    fn_row['di_value'] = row['value']
                if 'di_confidence' in df.columns:
                    fn_row['di_confidence'] = row['di_confidence']
                elif 'confidence' in df.columns:
                    fn_row['di_confidence'] = row['confidence']
                
                if 'llm_extracted' in df.columns:
                    fn_row['llm_extracted'] = row['llm_extracted']
                if 'llm_value' in df.columns:
                    fn_row['llm_value'] = row['llm_value']
                if 'llm_confidence' in df.columns:
                    fn_row['llm_confidence'] = row['llm_confidence']
                if 'llm_source' in df.columns:
                    fn_row['llm_source'] = row['llm_source']
                
                if 'multimodal_extracted' in df.columns:
                    fn_row['multimodal_extracted'] = row['multimodal_extracted']
                if 'multimodal_value' in df.columns:
                    fn_row['multimodal_value'] = row['multimodal_value']
                if 'multimodal_confidence' in df.columns:
                    fn_row['multimodal_confidence'] = row['multimodal_confidence']
                
                false_negatives.append(fn_row)
    
    return pd.DataFrame(false_negatives)

def analyze_false_negatives(fn_df):
    """
    Analyze false negatives and provide insights.
    
    Args:
        fn_df: DataFrame with false negatives
    """
    if fn_df is None or len(fn_df) == 0:
        print("No false negatives found!")
        return
    
    print(f"\n{'='*80}")
    print(f"FALSE NEGATIVES ANALYSIS")
    print(f"{'='*80}\n")
    print(f"Total false negatives found: {len(fn_df)}\n")
    
    # Group by field name
    print("False negatives by field name:")
    print("-" * 80)
    by_field = fn_df.groupby('field_name').size().sort_values(ascending=False)
    for field, count in by_field.items():
        print(f"  {field:<40} {count:>3} occurrences")
    
    # Group by PDF
    print(f"\nFalse negatives by PDF:")
    print("-" * 80)
    by_pdf = fn_df.groupby('pdf_name').size().sort_values(ascending=False)
    for pdf, count in by_pdf.items():
        print(f"  {pdf:<50} {count:>3} fields")
    
    # Group by extraction method
    print(f"\nFalse negatives by extraction method:")
    print("-" * 80)
    di_count = fn_df['has_di_value'].sum()
    llm_count = fn_df['has_llm_value'].sum()
    multimodal_count = fn_df['has_multimodal_value'].sum()
    print(f"  DI OCR found value but marked not extracted:     {di_count:>3}")
    print(f"  Base LLM found value but marked not extracted:   {llm_count:>3}")
    print(f"  Multimodal LLM found value but marked not extracted: {multimodal_count:>3}")
    
    # Fields with low confidence
    print(f"\nFalse negatives with confidence scores:")
    print("-" * 80)
    low_conf_di = fn_df[fn_df['has_di_value'] & (fn_df['di_confidence'] < 0.75) & (fn_df['di_confidence'].notna())]
    low_conf_llm = fn_df[fn_df['has_llm_value'] & (fn_df['llm_confidence'] < 0.75) & (fn_df['llm_confidence'].notna())]
    print(f"  DI fields with confidence < 0.75: {len(low_conf_di)}")
    print(f"  LLM fields with confidence < 0.75: {len(low_conf_llm)}")
    
    # Show examples
    print(f"\nExample false negatives (first 10):")
    print("-" * 80)
    for idx, row in fn_df.head(10).iterrows():
        methods = []
        if row['has_di_value']:
            methods.append(f"DI({row['di_confidence']:.2f})" if pd.notna(row['di_confidence']) else "DI")
        if row['has_llm_value']:
            methods.append(f"LLM({row['llm_confidence']:.2f})" if pd.notna(row['llm_confidence']) else "LLM")
        if row['has_multimodal_value']:
            methods.append(f"MM({row['multimodal_confidence']:.2f})" if pd.notna(row['multimodal_confidence']) else "MM")
        
        value_preview = ""
        if row['has_di_value']:
            value_preview = str(row['di_value'])[:30]
        elif row['has_llm_value']:
            value_preview = str(row['llm_value'])[:30]
        elif row['has_multimodal_value']:
            value_preview = str(row['multimodal_value'])[:30]
        
        print(f"  {row['pdf_name']:<30} {row['field_name']:<25} {', '.join(methods):<20} {value_preview}")

def main():
    """Main function."""
    csv_path = sys.argv[1] if len(sys.argv) > 1 else 'comprehensive_extraction_field_details.csv'
    
    print(f"Analyzing false negatives in: {csv_path}")
    
    fn_df = identify_false_negatives(csv_path)
    
    if fn_df is None:
        return
    
    analyze_false_negatives(fn_df)
    
    # Save detailed report
    output_path = 'false_negatives_report.csv'
    fn_df.to_csv(output_path, index=False)
    print(f"\n{'='*80}")
    print(f"Detailed report saved to: {output_path}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
