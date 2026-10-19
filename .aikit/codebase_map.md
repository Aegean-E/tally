# Codebase Map & Symbol Catalog 🗺️

> **AUTO-GENERATED & VERIFIED BY `scripts/update_knowledge_base.py`**
> This document provides an automated, up-to-date registry of all modules, classes, and exported functions across this repository.

---

## 📊 Codebase Metrics
- **Total Python Modules**: `12`
- **Total Classes**: `9`
- **Total Top-Level Functions**: `10`
- **Total Class Methods**: `56`
- **Total Source Lines**: `812`

---

## 📦 Modules & Exported Symbols

### [`tally/__init__.py`](tally/__init__.py)
> *Tally: a dependency-free, local-first expense ledger.*

**Size**: `3` lines (`83` bytes)

---

### [`tally/__main__.py`](tally/__main__.py)
> *`python -m tally` entry point.*

**Size**: `7` lines (`95` bytes)

---

### [`tally/cli.py`](tally/cli.py)
> *Command-line interface: `add`, `list` and `summary` over one ledger file.*

**Size**: `105` lines (`3687` bytes)

**Functions:**
- `def build_parser()` - *The command grammar; `--db` selects the ledger file for every command.*
- `def run_add(ledger, args)` - *Validate the arguments, record the expense and echo it.*
- `def run_list(ledger, args)` - *Print one line per expense, or say the ledger is empty.*
- `def run_summary(ledger)` - *Print per-category totals and the grand total.*
- `def main(argv)` - *Run one command; user errors print the Why/Fix triad and exit 1.*

---

### [`tally/errors.py`](tally/errors.py)
> *Every user-facing failure carries a message, a reason and a repair (PRINCIPLE-011 R6).*

**Size**: `15` lines (`547` bytes)

**Classes:**
- `class TallyError` - *A failure the CLI reports as `Error:` / `Why:` / `Fix:` without a traceback.*
  - Method `.__init__(message, why, fix)`
  - Method `.render()` - *The three-line report the CLI prints on stderr.*

---

### [`tally/ledger.py`](tally/ledger.py)
> *Expense operations: the one place that assigns ids and computes category totals.*

**Size**: `40` lines (`1694` bytes)

**Classes:**
- `class Ledger` - *Add and read expenses through a `StateStore`; it owns no storage logic itself.*
  - Method `.__init__(store)`
  - Method `.add(amount_cents, category, note, spent_on)` - *Record one expense with the next free id.*
  - Method `.entries(category)` - *Every expense, oldest first, optionally narrowed to one normalized category.*
  - Method `.summary()` - *Total cents per category, with categories in alphabetical order.*
  - Method `.total()` - *Total cents across every category.*

---

### [`tally/models.py`](tally/models.py)
> *Expense value objects and money/date parsing shared by storage and the CLI.*

**Size**: `131` lines (`4778` bytes)

**Classes:**
- `class Expense` - *One recorded expense; money is integer cents so no float rounding can drift.*
  - Method `.as_dict()` - *The persisted form; keys are the on-disk schema from ADR-001.*
  - Method `.from_dict(data)` - *Rebuild an expense, refusing a record that would corrupt totals.*

**Functions:**
- `def parse_amount(text)` - *Convert a decimal amount such as `12.50` to integer cents.*
- `def format_cents(cents)` - *Render integer cents as a plain decimal string, e.g. 1250 -> `12.50`.*
- `def normalize_category(text)` - *Trim and lowercase a category, refusing empty or oversized values.*
- `def normalize_note(text)` - *Trim a note and refuse one that would dwarf a ledger line.*
- `def parse_date(text)` - *Validate an ISO date and return it unchanged, so stored dates sort lexically.*

---

### [`tally/storage.py`](tally/storage.py)
> *Crash-resilient JSON storage for the ledger (PRINCIPLE-013).*

**Size**: `231` lines (`9844` bytes)

