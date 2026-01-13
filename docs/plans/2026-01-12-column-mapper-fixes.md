# Column Mapper Cache and Auto-Detection Fixes

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix two bugs in column mapping: case-sensitive cache path hashing causing cache misses on Windows, and auto-detection preferring longer column names over exact matches.

**Architecture:** Normalize file paths to lowercase before hashing for cache keys. Update column auto-detection to prefer shorter/exact matches when multiple columns match a pattern.

**Tech Stack:** Python, pathlib, hashlib

---

## Task 1: Write Failing Test for Case-Insensitive Cache Lookup

**Files:**
- Create: `tests/unit/test_column_mapper_cache.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_column_mapper_cache.py
"""Tests for ColumnMapper cache path normalization."""

import pytest
from pathlib import Path
from unittest.mock import patch
import tempfile
import os

from src.core.column_mapper import ColumnMapper
from src.core.models import ColumnMapping


class TestCachePathNormalization:
    """Tests for case-insensitive cache path handling on Windows."""

    def test_same_file_different_case_uses_same_cache(self, tmp_path):
        """Loading same file with different path casing should use same cache."""
        # Create a test mapping
        mapping = ColumnMapping(
            ticker="ticker",
            date="date",
            time="time",
            gain_pct="gain_pct",
            mae_pct="mae_pct",
        )

        mapper = ColumnMapper(cache_dir=tmp_path)

        # Save with uppercase drive letter
        uppercase_path = Path("C:/Users/Test/file.xlsx")
        mapper.save_mapping(uppercase_path, mapping, "Sheet1")

        # Load with lowercase drive letter - should find the same cache
        lowercase_path = Path("c:/Users/Test/file.xlsx")
        loaded = mapper.load_mapping(lowercase_path, "Sheet1")

        assert loaded is not None, "Cache miss due to path case sensitivity"
        assert loaded.gain_pct == "gain_pct"

    def test_hash_is_case_insensitive(self):
        """Cache hash should be identical regardless of path casing."""
        mapper = ColumnMapper()

        hash1 = mapper._get_file_hash(Path("C:/Users/Test/file.xlsx"), "Sheet1")
        hash2 = mapper._get_file_hash(Path("c:/Users/Test/file.xlsx"), "Sheet1")

        assert hash1 == hash2, f"Hashes differ: {hash1} vs {hash2}"

    def test_hash_normalizes_backslashes(self):
        """Cache hash should normalize path separators."""
        mapper = ColumnMapper()

        hash1 = mapper._get_file_hash(Path("C:/Users/Test/file.xlsx"), "Sheet1")
        hash2 = mapper._get_file_hash(Path("C:\\Users\\Test\\file.xlsx"), "Sheet1")

        assert hash1 == hash2, f"Hashes differ: {hash1} vs {hash2}"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_column_mapper_cache.py -v`
Expected: FAIL with "Cache miss due to path case sensitivity" or hash mismatch

**Step 3: Implement the fix in ColumnMapper**

Modify `src/core/column_mapper.py`:

```python
def _get_file_hash(self, file_path: Path, sheet: str | None = None) -> str:
    """Generate hash for cache key.

    Args:
        file_path: Path to the data file.
        sheet: Optional sheet name for Excel files.

    Returns:
        MD5 hash string.
    """
    # Normalize path: resolve to absolute, convert to lowercase for case-insensitive matching
    # Use as_posix() to normalize separators, then lowercase for Windows compatibility
    normalized_path = file_path.resolve().as_posix().lower()
    key = normalized_path + (sheet or "")
    return hashlib.md5(key.encode()).hexdigest()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_column_mapper_cache.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/test_column_mapper_cache.py src/core/column_mapper.py
git commit -m "$(cat <<'EOF'
fix: normalize cache path to be case-insensitive on Windows

The cache key hash now uses lowercase, forward-slash normalized paths
to ensure the same file loaded with different path casings (C:\ vs c:\)
uses the same cached column mapping.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Write Failing Test for Column Auto-Detection Priority

**Files:**
- Modify: `tests/unit/test_column_mapper.py`

**Step 1: Write the failing test**

```python
# Add to tests/unit/test_column_mapper.py

