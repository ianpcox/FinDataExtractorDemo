# P0 Concurrency Correctness: Atomic UPDATE Verification

## Summary

Successfully eliminated TOCTOU (Time-Of-Check-Time-Of-Use) races in `transition_state()` and `update_with_review_version()` by converting them to single-statement guarded UPDATEs with no prior SELECT operations.

## Changes Applied

### 1. `DatabaseService.update_with_review_version()` (src/services/db_service.py)

**Before:**
- Manually set `review_version` in patch dict: `patch["review_version"] = expected_review_version + 1`
- Returned `int` (rowcount)
- Did not sanitize protected fields adequately

**After:**
```python
@staticmethod
async def update_with_review_version(
    invoice_id: str,
    patch: dict,
    expected_review_version: int,
    db: Optional[AsyncSession] = None,
) -> bool:
    """
    Atomic optimistic-locking update using single-statement guarded UPDATE.
    Returns True if updated, False if stale write.
    """
    # Sanitize patch: never allow these fields to be patched
    patch = patch.copy()
    patch.pop("id", None)
    patch.pop("created_at", None)
    patch.pop("review_version", None)
    patch.pop("processing_state", None)  # HITL should not change processing state
    
    # Use atomic UPDATE with WHERE clause (no SELECT-then-UPDATE race)
    # Increment review_version in the same statement
    stmt = (
        update(InvoiceDB)
        .where(
            InvoiceDB.id == invoice_id,
            InvoiceDB.review_version == expected_review_version,
        )
        .values(
            **valid_patch,
            review_version=InvoiceDB.review_version + 1,  # Atomic increment
            updated_at=datetime.utcnow(),
        )
    )
    result = await session.execute(stmt)
    await session.commit()
    
    return (result.rowcount or 0) > 0  # True if updated, False if stale
```

**Key Improvements:**
- ✅ Uses SQLAlchemy expression `InvoiceDB.review_version + 1` for atomic increment
- ✅ Returns `bool` instead of `int` for clearer semantics
- ✅ Sanitizes protected fields: `id`, `created_at`, `review_version`, `processing_state`
- ✅ Single atomic UPDATE statement - no TOCTOU window

### 2. `DatabaseService.transition_state()` (src/services/db_service.py)

**Status:** Already atomic! No changes required.

The existing implementation correctly uses:
```python
stmt = (
    update(InvoiceDB)
    .where(
        InvoiceDB.id == invoice_id,
        InvoiceDB.processing_state.in_(list(from_states)),
    )
    .values(
        processing_state=to_state,
        status=to_state,
        updated_at=datetime.utcnow(),
    )
)
result = await session.execute(stmt)
await session.commit()

return (result.rowcount or 0) > 0
```

**Note:** The method does call `get_state()` on failure when `error_on_invalid=True`, but this is **after** the atomic UPDATE has already failed, purely for error reporting. This does not introduce a race.

### 3. Caller Updates (api/routes/hitl.py)

**Before:**
```python
rows = await DatabaseService.update_with_review_version(...)
if rows == 0:
    # Handle stale write
```

**After:**
```python
success = await DatabaseService.update_with_review_version(...)
if not success:
    # Handle stale write - return HTTP 409
```

### 4. Test Updates

Updated all tests to use boolean assertions:
- `test_atomic_updates.py`: All 8 tests updated and passing
- `test_concurrency.py`: Tests updated and passing
- `test_update_with_review_version_handles_complex_patch`: Now verifies that protected fields (`processing_state`, `id`, `created_at`, `review_version`) are correctly excluded from patches

## Test Results

