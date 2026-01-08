"""Check tax extraction from database and Document Intelligence"""
import sqlite3
import json
from pathlib import Path

# Check database
db_path = Path("findataextractor_demo.db")
if not db_path.exists():
    print(f"Database not found: {db_path}")
    exit(1)

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Get sample invoices
cursor.execute("""
    SELECT id, gst_amount, pst_amount, qst_amount, hst_amount, tax_amount, 
           field_confidence, extraction_confidence, status, processing_state
    FROM invoices 
    WHERE processing_state = 'EXTRACTED' OR status LIKE '%extracted%'
    LIMIT 5
""")

rows = cursor.fetchall()
print("=" * 80)
print("TAX EXTRACTION ANALYSIS")
print("=" * 80)
print(f"\nFound {len(rows)} extracted invoices\n")

for row in rows:
    invoice_id, gst, pst, qst, hst, tax, field_conf, ext_conf, status, proc_state = row
    print(f"Invoice ID: {invoice_id[:30]}...")
    print(f"  Status: {status}, Processing State: {proc_state}")
    print(f"  GST Amount: {gst}")
    print(f"  PST Amount: {pst}")
    print(f"  QST Amount: {qst}")
    print(f"  HST Amount: {hst}")
    print(f"  Tax Amount: {tax}")
    print(f"  Extraction Confidence: {ext_conf}")
    
    # Check field confidence for tax fields
    if field_conf:
        try:
            conf_dict = json.loads(field_conf)
            tax_confidences = {
                "gst_amount": conf_dict.get("gst_amount"),
                "pst_amount": conf_dict.get("pst_amount"),
                "qst_amount": conf_dict.get("qst_amount"),
                "hst_amount": conf_dict.get("hst_amount"),
                "tax_amount": conf_dict.get("tax_amount"),
            }
            print(f"  Tax Field Confidences:")
            for field, conf in tax_confidences.items():
                print(f"    {field}: {conf}")
        except Exception as e:
            print(f"  Could not parse field_confidence: {e}")
    print()

conn.close()