class TestAutoDetectionPriority:
    """Tests for column auto-detection preferring exact/shorter matches."""

    def test_prefers_exact_match_over_substring(self):
        """Should prefer 'gain_pct' over 'gain_pct_from_low'."""
        mapper = ColumnMapper()
        columns = [
            "ticker",
            "date",
            "time",
            "gain_pct_from_low",  # Longer, appears first
            "gain_pct",  # Exact match, appears second
            "mae_pct",
        ]

        result = mapper.auto_detect(columns)

        assert result.mapping is not None
        assert result.mapping.gain_pct == "gain_pct", (
            f"Expected 'gain_pct' but got '{result.mapping.gain_pct}'. "
            "Auto-detection should prefer shorter/exact matches."
        )

    def test_prefers_shorter_match_when_both_contain_pattern(self):
        """Should prefer shorter column name when multiple contain pattern."""
        mapper = ColumnMapper()
        columns = [
            "ticker",
            "date",
            "trigger_time_et",  # Longer
            "time",  # Shorter, exact
            "gain_pct",
            "mae_pct",
        ]

        result = mapper.auto_detect(columns)

        assert result.mapping is not None
        assert result.mapping.time == "time", (
            f"Expected 'time' but got '{result.mapping.time}'. "
            "Auto-detection should prefer shorter matches."
        )

    def test_exact_pattern_match_takes_priority(self):
        """Exact pattern match should beat substring match."""
        mapper = ColumnMapper()
        columns = [
            "my_ticker_symbol",  # Contains 'ticker'
            "ticker",  # Exact match
            "date",
            "time",
            "gain_pct",
            "mae_pct",
        ]

        result = mapper.auto_detect(columns)

        assert result.mapping is not None
        assert result.mapping.ticker == "ticker"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_column_mapper.py::TestAutoDetectionPriority -v`
Expected: FAIL with "Expected 'gain_pct' but got 'gain_pct_from_low'"

**Step 3: Implement the fix**

Modify `src/core/column_mapper.py` `_match_column` method:

```python
def _match_column(self, columns: list[str], patterns: list[str]) -> tuple[str | None, str]:
    """Match a column using case-insensitive matching with priority rules.

    Priority order:
    1. Exact match (case-insensitive)
    2. Substring match - prefer shorter column names
    3. Reverse substring match (guessed)

    Args:
        columns: List of column names to search.
        patterns: List of patterns to match against.

    Returns:
        Tuple of (matched_column_name, status).
        Status is "detected" for exact/substring match, "guessed" for partial,
        "missing" if no match found.
    """
    columns_lower = {col.lower(): col for col in columns}

    # First pass: exact match (case-insensitive) - highest priority
    for pattern in patterns:
        if pattern.lower() in columns_lower:
            return columns_lower[pattern.lower()], "detected"

    # Second pass: substring match (pattern appears in column name)
    # Collect all matches, then prefer shorter column names
    substring_matches: list[str] = []
    for pattern in patterns:
        for col_lower, col_original in columns_lower.items():
            if pattern.lower() in col_lower:
                substring_matches.append(col_original)

    if substring_matches:
        # Sort by length (prefer shorter names) then alphabetically for consistency
        substring_matches.sort(key=lambda x: (len(x), x.lower()))
        return substring_matches[0], "detected"

    # Third pass: column name appears in pattern (guessed) - lowest priority
    for pattern in patterns:
        for col_lower, col_original in columns_lower.items():
            if col_lower in pattern.lower():
                return col_original, "guessed"

    return None, "missing"
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_column_mapper.py::TestAutoDetectionPriority -v`
Expected: PASS

**Step 5: Run full column mapper test suite**

Run: `pytest tests/unit/test_column_mapper.py -v`
Expected: PASS (no regressions)

**Step 6: Commit**

```bash
git add src/core/column_mapper.py tests/unit/test_column_mapper.py
git commit -m "$(cat <<'EOF'
fix: auto-detection prefers shorter/exact column name matches

When multiple columns match a pattern (e.g., 'gain_pct' and
'gain_pct_from_low' both contain 'gain'), the auto-detection now
prefers the shorter column name. This fixes incorrect column
selection when similar column names exist.

Priority order:
1. Exact pattern match (case-insensitive)
2. Substring match, preferring shorter column names
3. Reverse substring match (guessed)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Clean Up Stale Cache Files

**Files:**
- Modify: `.lumen_cache/` (manual cleanup)

**Step 1: Identify stale cache entries**

After the path normalization fix, old cache files with non-normalized paths become orphaned. The fix uses normalized (lowercase, forward-slash) paths, so old caches won't be found.

**Step 2: Run migration script**

```python
# Run this once to migrate existing caches
import hashlib
import json
from pathlib import Path

cache_dir = Path(".lumen_cache")
migrated = 0

for cache_file in cache_dir.glob("*_mappings.json"):
    # Old caches are orphaned - we can't easily determine their original paths
    # Best approach: let users re-configure on next load
    print(f"Found cache: {cache_file.name}")

# Optionally: delete all mapping caches to force re-detection
# for cache_file in cache_dir.glob("*_mappings.json"):
#     cache_file.unlink()
#     print(f"Deleted: {cache_file.name}")
```

**Step 3: Document behavior**

