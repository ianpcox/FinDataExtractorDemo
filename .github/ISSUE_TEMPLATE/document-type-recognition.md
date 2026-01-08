# Feature: Document Type Recognition and Separate Storage

## Description
Implement document type recognition to automatically classify uploaded documents (Invoice, PO, Receipt, etc.) and route them to appropriate storage containers and databases.

## Current State
The system currently assumes all uploaded documents are invoices and stores them in a single storage location and database.

## Requirements

### 1. Document Type Recognition
- Detect document type during ingestion (Invoice, PO, Receipt, Contract, etc.)
- Use Azure Document Intelligence prebuilt models:
  - `prebuilt-invoice` for invoices
  - `prebuilt-purchaseOrder` for POs
  - `prebuilt-receipt` for receipts
  - Generic layout model for other documents
- Support manual override/correction of document type
- Store document type metadata

### 2. Separate Storage Containers
- Create separate Azure Blob Storage containers for each document type:
  - `invoices-raw` / `invoices-processed`
  - `pos-raw` / `pos-processed`
  - `receipts-raw` / `receipts-processed`
  - `other-raw` / `other-processed`
- Route documents to appropriate container based on type
- Maintain file path references in database

### 3. Separate Databases (Optional)
- **Option A**: Single database with document type tables (invoices, purchase_orders, receipts)
- **Option B**: Separate databases per document type
- **Option C**: Hybrid - shared database with separate schemas
- Consider: Cross-document relationships (invoice -> PO matching)

### 4. Document Type Service
- Create `DocumentTypeRecognizer` service
- Integrate with ingestion pipeline
- Support confidence scoring for document type
- Handle ambiguous documents (multiple possible types)

## Acceptance Criteria
- [ ] Document type is detected during ingestion
- [ ] Documents are routed to appropriate storage container
- [ ] Document type is stored in metadata
- [ ] Support for at least: Invoice, PO, Receipt
- [ ] Manual override/correction of document type
- [ ] Cross-document relationships are maintained (invoice -> PO)
- [ ] Documentation updated with document type architecture

## Technical Considerations
- Azure Document Intelligence model selection
- Storage container naming convention
- Database schema design for multiple document types
- Performance: minimize document analysis calls
- Cost: Document Intelligence API calls per document
- Error handling: unrecognized document types

## Implementation Phases

### Phase 1: Document Type Recognition
- Add document type detection to ingestion service
- Store document type in metadata
- Log unrecognized documents

### Phase 2: Storage Routing
- Create separate storage containers
- Route documents based on type
- Update file handler to support type-based routing

### Phase 3: Database Separation (if needed)
- Design database schema for multiple document types
- Create migration scripts
- Update services to use appropriate tables

### Phase 4: Cross-Document Integration
- Maintain relationships between document types
- Support invoice -> PO matching across databases
- Update overlay renderer to access PO data

## Related Issues
- See issue: PO Data Integration for Overlay
- See issue: Approver List Integration
- See issue: PO Matching Service

## Priority
High - Foundation for multi-document type support and PO integration

