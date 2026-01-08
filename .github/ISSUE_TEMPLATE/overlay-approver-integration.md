# Feature: Overlay Renderer - Approver List Integration

## Description
Enhance the PDF overlay renderer to pull approver information from an approver code list/registry instead of only using the invoice's stored approver fields.

## Current State
The overlay renderer currently displays approver information directly from the invoice model fields (`bv_approver`, `fa_approver`, etc.) without additional context like approver codes, departments, or validation.

## Requirements

### 1. Approver Code List/Registry
- Create or integrate an approver code list table/service
- Store approver codes, names, departments, and active status
- Support lookup by code or name
- Track approver metadata (department, role, approval limits)

### 2. Enhanced Overlay Display
- Display approver codes alongside names in the approval box
- Show approver department/role information
- Validate that approvers exist in the registry
- Handle inactive or invalid approvers gracefully

### 3. Data Source Options
- **Option A**: Create new `approver_codes` table in existing database
- **Option B**: Integrate with external approver registry service/API
- **Option C**: Support both (local table with optional external sync)

## Acceptance Criteria
- [ ] Approver code list/registry is accessible to overlay renderer
- [ ] Overlay displays approver codes (e.g., "BV: APP-001 - John Doe (Finance)")
- [ ] Overlay shows approver department when available
- [ ] Invalid/missing approvers are handled gracefully (show code/name if available, fallback to stored value)
- [ ] Documentation updated with approver integration details

## Technical Considerations
- Consider caching approver list for performance
- Support approver lookup by code or name
- Handle approver updates (active/inactive status)
- Consider audit trail for approver lookups

## Related Issues
- See issue: Document Type Recognition and Separate Storage
- See issue: PO Data Integration for Overlay

## Priority
Medium - Enhances overlay functionality but not critical for core workflow

