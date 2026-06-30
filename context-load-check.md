# Summary of CLAUDE.md

## Project Context
A CLI tool for analyzing synthetic event logs (`events.csv`) from the Bacardi brand-home booking capacity system (US-01 live capacity). Provides operational insights into booking patterns. Related services include `capacity-indicator`, `booking-agent-router`, `ticketing-sync`, and `eligibility-check`.

## Conventions
- Code in `src/`
- Tests in `tests/`
- Data in `data/`

## Utilities to Prefer
- Python 3.11 standard library
- `ruff` for linting/formatting
- `pytest` for testing

## Escalation Gates
Must ask before:
- Installing or adding dependencies
- Using non-synthetic data sources
- Overwriting `spec.md` after sign-off
