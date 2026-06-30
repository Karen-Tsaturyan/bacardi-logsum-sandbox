# Repository Questions & Answers

## Question 1: Where is the grouping rule implemented?

### Files Read
- `spec.md` (lines 50-80)
- `src/logsum.py` (lines 1-100)

### Answer
The grouping rule is implemented in two places:

**Specification (spec.md:76-78):**
The spec defines the grouping rule as: *"Group key: `(service, level)`. Each unique combination of service and normalized level creates one summary row."*

**Implementation (src/logsum.py:84-86):**
The code creates the group key by combining service and normalized level:
```python
normalized_level = normalize_level(level)
key = (service, normalized_level)
```

This tuple `(service, normalized_level)` is used as the dictionary key to aggregate events in the `_update_group()` function. The groups dictionary is initialized at `src/logsum.py:42` as a `defaultdict` that stores count, first_seen, and last_seen for each unique group key.

### Citations
- spec.md:76-78 - Grouping rule specification
- src/logsum.py:42 - Groups dictionary initialization
- src/logsum.py:84-86 - Group key creation in `_update_group()`
- src/logsum.py:88-91 - Aggregation logic using the group key

### Could Not Verify
- Nothing. Both specification and implementation are clear and consistent.

---

## Question 2: How is missing level handled?

### Files Read
- `spec.md` (lines 50-80)
- `src/logsum.py` (lines 1-100)
- `tests/test_logsum.py` (lines 65-80, 278-300)

### Answer
Missing or empty levels are mapped to the string `"UNKNOWN"`.

**Specification (spec.md:65):**
The spec states: *"Empty or null level → `UNKNOWN`"*

**Implementation (src/logsum.py:11-13):**
The `normalize_level()` function checks if the level is empty or whitespace-only and returns `'UNKNOWN'`:
```python
if not level or level.strip() == '':
    return 'UNKNOWN'
```

**Test Verification (tests/test_logsum.py:66-75, 295-297):**
The test fixture creates CSV rows with empty level fields:
```csv
2026-06-30T14:00:00Z,,capacity-indicator,No level
```

The test verifies that these events are grouped under level `"UNKNOWN"` (tests/test_logsum.py:295-297):
```python
assert rows[0]["level"] == "UNKNOWN"
assert rows[0]["count"] == "2"
```

This means missing levels don't cause errors—they're preserved in the summary as `UNKNOWN` groups, allowing operators to identify logging issues while still processing valid data.

### Citations
- spec.md:65 - Missing level specification
- src/logsum.py:11-13 - `normalize_level()` handles empty/null levels
- tests/test_logsum.py:71-72 - Test fixture with empty level fields
- tests/test_logsum.py:295-297 - Assertion verifying UNKNOWN mapping

### Could Not Verify
- Nothing. Specification, implementation, and test coverage are all consistent.

---

## Question 3: How do I run tests and CI locally?

### Files Read
- `CLAUDE.md` (lines 1-30)
- `.github/workflows/ci.yml` (lines 1-35)
- Terminal context from provenance-min-count.md

### Answer

**To run tests locally:**

1. **Install pytest** (CLAUDE.md:21 specifies pytest as the testing utility):
   ```bash
   python3 -m pip install pytest
   ```

2. **Run tests with verbose output**:
   ```bash
   python3 -m pytest -v
   ```
   This matches the CI command at `.github/workflows/ci.yml:32`.

**To run linting locally:**

1. **Install ruff** (CLAUDE.md:20 specifies ruff for linting/formatting):
   ```bash
   python3 -m pip install ruff
   ```

2. **Run ruff check**:
   ```bash
   ruff check .
   ```
   Or via Python module:
   ```bash
   python3 -m ruff check .
   ```
   This matches the CI command at `.github/workflows/ci.yml:20`.

**Full CI simulation:**

To replicate the entire CI workflow locally:
```bash
# Lint job
pip install ruff
ruff check .

# Test job
pip install pytest
pytest -v
```

Both jobs run on Python 3.11 in CI (`.github/workflows/ci.yml:16, 27`), though they should work on Python 3.9+ based on observed terminal output.

### Citations
- CLAUDE.md:20 - "ruff for linting/formatting"
- CLAUDE.md:21 - "pytest for testing"
- .github/workflows/ci.yml:16 - Lint job uses Python 3.11
- .github/workflows/ci.yml:19 - "pip install ruff"
- .github/workflows/ci.yml:20 - "ruff check ."
- .github/workflows/ci.yml:27 - Test job uses Python 3.11
- .github/workflows/ci.yml:30 - "pip install pytest"
- .github/workflows/ci.yml:32 - "pytest -v"

### Could Not Verify
- **Python version requirement:** CLAUDE.md:18 mentions Python 3.11, but tests ran successfully on Python 3.9.6 in terminal history. The actual minimum Python version is not documented.
- **Working directory:** CI assumes commands run from repository root, but this is not explicitly documented.
- **Virtual environment setup:** Neither CLAUDE.md nor CI workflow mentions whether to use a virtual environment (recommended but not required).

---

## Verification

### Question 1: Where is the grouping rule implemented?
- **Citation:** src/logsum.py:84-86
- **Verdict:** ✅ Correct
- **Notes:** Verified `_update_group()` creates tuple key `(service, normalized_level)` exactly as specified. Groups dictionary at line 42 uses this key for aggregation. Implementation matches spec.md:76-78 requirement.

### Question 2: How is missing level handled?
- **Citation:** src/logsum.py:11-13
- **Verdict:** ✅ Correct
- **Notes:** Verified `normalize_level()` returns `'UNKNOWN'` for empty/null levels. Test at tests/test_logsum.py:278-297 confirms behavior with empty CSV level fields. Matches spec.md:65 exactly.

### Question 3: How do I run tests and CI locally?
- **Citation:** .github/workflows/ci.yml:19-20, 30-32
- **Verdict:** ✅ Correct
- **Notes:** Verified commands match CI workflow exactly. Both `pytest -v` and `ruff check .` run successfully locally. Commands are properly documented with citations to workflow file.

---

**Compiled by:** Claude Sonnet 4.5
**Date:** 2026-06-30
**Reviewer:** Karen Tsaturyan

**Verified by:** Karen Tsaturyan – 2026-06-30
