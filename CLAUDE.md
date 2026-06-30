# CLAUDE.md

## Project Context

Tiny CLI tool that summarizes synthetic `events.csv` logs for Bacardi brand-home booking capacity flow (US-01 live capacity). Analyzes event patterns to provide operational insights into the booking system.

Related Bacardi services: `capacity-indicator`, `booking-agent-router`, `ticketing-sync`, `eligibility-check`.

## Conventions

- **Code**: `src/`
- **Tests**: `tests/`
- **Data**: `data/`

## Utilities to Prefer

- Python 3.11 standard library
- `ruff` for linting/formatting
- `pytest` for testing

## Escalation Gates

**Stop and ask before:**
- Installing or adding dependencies
- Using non-synthetic data sources
- Overwriting `spec.md` after sign-off
