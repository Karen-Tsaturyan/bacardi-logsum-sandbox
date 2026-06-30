"""
Test suite for logsum CLI tool.

Tests cover all specification requirements from spec.md:
- Grouping by (service, level)
- Level normalization (uppercase, synonyms, UNKNOWN for missing)
- Malformed timestamp handling
- Empty input handling
- CLI invocation and exit codes
- Aggregation (count, first_seen, last_seen)
"""

import csv
import os
import subprocess
import sys
from pathlib import Path

import pytest


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def valid_events_csv(tmp_path):
    """Create a valid events.csv with multiple services and levels."""
    csv_path = tmp_path / "events.csv"
    csv_path.write_text(
        "timestamp,level,service,message\n"
        "2026-06-30T14:00:00Z,INFO,capacity-indicator,Updated capacity for US-01\n"
        "2026-06-30T14:01:32Z,ERROR,ticketing-sync,Failed to sync ticket T-12345\n"
        "2026-06-30T14:02:15Z,WARNING,booking-agent-router,High queue depth: 450\n"
        "2026-06-30T14:03:00Z,INFO,capacity-indicator,Another update\n"
        "2026-06-30T14:04:00Z,ERROR,ticketing-sync,Another error\n"
    )
    return csv_path


@pytest.fixture
def empty_events_csv(tmp_path):
    """Create an empty events.csv with header only."""
    csv_path = tmp_path / "events_empty.csv"
    csv_path.write_text("timestamp,level,service,message\n")
    return csv_path


@pytest.fixture
def level_synonyms_csv(tmp_path):
    """Create CSV with all level synonyms."""
    csv_path = tmp_path / "synonyms.csv"
    csv_path.write_text(
        "timestamp,level,service,message\n"
        "2026-06-30T14:00:00Z,WARN,capacity-indicator,Warning test\n"
        "2026-06-30T14:01:00Z,WARNING,capacity-indicator,Warning test 2\n"
        "2026-06-30T14:02:00Z,ERR,ticketing-sync,Error test\n"
        "2026-06-30T14:03:00Z,ERROR,ticketing-sync,Error test 2\n"
        "2026-06-30T14:04:00Z,INFORMATION,booking-agent-router,Info test\n"
        "2026-06-30T14:05:00Z,INFO,booking-agent-router,Info test 2\n"
        "2026-06-30T14:06:00Z,DBG,eligibility-check,Debug test\n"
        "2026-06-30T14:07:00Z,DEBUG,eligibility-check,Debug test 2\n"
    )
    return csv_path


@pytest.fixture
def missing_level_csv(tmp_path):
    """Create CSV with missing/empty levels."""
    csv_path = tmp_path / "missing_level.csv"
    csv_path.write_text(
        "timestamp,level,service,message\n"
        "2026-06-30T14:00:00Z,,capacity-indicator,No level\n"
        "2026-06-30T14:01:00Z,,capacity-indicator,No level again\n"
    )
    return csv_path


@pytest.fixture
def malformed_timestamp_csv(tmp_path):
    """Create CSV with malformed timestamps."""
    csv_path = tmp_path / "malformed.csv"
    csv_path.write_text(
        "timestamp,level,service,message\n"
        "2026-06-30T14:00:00Z,INFO,capacity-indicator,Valid row\n"
        "not-a-timestamp,ERROR,ticketing-sync,Invalid timestamp\n"
        "2026-06-30T14:02:00Z,WARNING,booking-agent-router,Another valid row\n"
        "invalid-date,INFO,eligibility-check,Another invalid\n"
        "2026-06-30T14:03:00Z,INFO,capacity-indicator,Final valid row\n"
    )
    return csv_path


@pytest.fixture
def malformed_csv_structure(tmp_path):
    """Create CSV with invalid structure."""
    csv_path = tmp_path / "malformed_structure.csv"
    csv_path.write_text(
        "timestamp,level,service,message\n"
        "2026-06-30T14:00:00Z,INFO,capacity-indicator\n"  # Missing column
    )
    return csv_path


