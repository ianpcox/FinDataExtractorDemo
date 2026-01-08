"""
Quick diagnostic: Analyze address extraction issues from existing CSV results.

This analyzes the di_ocr_extraction_with_false_negatives.csv to understand
why addresses have DI sources but no values.
"""

import pandas as pd
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Load the CSV
df = pd.read_csv('di_ocr_extraction_with_false_negatives.csv')

print("="*100)
print("ADDRESS EXTRACTION DIAGNOSIS")
print("="*100)

# Filter for address fields
address_fields = ['vendor_address', 'bill_to_address', 'remit_to_address']
address_df = df[df['field_name'].isin(address_fields)]

print(f"\nTotal address field records: {len(address_df)}")
print(f"PDFs with address issues: {address_df['pdf_name'].nunique()}")

# Group by PDF and field
print("\n" + "="*100)
print("ADDRESS FIELD STATUS BY PDF")
print("="*100)

for pdf_name in sorted(address_df['pdf_name'].unique()):
    pdf_data = address_df[address_df['pdf_name'] == pdf_name]
    print(f"\n📄 {pdf_name}:")
    
    for field_name in address_fields:
        field_data = pdf_data[pdf_data['field_name'] == field_name]
        if len(field_data) > 0:
            row = field_data.iloc[0]
            extracted = row.get('extracted', False)
            value = row.get('value')
            confidence = row.get('confidence')
            di_sources = row.get('di_field_sources', '')
            
            status = "✅" if extracted and value else "❌"
            print(f"  {status} {field_name}:")
            print(f"    Extracted: {extracted}")
            print(f"    Value: {value if value else 'None/Empty'}")
            print(f"    Confidence: {confidence}")
            print(f"    DI Sources: {di_sources if di_sources else 'None'}")

# Summary statistics
print("\n" + "="*100)
print("SUMMARY STATISTICS")
print("="*100)

for field_name in address_fields:
    field_data = address_df[address_df['field_name'] == field_name]
    total = len(field_data)
    extracted = len(field_data[field_data['extracted'] == True])
    has_value = len(field_data[pd.notna(field_data['value']) & (field_data['value'] != '')])
    has_di_source = len(field_data[pd.notna(field_data['di_field_sources']) & (field_data['di_field_sources'] != '')])
    has_confidence = len(field_data[pd.notna(field_data['confidence']) & (field_data['confidence'] > 0)])
    
    print(f"\n{field_name}:")
    print(f"  Total records: {total}")
    print(f"  Marked as extracted: {extracted}")
    print(f"  Has value: {has_value}")
    print(f"  Has DI source: {has_di_source}")
    print(f"  Has confidence: {has_confidence}")
    print(f"  Issue: {total - has_value} records have DI source/confidence but no value")

print("\n" + "="*100)
print("HYPOTHESIS")
print("="*100)
print("""
Based on the data, it appears that:
1. DI API is detecting address fields (has DI sources like 'VendorAddress', 'CustomerAddress')
2. DI API is assigning confidence scores to these fields
3. BUT the address value from DI is either:
   - None/empty dict
   - Dict with all None/empty values
   - Empty string

This suggests the DI API recognizes address fields exist but cannot extract their content,
possibly due to:
- Poor OCR quality for address sections
- Address formatting not recognized by DI
- Address fields split across multiple locations
- Address fields in non-standard formats

Next step: Run diagnose_address_extraction.py to inspect raw DI API responses.
""")
