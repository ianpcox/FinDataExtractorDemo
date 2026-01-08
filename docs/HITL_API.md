# HITL (Human-in-the-Loop) API Documentation

## Overview

The HITL API provides endpoints for human validation and correction of extracted invoice data. It displays field-level confidence scores and allows users to validate, correct, and approve invoices.

## Endpoints

### 1. Get Invoice for Validation

**GET** `/api/hitl/invoice/{invoice_id}`

Retrieve invoice data with field-level confidence scores for human review.

**Response:**
```json
{
  "invoice_id": "uuid",
  "status": "extracted",
  "file_name": "invoice.pdf",
  "extraction_confidence": 0.85,
  "fields": {
    "invoice_number": {
      "value": "INV-12345",
      "confidence": 0.95,
      "validated": false
    },
    "invoice_date": {
      "value": "2024-01-15",
      "confidence": 0.90,
      "validated": false
    },
    "vendor_name": {
      "value": "Acme Corp",
      "confidence": 0.85,
      "validated": false
    },
    "total_amount": {
      "value": 1500.00,
      "confidence": 0.88,
      "validated": false
    }
  },
  "line_items": [
    {
      "line_number": 1,
      "description": "Item A",
      "amount": 100.00,
      "confidence": 0.90,
      "validated": false
    }
  ]
}
```

### 2. Validate Invoice

**POST** `/api/hitl/invoice/validate`

Submit validation and corrections for an invoice.

**Request:**
```json
{
  "invoice_id": "uuid",
  "field_validations": [
    {
      "field_name": "vendor_name",
      "value": "Acme Corp",
      "confidence": 0.85,
      "validated": true,
      "corrected_value": "Acme Corporation",
      "validation_notes": "Corrected company name"
    }
  ],
  "line_item_validations": [
    {
      "line_number": 1,
      "validated": true,
      "corrections": {
        "description": "Item A - Updated"
      }
    }
  ],
  "overall_validation_status": "validated",
  "validation_notes": "All fields validated",
  "reviewer": "john.doe"
}
```

**Response:**
```json
{
  "success": true,
  "invoice_id": "uuid",
  "validation_status": "validated",
  "message": "Invoice validation completed successfully"
}
```

### 3. Get Invoice PDF

**GET** `/api/hitl/invoice/{invoice_id}/pdf`

Retrieve the original invoice PDF for display in the UI.

**Response:** PDF file (application/pdf)

### 4. List Invoices for Review

**GET** `/api/hitl/invoices?skip=0&limit=50&status=extracted`

List invoices available for review.

**Query Parameters:**
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum records to return (default: 50)
- `status`: Optional status filter

**Response:**
```json
{
  "invoices": [
    {
      "invoice_id": "uuid",
      "invoice_number": "INV-12345",
      "vendor_name": "Acme Corp",
      "total_amount": 1500.00,
      "currency": "CAD",
      "invoice_date": "2024-01-15",
      "status": "extracted",
      "review_status": "pending_review",
      "extraction_confidence": 0.85,
      "line_item_count": 5
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 50
}
```

## Usage Examples

### Python Client

```python
import requests

# Get invoice for validation
response = requests.get(f"{API_URL}/api/hitl/invoice/{invoice_id}")
invoice_data = response.json()

# Display confidence scores
for field_name, field_data in invoice_data["fields"].items():
    confidence = field_data["confidence"]
    value = field_data["value"]
    print(f"{field_name}: {value} (confidence: {confidence:.0%})")

# Validate invoice
validation_request = {
    "invoice_id": invoice_id,
    "field_validations": [
        {
            "field_name": "vendor_name",
            "value": invoice_data["fields"]["vendor_name"]["value"],
            "confidence": invoice_data["fields"]["vendor_name"]["confidence"],
            "validated": True,
            "corrected_value": "Corrected Vendor Name"
        }
    ],
    "overall_validation_status": "validated",
    "reviewer": "user@example.com"
}

response = requests.post(
    f"{API_URL}/api/hitl/invoice/validate",
    json=validation_request
)
```

### JavaScript/TypeScript Client

```typescript
// Get invoice for validation
const response = await fetch(`/api/hitl/invoice/${invoiceId}`);
const invoiceData = await response.json();

// Display confidence indicators
invoiceData.fields.forEach(field => {
  const confidence = field.confidence;
  const indicator = confidence >= 0.9 ? 'high' : 
                    confidence >= 0.7 ? 'medium' : 'low';
  // Display with appropriate color/icon
});

// Validate invoice
const validationRequest = {
  invoice_id: invoiceId,
  field_validations: [
    {
      field_name: 'vendor_name',
      value: invoiceData.fields.vendor_name.value,
      confidence: invoiceData.fields.vendor_name.confidence,
      validated: true,
      corrected_value: 'Corrected Vendor Name'
    }
  ],
  overall_validation_status: 'validated',
  reviewer: 'user@example.com'
};

await fetch('/api/hitl/invoice/validate', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(validationRequest)
});
```

## Field Confidence Mapping

The API maps Document Intelligence field names to invoice model fields:

| Document Intelligence Field | Invoice Model Field | Confidence Key |
|----------------------------|-------------------|----------------|
| InvoiceId | invoice_number | invoice_id |
| InvoiceDate | invoice_date | invoice_date |
| DueDate | due_date | due_date |
| VendorName | vendor_name | vendor_name |
| CustomerName | customer_name | customer_name |
| SubTotal | subtotal | subtotal |
| TotalTax | tax_amount | total_tax |
| InvoiceTotal | total_amount | invoice_total |
| PurchaseOrder | po_number | purchase_order |

## Validation Status Values

- `pending`: Not yet validated
- `validated`: All fields validated and correct
- `needs_review`: Requires additional review
- `reviewed`: Review completed
- `skipped`: Validation skipped

## Related Documentation

- [PDF Overlay Renderer](./PDF_OVERLAY.md)
- [PO Matching](./PO_MATCHING.md)
- [Architecture](./ARCHITECTURE.md)