**Classes:**
- `class StateStore` - *The ledger file, its backup and its lock, addressed by one path.*
  - Method `.__init__(path)`
  - Method `.read()` - *Every recorded expense; a missing ledger is an empty one.*
  - Method `.update(mutate)` - *Apply `mutate` to the ledger and persist its result under one held lock.*
  - Method `._load()` - *Parse the ledger, recovering from a readable backup before giving up on it.*
  - Method `._backup_or_empty(reason, quarantine)` - *Use the backup when it parses; otherwise quarantine the bad file and start empty.*
  - Method `._read_backup()` - *The parsed backup, or None when it is absent or unreadable.*
  - Method `._decode(data)` - *Validate the document envelope and rebuild every expense.*
  - Method `._save(expenses)` - *Write the ledger atomically, keeping the previous version as a backup.*
  - Method `._replace(temp_path)` - *Replace the ledger, retrying only transient sharing violations on Windows (ADR-002).*
  - Method `._fsync_directory(directory)` - *Flush the directory entry on POSIX; Windows cannot fsync a directory handle.*
  - Method `._quarantine()` - *Move a corrupt ledger aside so it can neither block reads nor be overwritten.*
  - Method `._lock()` - *Hold the advisory lock file for one read-modify-write.*
  - Method `._break_stale_lock()` - *Break a lock older than 30 seconds by atomically renaming it aside.*

---

### [`tests/__init__.py`](tests/__init__.py)
> *Test package for Tally.*

**Size**: `1` lines (`30` bytes)

---

### [`tests/test_cli.py`](tests/test_cli.py)
> *End-to-end tests of the command-line interface through `main`.*

**Size**: `62` lines (`2103` bytes)

**Classes:**
- `class CliTests`
  - Method `.setUp()`
  - Method `.run_cli(*arguments)`
  - Method `.test_add_then_list_then_summary()`
  - Method `.test_list_on_empty_ledger()`
  - Method `.test_invalid_amount_reports_why_and_fix()`
  - Method `.test_missing_command_is_argument_misuse()`

---

### [`tests/test_ledger.py`](tests/test_ledger.py)
> *Tests for the ledger operations on top of the state store.*

**Size**: `50` lines (`2057` bytes)

**Classes:**
- `class LedgerTests`
  - Method `.setUp()`
  - Method `.test_add_assigns_consecutive_ids()`
  - Method `.test_entries_are_oldest_first()`
  - Method `.test_entries_filter_by_category()`
  - Method `.test_summary_totals_each_category()`
  - Method `.test_entries_survive_a_new_ledger_instance()`

---

### [`tests/test_models.py`](tests/test_models.py)
> *Tests for money, date and category parsing.*

**Size**: `54` lines (`1760` bytes)

**Classes:**
- `class AmountTests`
  - Method `.test_parses_decimal_amounts_to_cents()`
  - Method `.test_rejects_non_positive_amounts()`
  - Method `.test_rejects_fractions_of_a_cent()`
  - Method `.test_rejects_garbage()`
  - Method `.test_formats_cents_with_two_places()`
- `class LabelTests`
  - Method `.test_category_is_trimmed_and_lowercased()`
  - Method `.test_empty_category_is_refused()`
  - Method `.test_note_is_trimmed()`
  - Method `.test_iso_date_is_kept()`
  - Method `.test_invalid_date_is_refused()`

---

### [`tests/test_storage.py`](tests/test_storage.py)
> *Fault-injection tests for the atomic ledger store (PRINCIPLE-013).*

**Size**: `113` lines (`4665` bytes)

**Classes:**
- `class StoreFaultTests`
  - Method `.setUp()`
  - Method `._write(expenses)`
  - Method `.test_malformed_json_recovers_from_backup()`
  - Method `.test_zero_byte_ledger_recovers_from_backup()`
  - Method `.test_backup_is_written_before_replacement()`
  - Method `.test_unknown_version_is_refused_in_place()`
  - Method `.test_insufficient_disk_space_writes_nothing()`
  - Method `.test_concurrent_writers_lose_no_entries()`
  - Method `.test_replace_does_not_retry_a_non_transient_error()`
  - Method `.test_replace_retries_a_permission_error_then_succeeds()`
  - Method `.test_fsync_directory_failure_is_reported()`
  - Method `.test_backup_failure_is_reported_and_the_write_continues()`

---