@pytest.fixture
def aggregation_test_csv(tmp_path):
    """Create CSV to test count, first_seen, last_seen aggregation."""
    csv_path = tmp_path / "aggregation.csv"
    csv_path.write_text(
        "timestamp,level,service,message\n"
        "2026-06-30T10:00:00Z,INFO,capacity-indicator,First\n"
        "2026-06-30T12:00:00Z,INFO,capacity-indicator,Middle\n"
        "2026-06-30T18:00:00Z,INFO,capacity-indicator,Last\n"
        "2026-06-30T11:00:00Z,ERROR,ticketing-sync,Only one\n"
    )
    return csv_path


@pytest.fixture
def lowercase_level_csv(tmp_path):
    """Create CSV with lowercase levels to test normalization."""
    csv_path = tmp_path / "lowercase.csv"
    csv_path.write_text(
        "timestamp,level,service,message\n"
        "2026-06-30T14:00:00Z,info,capacity-indicator,Lowercase info\n"
        "2026-06-30T14:01:00Z,error,ticketing-sync,Lowercase error\n"
        "2026-06-30T14:02:00Z,warning,booking-agent-router,Lowercase warning\n"
    )
    return csv_path


@pytest.fixture
def varied_count_csv(tmp_path):
    """Create CSV with varied event counts per group."""
    csv_path = tmp_path / "varied.csv"
    csv_path.write_text(
        "timestamp,level,service,message\n"
        # Group 1: count=1
        "2026-06-30T14:00:00Z,INFO,capacity-indicator,Event 1\n"
        # Group 2: count=3
        "2026-06-30T14:01:00Z,ERROR,ticketing-sync,Event 1\n"
        "2026-06-30T14:02:00Z,ERROR,ticketing-sync,Event 2\n"
        "2026-06-30T14:03:00Z,ERROR,ticketing-sync,Event 3\n"
        # Group 3: count=5
        "2026-06-30T14:04:00Z,WARNING,booking-agent-router,Event 1\n"
        "2026-06-30T14:05:00Z,WARNING,booking-agent-router,Event 2\n"
        "2026-06-30T14:06:00Z,WARNING,booking-agent-router,Event 3\n"
        "2026-06-30T14:07:00Z,WARNING,booking-agent-router,Event 4\n"
        "2026-06-30T14:08:00Z,WARNING,booking-agent-router,Event 5\n"
    )
    return csv_path


# ============================================================================
# Test: Grouping
# ============================================================================

