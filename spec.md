# spec.md – logsum

## Goal

Summarize synthetic event logs from Bacardi brand-home booking capacity services to provide operational insights. Produces a grouped summary of event counts and time ranges per service and log level.

## Inputs

**File:** `events.csv`

**Schema:**
```
timestamp,level,service,message
```

**Columns:**
- `timestamp` – ISO 8601 datetime (e.g., `2026-06-30T14:23:45Z`)
- `level` – Log level (INFO, WARNING, ERROR, DEBUG, etc.)
- `service` – Bacardi service name: `capacity-indicator`, `booking-agent-router`, `ticketing-sync`, `eligibility-check`
- `message` – Free-text log message

**Example:**
```csv
timestamp,level,service,message
2026-06-30T14:00:00Z,INFO,capacity-indicator,Updated capacity for US-01
2026-06-30T14:01:32Z,ERROR,ticketing-sync,Failed to sync ticket T-12345
2026-06-30T14:02:15Z,WARNING,booking-agent-router,High queue depth: 450
```

## Outputs

**File:** `summary.csv` (or user-specified via `-o`)

**Schema:**
```
service,level,count,first_seen,last_seen
```

**Columns:**
- `service` – Service name (lowercase, as in input)
- `level` – Normalized log level (uppercase)
- `count` – Number of events in this group
- `first_seen` – Earliest timestamp for this group
- `last_seen` – Latest timestamp for this group

**Example:**
```csv
service,level,count,first_seen,last_seen
capacity-indicator,INFO,342,2026-06-30T14:00:00Z,2026-06-30T18:45:12Z
capacity-indicator,ERROR,5,2026-06-30T15:23:10Z,2026-06-30T15:28:03Z
ticketing-sync,ERROR,18,2026-06-30T14:01:32Z,2026-06-30T16:12:45Z
booking-agent-router,WARNING,67,2026-06-30T14:02:15Z,2026-06-30T18:30:22Z
```

## Normalisation rules

### Log levels
1. Convert to uppercase
2. Apply synonym mappings:
   - `WARNING`, `WARN` → `WARNING`
   - `ERROR`, `ERR` → `ERROR`
   - `INFO`, `INFORMATION` → `INFO`
   - `DEBUG`, `DBG` → `DEBUG`
3. Empty or null level → `UNKNOWN`

### Service names
- Use as-is (already standardized in lowercase)
- No trimming or transformation

### Timestamps
- Must parse as ISO 8601
- Timezone-aware (preserve UTC or local offset)

## Grouping rule

**Group key:** `(service, level)`

Each unique combination of service and normalized level creates one summary row.

## Aggregation

For each group:
- **count** – Total number of events
- **first_seen** – Earliest timestamp in the group
- **last_seen** – Latest timestamp in the group

## Edge cases

### Malformed timestamps
- **Behavior:** Skip the row, emit warning to stderr
- **Warning format:** `WARNING: Skipped row {row_num}: invalid timestamp '{value}'`
- **Continue processing remaining rows**

### Empty input
- **Behavior:** Create `summary.csv` with header row only
- **Exit code:** 0 (success)

### Missing level
- **Behavior:** Map to `UNKNOWN` level
- **Rationale:** Preserves event in summary; alerts to logging issues

### Duplicate headers or malformed CSV
- **Behavior:** Exit with error code 1, emit error to stderr
- **Error format:** `ERROR: Invalid CSV structure in {filename}`

## CLI

### Usage
```bash
python -m logsum <input.csv> [-o <output.csv>]
```

### Arguments
- `<input.csv>` – Path to events CSV file (required)
- `-o, --output` – Output path (optional, default: `summary.csv`)

### Exit codes
- `0` – Success
- `1` – Runtime error (I/O failure, invalid CSV structure, permissions)
- `2` – Invalid usage (missing required argument, file not found)

### Examples
```bash
# Default output (summary.csv)
python -m logsum data/events.csv

# Custom output path
python -m logsum data/events.csv -o results/summary.csv

# Invalid usage
python -m logsum
# Exit 2: ERROR: Missing required argument <input.csv>
```

## Out of scope

This tool does **not**:
- Analyze or parse message content (no regex, pattern matching, or keyword extraction)
- Filter events by time range, service, or level
- Process multiple files or directories
- Perform real-time or streaming analysis
- Validate data against schemas (beyond basic CSV parsing)
- Generate alerts or check thresholds
- Produce visualizations or HTML reports
- Modify or enrich input data

The tool is a single-purpose batch summarizer: read CSV, group, count, write CSV.

## Implementation notes

**Graceful degradation over strict validation:** Malformed timestamps trigger warnings to stderr but do not halt processing. This design choice prioritizes operational visibility—the tool produces a summary from valid data while alerting operators to quality issues, rather than failing silently or rejecting entire batches. In production log analysis, partial insights are often more valuable than no output.

## Signed off

**Karen Tsaturyan** – 2026-06-30
