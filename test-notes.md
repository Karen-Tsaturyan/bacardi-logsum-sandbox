# Test Notes — Kata 5.W.4

## Isolation method
**Fresh session** - test author did not see `src/logsum.py`

## Test results
- **16 passing** - Core functionality correct
- **2 failing** - Edge cases revealed

## Test failures and decisions

### 1. `test_cli_with_default_output`
**Failure:** Module not found when test changes working directory
**Decision:** **Test bug** - environment setup issue, not spec violation
**Action:** Skip or fix test to use absolute paths (not a spec gap)

### 2. `test_exit_code_runtime_error_malformed_csv`
**Failure:** Implementation returns exit code 0 for malformed CSV, spec requires 1
**Decision:** **Implementation bug** - violates spec.md edge case section
**Action:** Fix implementation to catch CSV parsing errors and exit(1)
**Spec reference:** "Duplicate headers or malformed CSV → Exit with error code 1"

## Key finding
Independent testing caught a **missing error handler** the implementation session overlooked. The code handles valid CSV edge cases (empty input, missing levels) but doesn't validate CSV structure itself. This is exactly why tests should be written by a separate session that hasn't seen the code.

---

**Signed:** Karen Tsaturyan – 2026-06-30