```
tests/unit/test_atomic_updates.py::TestAtomicUpdates::test_transition_state_is_atomic PASSED
tests/unit/test_atomic_updates.py::TestAtomicUpdates::test_update_with_review_version_is_atomic PASSED
tests/unit/test_atomic_updates.py::TestAtomicUpdates::test_concurrent_review_version_updates_one_wins PASSED
tests/unit/test_atomic_updates.py::TestAtomicUpdates::test_transition_state_prevents_invalid_transitions PASSED
tests/unit/test_atomic_updates.py::TestAtomicUpdates::test_update_with_review_version_increments_correctly PASSED
tests/unit/test_atomic_updates.py::TestAtomicUpdates::test_transition_state_with_multiple_valid_from_states PASSED
tests/unit/test_atomic_updates.py::TestAtomicUpdates::test_update_with_review_version_handles_complex_patch PASSED
tests/unit/test_atomic_updates.py::TestAtomicUpdates::test_atomic_update_no_lost_updates PASSED
tests/unit/test_concurrency.py::test_review_version_optimistic_lock PASSED
tests/unit/test_concurrency.py::test_claim_for_extraction PASSED
tests/unit/test_concurrency.py::test_set_extraction_result_requires_processing_state PASSED
tests/unit/test_concurrency.py::test_invalid_transition_processing_to_validated PASSED

12/12 tests passing ✅
```

## Concurrency Properties Verified

### 1. ✅ Single-Statement Atomicity
- No SELECT-then-UPDATE pattern remains
- All updates use guarded UPDATE with WHERE clause
- Rowcount determines success/failure

### 2. ✅ Optimistic Locking Works
- `test_update_with_review_version_is_atomic`: First update succeeds, second with stale version fails
- `test_concurrent_review_version_updates_one_wins`: Two concurrent updates, exactly one succeeds
- `test_atomic_update_no_lost_updates`: Sequential updates with correct versions all succeed

### 3. ✅ State Transitions Are Guarded
- `test_transition_state_is_atomic`: PENDING→PROCESSING transition atomic
- `test_transition_state_with_multiple_valid_from_states`: Multiple valid from_states handled correctly
- `test_transition_state_prevents_invalid_transitions`: Invalid transitions properly rejected

### 4. ✅ Protected Fields Cannot Be Overwritten
- `test_update_with_review_version_handles_complex_patch`: Verifies that:
  - `id` cannot be changed
  - `created_at` cannot be changed
  - `review_version` is incremented by the method, not set from patch
  - `processing_state` cannot be changed via HITL updates

### 5. ✅ API Surfaces Conflicts Correctly
- HITL validate endpoint returns HTTP 409 with `error_code: "STALE_WRITE"` on conflicts
- Includes `current_review_version` for client reconciliation

## Acceptance Criteria Met

- [x] No SELECT-then-write remains in either function
- [x] Both functions rely solely on guarded UPDATE + rowcount
- [x] `update_with_review_version()` increments `review_version` in same statement
- [x] `update_with_review_version()` returns `bool` (not `int`)
- [x] Protected fields (`id`, `created_at`, `review_version`, `processing_state`) excluded from patches
- [x] Caller treats `False` from `update_with_review_version()` as 409 STALE_WRITE
- [x] Concurrency tests prove only one writer "wins"
- [x] All 12 atomic update and concurrency tests passing

## Security & Correctness Guarantees

1. **No Lost Updates:** Two concurrent writers cannot both succeed. Exactly one wins, the other gets `False`.

2. **No Identity Corruption:** `id` cannot be changed via optimistic update.

3. **No Audit Trail Corruption:** `created_at` cannot be overwritten.

4. **No Version Manipulation:** `review_version` cannot be set from patch; always incremented atomically.

5. **No State Bypass:** HITL updates cannot change `processing_state` (extraction/validation state machine is separate).

## Files Modified

- `src/services/db_service.py`: Updated `update_with_review_version()` to return bool and use atomic increment
- `api/routes/hitl.py`: Updated caller to use boolean return
- `tests/unit/test_atomic_updates.py`: Updated all assertions to use booleans
- `tests/unit/test_concurrency.py`: Updated assertions to use booleans

## Next Steps

The concurrent extraction integration test (`test_concurrent_extraction.py`) can now proceed with confidence that the underlying database operations are truly atomic and race-free.

