# Requirements - FinDataExtractor Vanilla

## Invoice Data Structure

### Header Fields (Required for all invoices)
- Vendor ID / name
- Invoice number, date
- Currency
- Customer / entity
- Contract ID / PO # (if available)
- Period covered (start / end, if present)
- Subtotal, tax breakdown (by tax type) and total

### Line Items (Generic structure)
- Description
- Quantity, UoM (Unit of Measure)
- Unit price
- Line total
- Tax rate(s) and tax amount(s)
- Optional: project/region/airport/cost centre codes where explicitly present

## Extensions for Specific Patterns

### Shift-based Services (Sanitization Pattern)
Additional structured fields on each invoice package:
- `service_location` (e.g., site/branch/airport)
- `billing_period_start/end`
- `shift_rate`
- `total_shifts_billed`
- Optionally: `min_shifts_per_period` (if present in text)

On supporting timesheets, extract:
- Rows of `{date, worker_name, shift_number, time_in, time_out}`
- Representative name, signature presence, comments

### Per-diem Travel / Training (Travel Pattern)
Additional structured fields per line:
- `traveller_id` (LMS or employee #)
- `traveller_name`
- `programme_or_course_code`
- `work_location` (home site)
- `destination_location` (training site)
- `travel_from_date`, `travel_to_date`
- `training_start_date`, `training_end_date` (if present)
- `travel_days` (derived)
- `daily_rate`
- `line_total` (validation: days × daily_rate)

## Approval Workflow

### Stage 1: Business Verification (BV)
**Actor:** Operational/contract owner (e.g., site manager, training manager)

**Sees:**
- Invoice header and lines
- Key validation results and exceptions
- Summarised supporting evidence (e.g., total shifts from timesheets, list of travellers and dates)

**Can:**
- Correct extracted fields (within limits)
- Override specific warnings/blocks with reason
- Approve or reject

### Stage 2: Financial Authorization (FA)
**Actor:** Finance/AP or budget holder

**Sees:**
- Same invoice summary
- Result of Stage 1 (who approved, what corrections or overrides they made)
- GL coding, tax breakdown (recoverable vs non-recoverable), budget/commitment checks

**Can:**
- Adjust coding (GL, cost centre, project), if allowed
- Approve or reject payment

**Note:** For now, focus on appending data to raw document and saving as marked-up PDF. Approval UI will be determined later.

## Marked-Up PDF

The marked-up PDF should include:
- All header fields
- All line items
- Extensions (if applicable - ShiftService or PerDiemTravel)
- This data should be overlaid on the original invoice PDF

## HITL (Human-in-the-Loop) UI

**Requirements:**
- Display extracted invoice data
- Show PDF alongside extracted fields
- Display confidence values per field
- Allow user to validate/correct extracted data
- Support approval workflow (BV and FA stages)

**Technology:** Streamlit suggested as lightweight frontend framework

## ERP Integration

**Format:** TBD (client pending)
**Assumption:** At minimum, extracted invoice data structure
**Output:** Staged data ready for MS Dynamics Great Plains integration (batch or direct)