Users may need to re-select columns on first load after this update. Add a note to release notes.

**Step 4: Commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
chore: document cache migration after path normalization fix

Users may need to re-select column mappings on first load after
updating, as the cache key format has changed.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Integration Test with Real Data Pattern

**Files:**
- Create: `tests/integration/test_column_detection_edge_cases.py`

**Step 1: Write integration test**

```python
# tests/integration/test_column_detection_edge_cases.py
"""Integration tests for column detection edge cases."""

import pandas as pd
import pytest
from pathlib import Path

from src.core.column_mapper import ColumnMapper
from src.core.metrics import MetricsCalculator


class TestColumnDetectionWithSimilarNames:
    """Test auto-detection when columns have similar names."""

    def test_gain_pct_vs_gain_pct_from_low(self):
        """Should select 'gain_pct' over 'gain_pct_from_low'."""
        # Simulate the problematic column structure
        columns = [
            "ticker",
            "date",
            "trigger_time_et",
            "gain_pct_from_low",  # Wrong - huge values
            "gain_pct",  # Correct - decimal percentages
            "mae_pct",
        ]

        mapper = ColumnMapper()
        result = mapper.auto_detect(columns)

        assert result.mapping is not None
        assert result.mapping.gain_pct == "gain_pct"
        assert result.mapping.time == "trigger_time_et"  # Only time-like column

    def test_metrics_with_correct_column(self):
        """Metrics calculation should work with correctly detected column."""
        # Create test data mimicking the real data structure
        df = pd.DataFrame({
            "ticker": ["AAPL", "GOOGL", "MSFT"],
            "date": ["2024-01-01", "2024-01-01", "2024-01-02"],
            "trigger_time_et": ["09:30:00", "10:00:00", "09:35:00"],
            "gain_pct_from_low": [50.0, -80.0, 120.0],  # Wrong column - huge values
            "gain_pct": [0.05, -0.03, 0.08],  # Correct column - decimal percentages
            "mae_pct": [0.02, 0.05, 0.01],
        })

        mapper = ColumnMapper()
        result = mapper.auto_detect(list(df.columns))

        assert result.mapping is not None
        assert result.mapping.gain_pct == "gain_pct"

        # Calculate metrics
        calc = MetricsCalculator()
        metrics, _, _ = calc.calculate(
            df=df,
            gain_col=result.mapping.gain_pct,
            derived=True,
            breakeven_is_win=False,
        )

        # With correct column: 2 winners (0.05, 0.08), 1 loser (-0.03)
        assert metrics.winner_count == 2
        assert metrics.loser_count == 1
        assert metrics.win_rate == pytest.approx(66.67, rel=0.01)
```

**Step 2: Run test**

Run: `pytest tests/integration/test_column_detection_edge_cases.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/integration/test_column_detection_edge_cases.py
git commit -m "$(cat <<'EOF'
test: add integration tests for column detection edge cases

Verifies that auto-detection correctly prefers 'gain_pct' over
'gain_pct_from_low' and that metrics calculate correctly with
the properly detected column.

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Run Full Test Suite and Manual Verification

**Step 1: Run full test suite**

Run: `pytest tests/ -v --tb=short`
Expected: All tests PASS

**Step 2: Manual verification checklist**

- [ ] Load `Para40Min15Prev40.xlsx` with lowercase `c:` path
- [ ] Verify auto-detection selects `gain_pct` (not `gain_pct_from_low`)
- [ ] Verify win rate shows ~72% (not 0%)
- [ ] Load same file with uppercase `C:` path
- [ ] Verify same cache is used (no re-detection prompt)
- [ ] Load a different file to verify auto-detection still works

**Step 3: Final commit**

```bash
git add -A
git commit -m "$(cat <<'EOF'
test: verify column mapper fixes with full test suite

All tests pass. Manual verification confirms:
- Case-insensitive cache lookup works correctly
- Auto-detection prefers shorter/exact column matches
- No regressions in existing functionality

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Summary

| Task | Component | Description |
|------|-----------|-------------|
| 1 | column_mapper.py | Fix case-sensitive cache path hashing |
| 2 | column_mapper.py | Fix auto-detection to prefer shorter matches |
| 3 | .lumen_cache/ | Document cache migration |
| 4 | test_column_detection_edge_cases.py | Integration tests |
| 5 | All | Full test suite and manual verification |

**Root Cause Addressed:**
- Cache misses due to Windows path case differences (`C:\` vs `c:\`)
- Wrong column selected when `gain_pct_from_low` appears before `gain_pct`

**Expected Outcome:**
- Users loading files with any path casing get consistent behavior
- Auto-detection correctly selects `gain_pct` over `gain_pct_from_low`
- Win rate displays correctly (~72% instead of 0%)
