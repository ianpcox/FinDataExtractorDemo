# Base LLM Extraction Report (Standalone Test)

**Generated:** 2026-01-08 14:27:41 UTC
**File:** ACC012 4202092525.pdf
**Invoice ID:** standalone-llm-test-20260108-142732

---

## Extraction Summary

- **PDF Size:** 57,461 bytes
- **DI Success:** True
- **DI Fields Extracted:** 12
- **Low-Confidence Fields:** 43
- **LLM Triggered:** True
- **LLM Success:** True
- **LLM Groups Processed:** 3
- **LLM Groups Succeeded:** 3
- **LLM Groups Failed:** 0
- **Overall Extraction Confidence:** 0.9005411347517729

## LLM Group Results

### Fields Group: [SUCCESS]
- **Fields:** 31
- **Field Names:** invoice_type, shipping_amount, period_start, reference_number, currency, remit_to_name, vendor_phone, customer_fax, vendor_id, customer_email...

### Addresses Group: [SUCCESS]
- **Fields:** 3
- **Field Names:** remit_to_address, bill_to_address, vendor_address

### Canadian_taxes Group: [SUCCESS]
- **Fields:** 8
- **Field Names:** pst_rate, hst_amount, qst_amount, gst_rate, hst_rate, qst_rate, gst_amount, pst_amount

## Canonical Field Coverage

- **Total Canonical Fields:** 53
- **Fields Extracted:** 29 (54.7%)
- **Fields Missing:** 24 (45.3%)
- **Extracted by DI:** 30
- **Extracted by LLM:** 20
- **DI Only:** 10
- **LLM Only:** 20

## Extracted Fields

| Field Name | Extracted | Confidence | Source | Value Preview |
|------------|-----------|------------|--------|---------------|
| bill_to_address | [YES] | 0.90 | LLM | street='99 Bank Street, 13th Floor' city... |
| business_number | [NO] | 0.70 | - | None |
| contract_id | [NO] | 0.70 | - | None |
| currency | [NO] | 0.80 | LLM | None |
| customer_email | [NO] | 0.70 | - | None |
| customer_fax | [NO] | 0.70 | - | None |
| customer_id | [NO] | 0.70 | - | None |
| customer_name | [YES] | 0.96 | DI | CATSA/ACTSA |
| customer_phone | [NO] | 0.70 | - | None |
| delivery_date | [NO] | 0.70 | - | None |
| deposit_amount | [YES] | 0.90 | LLM | 0.00 |
| discount_amount | [YES] | 0.90 | LLM | 0.00 |
| due_date | [YES] | 0.96 | DI | 2025-10-25 |
| entity | [NO] | 0.70 | - | None |
| gst_amount | [YES] | 0.90 | LLM | 2.84 |
| gst_number | [YES] | 0.90 | LLM | 139666721 |
| gst_rate | [YES] | 0.90 | LLM | 5.00 |
| handling_fee | [NO] | 0.70 | - | None |
| hst_amount | [NO] | 0.70 | - | None |
| hst_rate | [NO] | 0.70 | - | None |
| invoice_date | [YES] | 0.96 | DI | 2025-09-25 |
| invoice_number | [YES] | 0.96 | DI | 4202092525 |
| invoice_type | [NO] | 0.70 | - | None |
| payment_due_upon | [NO] | 0.70 | - | None |
| payment_method | [NO] | 0.70 | - | None |
| payment_terms | [YES] | 0.94 | DI | Net 30 |
| period_end | [NO] | 0.70 | - | None |
| period_start | [YES] | 0.75 | LLM | 2025-09-25 |
| po_number | [YES] | 0.96 | DI | 1001401 |
| pst_amount | [YES] | 0.90 | LLM | 3.97 |
| pst_number | [YES] | 0.90 | LLM | 1001401 |
| pst_rate | [YES] | 0.90 | LLM | 7.00 |
| qst_amount | [NO] | 0.70 | - | None |
| qst_number | [NO] | 0.70 | - | None |
| qst_rate | [NO] | 0.70 | - | None |
| reference_number | [YES] | 0.90 | LLM | 4202092525 |
| remit_to_address | [YES] | 0.90 | LLM | street='Unit A - 111 Cole Avenue' city='... |
| remit_to_name | [YES] | 0.90 | LLM | Accurate Fire & Safety Ltd. |
| shipping_amount | [YES] | 0.90 | LLM | 0.00 |
| shipping_date | [NO] | 0.70 | - | None |
| standing_offer_number | [NO] | 0.70 | - | None |
| subtotal | [YES] | 0.95 | DI | 56.75 |
| tax_amount | [YES] | 0.95 | DI | 6.81 |
| tax_breakdown | [NO] | N/A | - | None |
| tax_registration_number | [YES] | 0.90 | LLM | 139666721 |
| total_amount | [YES] | 0.95 | DI | 63.56 |
| vendor_address | [YES] | 0.90 | LLM | street='Unit A - 111 Cole Avenue' city='... |
| vendor_email | [YES] | 0.90 | LLM | info@accuratefire.ca |
| vendor_fax | [YES] | 0.90 | LLM | (204) 667-1483 |
| vendor_id | [NO] | 0.70 | - | None |
| vendor_name | [YES] | 0.88 | DI | ACCURATE
fire & safety ltd. |
| vendor_phone | [YES] | 0.90 | LLM | (204) 668-9930 |
| vendor_website | [NO] | 0.70 | - | None |

---

**Report End**