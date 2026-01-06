# Session Summary: Concurrent Extraction Test + P0 Atomic TOCTOU Fix

## Overview

This session implemented two critical P0 reliability improvements:
1. **P0 Atomic TOCTOU Fix:** Eliminated race conditions in `transition_state()` and `update_with_review_version()`
2. **P0/P1 Concurrent Extraction Test:** Created integration test to prove extraction claim atomicity

## Part 1: P0 Atomic TOCTOU Fix ✅ COMPLETE

### Problem Statement
The `update_with_review_version()` method had potential race conditions:
- Manually setting `review_version` in patch dict instead of atomic SQL increment
- Returning `int` instead of `bool` for unclear semantics
- Not adequately sanitizing protected fields

### Solution Applied

**File: `src/services/db_service.py`**

```python
@staticmethod
async def update_with_review_version(
    invoice_id: str,
    patch: dict,
    expected_review_version: int,
    db: Optional[AsyncSession] = None,
) -> bool:
    """Atomic optimistic-locking update using single-statement guarded UPDATE."""
    
    # Sanitize patch: exclude protected fields
    patch = patch.copy()
    patch.pop("id", None)
    patch.pop("created_at", None)
    patch.pop("review_version", None)
    patch.pop("processing_state", None)  # HITL should not change processing state
    
    # Atomic UPDATE with review_version increment in same statement
    stmt = (
        update(InvoiceDB)
        .where(
            InvoiceDB.id == invoice_id,
            InvoiceDB.review_version == expected_review_version,
        )
        .values(
            **valid_patch,
            review_version=InvoiceDB.review_version + 1,  # ← Atomic increment
            updated_at=datetime.utcnow(),
        )
    )
    result = await session.execute(stmt)
    await session.commit()
    
    return (result.rowcount or 0) > 0  # True if updated, False if stale
```

### Key Improvements

1. **Atomic Increment:** Uses SQLAlchemy expression `InvoiceDB.review_version + 1` instead of manually setting in patch
2. **Boolean Return:** Returns `bool` for clearer semantics (True=success, False=stale write)
3. **Protected Fields:** Explicitly excludes `id`, `created_at`, `review_version`, `processing_state` from patches
4. **No TOCTOU:** Single UPDATE statement with no prior SELECT

### Test Results

**All 12 atomic update and concurrency tests passing:**
```
test_transition_state_is_atomic ✅
test_update_with_review_version_is_atomic ✅
test_concurrent_review_version_updates_one_wins ✅
test_transition_state_prevents_invalid_transitions ✅
test_update_with_review_version_increments_correctly ✅
test_transition_state_with_multiple_valid_from_states ✅
test_update_with_review_version_handles_complex_patch ✅
test_atomic_update_no_lost_updates ✅
test_review_version_optimistic_lock ✅
test_claim_for_extraction ✅
test_set_extraction_result_requires_processing_state ✅
test_invalid_transition_processing_to_validated ✅
```

### Files Modified

- `src/services/db_service.py`: Updated `update_with_review_version()` implementation
- `api/routes/hitl.py`: Updated caller to use boolean return
- `tests/unit/test_atomic_updates.py`: Updated 8 test methods
- `tests/unit/test_concurrency.py`: Updated 4 test methods
- `P0_ATOMIC_TOCTOU_FIX_VERIFICATION.md`: Comprehensive verification document

## Part 2: Concurrent Extraction Integration Test 🚧 IN PROGRESS

### Problem Statement
Need to prove that concurrent extraction requests are safe and deterministic:
1. Exactly ONE request successfully claims/processes the invoice
2. All other concurrent requests return 409 conflict
3. Final DB state is EXTRACTED (never stuck in PROCESSING)

### Solution Approach

**File: `tests/conftest.py`**

