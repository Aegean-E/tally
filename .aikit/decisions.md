# Decisions

Why this project is built the way it is, oldest first. One entry per decision that changes a
contract, a dependency, a data format or the architecture; IDs are consecutive and never reused.

### ADR-001: One JSON ledger with integer cents and atomic, locked writes
- **Date**: 2026-10-19
- **Status**: Accepted
- **Context**: A first usable project needs a durable expense log without a database dependency,
  and money must not drift through binary floating-point rounding.
- **Decision**: Store every expense in one JSON document
  (`{"version": 1, "expenses": [{"id", "amount_cents", "category", "note", "spent_on"}]}`).
  Amounts are integer cents parsed with `Decimal`. Each save copies the current file to `.bak`,
  writes a unique temporary file, fsyncs it, then replaces the ledger; each read-modify-write holds
  `<ledger>.lock` for at most 3 seconds, and a lock older than 30 seconds is broken. Malformed JSON
  is quarantined and recovered from `.bak`; an unknown `version` is refused in place.
- **Consequences**: The file is easy to inspect, back up and edit by hand. Totals are exact. The
  whole ledger is held in memory per command, which is fine at personal-ledger scale but would need
  a different store for very large histories. Categories are free-form lowercase labels, so typos
  create separate categories rather than being rejected.