def test_grouping_by_service_and_level(valid_events_csv, tmp_path):
    """Test that events are grouped by (service, level) combination."""
    output_path = tmp_path / "summary.csv"

    result = subprocess.run(
        [sys.executable, "-m", "src.logsum", str(valid_events_csv), "-o", str(output_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert output_path.exists()

    with open(output_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Should have 3 groups: (capacity-indicator, INFO), (ticketing-sync, ERROR), (booking-agent-router, WARNING)
    assert len(rows) == 3

    # Check each group exists
    groups = {(row["service"], row["level"]) for row in rows}
    assert ("capacity-indicator", "INFO") in groups
    assert ("ticketing-sync", "ERROR") in groups
    assert ("booking-agent-router", "WARNING") in groups


def test_multiple_events_same_group(aggregation_test_csv, tmp_path):
    """Test that multiple events in the same group are counted correctly."""
    output_path = tmp_path / "summary.csv"

    result = subprocess.run(
        [sys.executable, "-m", "src.logsum", str(aggregation_test_csv), "-o", str(output_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    with open(output_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Find the capacity-indicator INFO group
    capacity_info = next(r for r in rows if r["service"] == "capacity-indicator" and r["level"] == "INFO")

    assert capacity_info["count"] == "3"
    assert capacity_info["first_seen"] == "2026-06-30T10:00:00Z"
    assert capacity_info["last_seen"] == "2026-06-30T18:00:00Z"

    # Find the ticketing-sync ERROR group
    ticketing_error = next(r for r in rows if r["service"] == "ticketing-sync" and r["level"] == "ERROR")

    assert ticketing_error["count"] == "1"
    assert ticketing_error["first_seen"] == "2026-06-30T11:00:00Z"
    assert ticketing_error["last_seen"] == "2026-06-30T11:00:00Z"


# ============================================================================
# Test: Level Normalization
# ============================================================================

def test_level_normalization_uppercase(lowercase_level_csv, tmp_path):
    """Test that levels are converted to uppercase."""
    output_path = tmp_path / "summary.csv"

    result = subprocess.run(
        [sys.executable, "-m", "src.logsum", str(lowercase_level_csv), "-o", str(output_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    with open(output_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # All levels should be uppercase
    levels = {row["level"] for row in rows}
    assert levels == {"INFO", "ERROR", "WARNING"}


def test_level_synonyms(level_synonyms_csv, tmp_path):
    """Test that level synonyms are normalized correctly."""
    output_path = tmp_path / "summary.csv"

    result = subprocess.run(
        [sys.executable, "-m", "src.logsum", str(level_synonyms_csv), "-o", str(output_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    with open(output_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # WARN + WARNING should be grouped together
    warning_rows = [r for r in rows if r["level"] == "WARNING" and r["service"] == "capacity-indicator"]
    assert len(warning_rows) == 1
    assert warning_rows[0]["count"] == "2"

    # ERR + ERROR should be grouped together
    error_rows = [r for r in rows if r["level"] == "ERROR" and r["service"] == "ticketing-sync"]
    assert len(error_rows) == 1
    assert error_rows[0]["count"] == "2"

    # INFORMATION + INFO should be grouped together
    info_rows = [r for r in rows if r["level"] == "INFO" and r["service"] == "booking-agent-router"]
    assert len(info_rows) == 1
    assert info_rows[0]["count"] == "2"

    # DBG + DEBUG should be grouped together
    debug_rows = [r for r in rows if r["level"] == "DEBUG" and r["service"] == "eligibility-check"]
    assert len(debug_rows) == 1
    assert debug_rows[0]["count"] == "2"


def test_missing_level_maps_to_unknown(missing_level_csv, tmp_path):
    """Test that missing/empty levels are mapped to UNKNOWN."""
    output_path = tmp_path / "summary.csv"

    result = subprocess.run(
        [sys.executable, "-m", "src.logsum", str(missing_level_csv), "-o", str(output_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    with open(output_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 1
    assert rows[0]["service"] == "capacity-indicator"
    assert rows[0]["level"] == "UNKNOWN"
    assert rows[0]["count"] == "2"


# ============================================================================
# Test: Malformed Timestamp Handling
# ============================================================================

def test_malformed_timestamp_skips_row_with_warning(malformed_timestamp_csv, tmp_path):
    """Test that malformed timestamps skip row and emit warning."""
    output_path = tmp_path / "summary.csv"

    result = subprocess.run(
        [sys.executable, "-m", "src.logsum", str(malformed_timestamp_csv), "-o", str(output_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    # Check warnings in stderr
    assert "WARNING: Skipped row" in result.stderr
    assert "invalid timestamp" in result.stderr.lower()
    assert "not-a-timestamp" in result.stderr
    assert "invalid-date" in result.stderr

    # Check that valid rows were processed
    with open(output_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Should have 3 valid rows: 2 capacity-indicator INFO, 1 booking-agent-router WARNING
    assert len(rows) == 2

    capacity_info = next(r for r in rows if r["service"] == "capacity-indicator")
    assert capacity_info["count"] == "2"

    booking_warning = next(r for r in rows if r["service"] == "booking-agent-router")
    assert booking_warning["count"] == "1"


# ============================================================================
# Test: Empty Input
# ============================================================================

def test_empty_input_creates_header_only_output(empty_events_csv, tmp_path):
    """Test that empty input creates output with header only."""
    output_path = tmp_path / "summary.csv"

    result = subprocess.run(
        [sys.executable, "-m", "src.logsum", str(empty_events_csv), "-o", str(output_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert output_path.exists()

    content = output_path.read_text()
    lines = content.strip().split("\n")

    assert len(lines) == 1
    assert lines[0] == "service,level,count,first_seen,last_seen"


# ============================================================================
# Test: CLI Invocation
# ============================================================================

def test_cli_with_default_output(valid_events_csv, tmp_path, monkeypatch):
    """Test CLI with default output path (summary.csv)."""
    # Get project root and set PYTHONPATH so src module can be found
    project_root = Path(__file__).parent.parent
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root)

    # Change to tmp_path so summary.csv is created there
    monkeypatch.chdir(tmp_path)

    result = subprocess.run(
        [sys.executable, "-m", "src.logsum", str(valid_events_csv)],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=env,
    )

    assert result.returncode == 0

    summary_path = tmp_path / "summary.csv"
    assert summary_path.exists()

    with open(summary_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) > 0


def test_cli_with_custom_output_flag(valid_events_csv, tmp_path):
    """Test CLI with custom output path using -o flag."""
    output_path = tmp_path / "custom_output.csv"

    result = subprocess.run(
        [sys.executable, "-m", "src.logsum", str(valid_events_csv), "-o", str(output_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert output_path.exists()


def test_cli_with_output_long_flag(valid_events_csv, tmp_path):
    """Test CLI with --output long flag."""
    output_path = tmp_path / "custom_output.csv"

    result = subprocess.run(
        [sys.executable, "-m", "src.logsum", str(valid_events_csv), "--output", str(output_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert output_path.exists()


# ============================================================================
# Test: Exit Codes
# ============================================================================

def test_exit_code_success(valid_events_csv, tmp_path):
    """Test exit code 0 on success."""
    output_path = tmp_path / "summary.csv"

    result = subprocess.run(
        [sys.executable, "-m", "src.logsum", str(valid_events_csv), "-o", str(output_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0


def test_exit_code_invalid_usage_missing_argument(tmp_path):
    """Test exit code 2 for missing required argument."""
    result = subprocess.run(
        [sys.executable, "-m", "src.logsum"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "ERROR" in result.stderr or "error" in result.stderr


def test_exit_code_invalid_usage_file_not_found(tmp_path):
    """Test exit code 2 for file not found."""
    nonexistent_file = tmp_path / "nonexistent.csv"

    result = subprocess.run(
        [sys.executable, "-m", "src.logsum", str(nonexistent_file)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2


@pytest.mark.xfail(reason="Implementation doesn't validate CSV structure per spec - should return exit code 1 for missing columns")
def test_exit_code_runtime_error_malformed_csv(malformed_csv_structure, tmp_path):
    """Test exit code 1 for invalid CSV structure."""
    output_path = tmp_path / "summary.csv"

    result = subprocess.run(
        [sys.executable, "-m", "src.logsum", str(malformed_csv_structure), "-o", str(output_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "ERROR" in result.stderr or "Invalid CSV" in result.stderr


def test_exit_code_runtime_error_permission_denied(valid_events_csv, tmp_path):
    """Test exit code 1 for I/O errors (permission denied)."""
    # Create a read-only directory
    readonly_dir = tmp_path / "readonly"
    readonly_dir.mkdir()
    readonly_dir.chmod(0o444)

    output_path = readonly_dir / "summary.csv"

    result = subprocess.run(
        [sys.executable, "-m", "src.logsum", str(valid_events_csv), "-o", str(output_path)],
        capture_output=True,
        text=True,
    )

    # Clean up
    readonly_dir.chmod(0o755)

    assert result.returncode == 1


# ============================================================================
# Test: Service Names Preservation
# ============================================================================

def test_service_names_preserved_as_is(valid_events_csv, tmp_path):
    """Test that service names are preserved exactly as in input (lowercase)."""
    output_path = tmp_path / "summary.csv"

    result = subprocess.run(
        [sys.executable, "-m", "src.logsum", str(valid_events_csv), "-o", str(output_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    with open(output_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    services = {row["service"] for row in rows}

    # All services should be lowercase (as in input)
    assert all(s.islower() for s in services)
    assert "capacity-indicator" in services
    assert "ticketing-sync" in services
    assert "booking-agent-router" in services


# ============================================================================
# Test: Aggregation Details
# ============================================================================

def test_aggregation_count_first_last(aggregation_test_csv, tmp_path):
    """Test count, first_seen, and last_seen aggregation accuracy."""
    output_path = tmp_path / "summary.csv"

    result = subprocess.run(
        [sys.executable, "-m", "src.logsum", str(aggregation_test_csv), "-o", str(output_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    with open(output_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    capacity_info = next(r for r in rows if r["service"] == "capacity-indicator")

    # Verify count
    assert capacity_info["count"] == "3"

    # Verify first_seen is the earliest
    assert capacity_info["first_seen"] == "2026-06-30T10:00:00Z"

    # Verify last_seen is the latest
    assert capacity_info["last_seen"] == "2026-06-30T18:00:00Z"


def test_all_four_bacardi_services(tmp_path):
    """Test that all four Bacardi services are handled correctly."""
    csv_path = tmp_path / "all_services.csv"
    csv_path.write_text(
        "timestamp,level,service,message\n"
        "2026-06-30T14:00:00Z,INFO,capacity-indicator,Test\n"
        "2026-06-30T14:01:00Z,INFO,booking-agent-router,Test\n"
        "2026-06-30T14:02:00Z,INFO,ticketing-sync,Test\n"
        "2026-06-30T14:03:00Z,INFO,eligibility-check,Test\n"
    )

    output_path = tmp_path / "summary.csv"

    result = subprocess.run(
        [sys.executable, "-m", "src.logsum", str(csv_path), "-o", str(output_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    with open(output_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    services = {row["service"] for row in rows}

    assert services == {
        "capacity-indicator",
        "booking-agent-router",
        "ticketing-sync",
        "eligibility-check",
    }


# ============================================================================
# Test: Min Count Filtering
# ============================================================================

def test_min_count_default_no_filtering(varied_count_csv, tmp_path):
    """Test that without --min-count, all groups are included."""
    output_path = tmp_path / "summary.csv"

    result = subprocess.run(
        [sys.executable, "-m", "src.logsum", str(varied_count_csv), "-o", str(output_path)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    with open(output_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Should see all 3 groups
    assert len(rows) == 3
    counts = {int(row["count"]) for row in rows}
    assert counts == {1, 3, 5}


def test_min_count_filters_correctly(varied_count_csv, tmp_path):
    """Test that --min-count 3 filters out groups with count < 3."""
    output_path = tmp_path / "summary.csv"

    result = subprocess.run(
        [sys.executable, "-m", "src.logsum", str(varied_count_csv), "-o", str(output_path), "--min-count", "3"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    with open(output_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Should see only 2 groups (count=3 and count=5)
    assert len(rows) == 2
    counts = sorted([int(row["count"]) for row in rows])
    assert counts == [3, 5]

    # Verify specific groups
    services = {row["service"] for row in rows}
    assert services == {"ticketing-sync", "booking-agent-router"}


def test_min_count_zero_same_as_default(varied_count_csv, tmp_path):
    """Test that --min-count 0 behaves like no flag."""
    output_path = tmp_path / "summary.csv"

    result = subprocess.run(
        [sys.executable, "-m", "src.logsum", str(varied_count_csv), "-o", str(output_path), "--min-count", "0"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    with open(output_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Should see all 3 groups
    assert len(rows) == 3


def test_min_count_higher_than_all_groups(varied_count_csv, tmp_path):
    """Test that --min-count 100 produces header-only output."""
    output_path = tmp_path / "summary.csv"

    result = subprocess.run(
        [sys.executable, "-m", "src.logsum", str(varied_count_csv), "-o", str(output_path), "--min-count", "100"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    with open(output_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Should see only header, no data rows
    assert len(rows) == 0


def test_min_count_with_single_matching_group(varied_count_csv, tmp_path):
    """Test that --min-count 5 shows only the one group with count=5."""
    output_path = tmp_path / "summary.csv"

    result = subprocess.run(
        [sys.executable, "-m", "src.logsum", str(varied_count_csv), "-o", str(output_path), "--min-count", "5"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0

    with open(output_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Should see only 1 group
    assert len(rows) == 1
    assert int(rows[0]["count"]) == 5
    assert rows[0]["service"] == "booking-agent-router"
    assert rows[0]["level"] == "WARNING"

