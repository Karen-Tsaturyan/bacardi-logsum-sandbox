"""Log summarization CLI for Bacardi event logs."""
import csv
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict
import argparse


def normalize_level(level):
    """Normalize log level according to spec."""
    if not level or level.strip() == '':
        return 'UNKNOWN'

    level = level.strip().upper()

    # Apply synonym mappings
    synonyms = {
        'WARN': 'WARNING',
        'ERR': 'ERROR',
        'INFORMATION': 'INFO',
        'DBG': 'DEBUG'
    }

    return synonyms.get(level, level)


def parse_timestamp(timestamp_str):
    """Parse ISO 8601 timestamp. Returns datetime object or None if invalid."""
    try:
        # Handle both Z suffix and explicit timezone
        ts = timestamp_str.strip()
        if ts.endswith('Z'):
            ts = ts[:-1] + '+00:00'
        return datetime.fromisoformat(ts)
    except (ValueError, AttributeError):
        return None


def process_events(input_path, output_path):
    """Main processing function. Returns exit code."""
    groups = defaultdict(lambda: {'count': 0, 'first_seen': None, 'last_seen': None})

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            # Validate CSV structure
            required_fields = {'timestamp', 'level', 'service', 'message'}
            if not reader.fieldnames or not required_fields.issubset(set(reader.fieldnames)):
                print(f"ERROR: Invalid CSV structure in {input_path}", file=sys.stderr)
                return 1

            for row_num, row in enumerate(reader, start=2):  # Row 1 is header
                timestamp_str = row.get('timestamp', '').strip()
                level = row.get('level', '')
                service = row.get('service', '').strip()

                # Parse timestamp
                timestamp = parse_timestamp(timestamp_str)
                if timestamp is None:
                    print(f"WARNING: Skipped row {row_num}: invalid timestamp '{timestamp_str}'", file=sys.stderr)
                    continue

                # Normalize level
                normalized_level = normalize_level(level)

                # Group key
                key = (service, normalized_level)

                # Update aggregation
                groups[key]['count'] += 1
                if groups[key]['first_seen'] is None or timestamp < groups[key]['first_seen']:
                    groups[key]['first_seen'] = timestamp
                if groups[key]['last_seen'] is None or timestamp > groups[key]['last_seen']:
                    groups[key]['last_seen'] = timestamp

    except FileNotFoundError:
        print(f"ERROR: File not found: {input_path}", file=sys.stderr)
        return 2
    except PermissionError:
        print(f"ERROR: Permission denied: {input_path}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    # Write output
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['service', 'level', 'count', 'first_seen', 'last_seen'])

            # Sort by service, then level for consistent output
            for (service, level), data in sorted(groups.items()):
                # Format timestamps back to ISO 8601 with Z suffix
                first_iso = data['first_seen'].isoformat()
                last_iso = data['last_seen'].isoformat()
                # Convert +00:00 to Z for UTC timestamps
                first_iso = first_iso.replace('+00:00', 'Z')
                last_iso = last_iso.replace('+00:00', 'Z')

                writer.writerow([
                    service,
                    level,
                    data['count'],
                    first_iso,
                    last_iso
                ])

        return 0

    except PermissionError:
        print(f"ERROR: Permission denied: {output_path}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR: Failed to write output: {e}", file=sys.stderr)
        return 1


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Summarize event logs by service and level',
        prog='logsum'
    )
    parser.add_argument('input', help='Path to events CSV file')
    parser.add_argument('output', nargs='?', default='summary.csv',
                        help='Output path (default: summary.csv)')
    parser.add_argument('-o', '--output-file', dest='output_alt',
                        help='Alternative way to specify output path')

    args = parser.parse_args()

    # Use -o flag if provided, otherwise use positional output arg
    output = args.output_alt if args.output_alt else args.output

    input_path = Path(args.input)
    output_path = Path(output)

    exit_code = process_events(input_path, output_path)
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