Added `async_client` fixture for true async concurrency:
```python
@pytest.fixture(scope="function")
async def async_client(db_engine):
    """
    Create an async httpx client for true concurrent ASGI requests.
    Uses httpx.AsyncClient with ASGI transport for real concurrent behavior.
    """
    import httpx
    from api.main import app
    
    # Override get_db dependency to use test DB
    async def override_get_db():
        async with TestingSessionLocal() as session:
            yield session
    
    app.dependency_overrides[get_db] = override_get_db
    
    # Create async client using ASGI transport
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client
    
    app.dependency_overrides.clear()
```

**File: `tests/integration/test_concurrent_extraction.py`**

Created comprehensive concurrent extraction test:
- `StubExtractionService`: Deterministic extraction stub with sleep delays
- `test_concurrent_extraction_claims_once`: Core concurrency test
- `test_concurrent_extraction_repeatability`: Stability verification

### Current Status: Debugging Required

**Issue:** All 5 concurrent requests return 409 conflict (none succeed).

**Possible Causes:**
1. Invoice not properly seeded in test DB
2. Transaction isolation between `db_session` and `DatabaseService.claim_for_extraction()`
3. `AsyncSessionLocal` override not taking effect properly

**Files Created:**
- `tests/conftest.py`: Added `async_client` fixture
- `tests/integration/test_concurrent_extraction.py`: Full test implementation (needs debugging)

### Next Steps for Concurrent Extraction Test

1. **Debug DB Isolation:** Add logging to understand why all claims fail
2. **Verify Seeding:** Ensure invoice is visible to all concurrent requests
3. **Session Management:** Verify `AsyncSessionLocal` override is working
4. **Simplify First:** Test single claim works before testing concurrency

## Documentation Created

1. **P0_ATOMIC_TOCTOU_FIX_VERIFICATION.md** ✅
   - Complete verification of atomic UPDATE fix
   - All test results documented
   - Acceptance criteria met

2. **SESSION_SUMMARY_CONCURRENT_EXTRACTION_TEST.md** (this file)
   - Session overview
   - Part 1 (Atomic TOCTOU) complete
   - Part 2 (Concurrent Extraction Test) in progress

## Acceptance Criteria

### Part 1: P0 Atomic TOCTOU Fix ✅ COMPLETE

- [x] No SELECT-then-write remains in either function
- [x] Both functions rely solely on guarded UPDATE + rowcount
- [x] `update_with_review_version()` increments `review_version` in same statement
- [x] `update_with_review_version()` returns `bool` (not `int`)
- [x] Protected fields excluded from patches
- [x] Caller treats `False` as 409 STALE_WRITE
- [x] All 12 atomic update and concurrency tests passing
- [x] No linter errors

### Part 2: Concurrent Extraction Test 🚧 NEEDS DEBUG

- [ ] Test uses `httpx.AsyncClient` + `asyncio.gather` for true concurrency ✅ (implemented)
- [ ] Extraction is stubbed (no network, deterministic) ✅ (implemented)
- [ ] Exactly one request succeeds; others conflict ❌ (all fail - needs fix)
- [ ] Final state is EXTRACTED ❌ (not reached)
- [ ] Test is stable on repeated runs ⏸️ (not yet tested)

## Commands Run

```bash
# Atomic TOCTOU fix verification
pytest tests/unit/test_atomic_updates.py tests/unit/test_concurrency.py -v --tb=short -q
# Result: 12/12 tests passing ✅

# Concurrent extraction test (debugging needed)
pytest tests/integration/test_concurrent_extraction.py::TestConcurrentExtraction::test_concurrent_extraction_claims_once -v --tb=short -x
# Result: All requests return 409 (needs debugging)
```

## Technical Debt / Follow-up

1. **Concurrent Extraction Test:** Debug and fix DB isolation issue
2. **Coverage:** Current coverage is 27% (below 70% threshold) - expected for unit test-only run
3. **Documentation:** Once concurrent test passes, update verification docs

## Summary

✅ **Part 1 Complete:** P0 Atomic TOCTOU fix successfully implemented and verified
🚧 **Part 2 In Progress:** Concurrent extraction test framework in place, needs debugging

The atomic UPDATE fix is production-ready and eliminates race conditions in optimistic locking. The concurrent extraction test needs DB isolation debugging before it can verify end-to-end extraction safety.

