# Invoice Fields Comparison: DEMO vs Vanilla

This document compares the invoice fields between the FinDataExtractorDEMO
and FinDataExtractorVanilla projects.

## Canonical Fields Comparison

- **DEMO Fields**: 112
- **Vanilla Fields**: 112
- **Common Fields**: 112
- **Only in DEMO**: 0
- **Only in Vanilla**: 0

### Field Differences (Common Fields with Different Values)

#### bill_to_address.city
- **Type**:
  - DEMO: `string, null`
  - Vanilla: `string`

#### bill_to_address.country
- **Type**:
  - DEMO: `string, null`
  - Vanilla: `string`

#### bill_to_address.postal_code
- **Type**:
  - DEMO: `string, null`
  - Vanilla: `string`

#### bill_to_address.province
- **Type**:
  - DEMO: `string, null`
  - Vanilla: `string`

#### bill_to_address.street
- **Type**:
  - DEMO: `string, null`
  - Vanilla: `string`

#### line_items[].airport_code
- **Type**:
  - DEMO: `string, null`
  - Vanilla: `string`

#### line_items[].confidence
- **Type**:
  - DEMO: `unknown`
  - Vanilla: `number`

#### line_items[].cost_centre_code
- **Type**:
  - DEMO: `string, null`
  - Vanilla: `string`

#### line_items[].project_code
- **Type**:
  - DEMO: `string, null`
  - Vanilla: `string`

#### line_items[].region_code
- **Type**:
  - DEMO: `string, null`
  - Vanilla: `string`

#### line_items[].unit_of_measure
- **Type**:
  - DEMO: `string, null`
  - Vanilla: `string`

#### remit_to_address.city
- **Type**:
  - DEMO: `string, null`
  - Vanilla: `string`

#### remit_to_address.country
- **Type**:
  - DEMO: `string, null`
  - Vanilla: `string`

#### remit_to_address.postal_code
- **Type**:
  - DEMO: `string, null`
  - Vanilla: `string`

#### remit_to_address.province
- **Type**:
  - DEMO: `string, null`
  - Vanilla: `string`

#### remit_to_address.street
- **Type**:
  - DEMO: `string, null`
  - Vanilla: `string`

#### vendor_address.city
- **Type**:
  - DEMO: `string, null`
  - Vanilla: `string`

#### vendor_address.country
- **Type**:
  - DEMO: `string, null`
  - Vanilla: `string`

#### vendor_address.postal_code
- **Type**:
  - DEMO: `string, null`
  - Vanilla: `string`

#### vendor_address.province
- **Type**:
  - DEMO: `string, null`
  - Vanilla: `string`

*... and 1 more differences*

## UI Fields Comparison

- **DEMO Fields**: 24
- **Vanilla Fields**: 24
- **Common Fields**: 24
- **Only in DEMO**: 0
- **Only in Vanilla**: 0

### Field Differences

✓ **No differences found**: All UI fields are identical between DEMO and Vanilla projects.

## Summary

### Canonical Fields

✓ **Identical**: Both projects have the same canonical fields.

### UI Fields

✓ **Identical**: Both projects have the same UI fields.
