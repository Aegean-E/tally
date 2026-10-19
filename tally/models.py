"""Expense value objects and money/date parsing shared by storage and the CLI."""

import calendar
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional, Tuple

from tally.errors import TallyError

MAX_NOTE_CHARS = 200
MAX_CATEGORY_CHARS = 40


@dataclass(frozen=True)
class Expense:
    """One recorded expense; money is integer cents so no float rounding can drift."""

    id: int
    amount_cents: int
    category: str
    note: str
    spent_on: str

    def as_dict(self) -> Dict[str, Any]:
        """The persisted form; keys are the on-disk schema from ADR-001."""
        return {
            "id": self.id,
            "amount_cents": self.amount_cents,
            "category": self.category,
            "note": self.note,
            "spent_on": self.spent_on,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Expense":
        """Rebuild an expense, refusing a record that would corrupt totals."""
        try:
            expense = cls(
                id=int(data["id"]),
                amount_cents=int(data["amount_cents"]),
                category=str(data["category"]),
                note=str(data.get("note", "")),
                spent_on=str(data["spent_on"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise TallyError(
                f"Expense record is malformed: {exc}",
                "the ledger file holds data the tool cannot total safely.",
                "restore the .bak file beside the ledger, or fix the record by hand.",
            ) from exc
        if expense.id < 1 or expense.amount_cents <= 0:
            raise TallyError(
                f"Expense record #{expense.id} has an impossible amount.",
                "ids start at 1 and amounts are positive integer cents.",
                "correct the record, or restore the ledger's .bak file.",
            )
        return expense


def parse_amount(text: str) -> int:
    """Convert a decimal amount such as `12.50` to integer cents."""
    try:
        value = Decimal(text.strip())
    except (InvalidOperation, AttributeError) as exc:
        raise TallyError(
            f"'{text}' is not a valid amount.",
            "amounts are decimal numbers such as 12.50.",
            "pass a positive amount with at most two decimal places, e.g. 'tally add 12.50'.",
        ) from exc
    if not value.is_finite() or value <= 0:
        raise TallyError(
            f"Amount '{text}' must be greater than zero.",
            "an expense records money spent, so it cannot be zero or negative.",
            "pass a positive amount, e.g. 'tally add 12.50'.",
        )
    if value.as_tuple().exponent < -2:
        raise TallyError(
            f"Amount '{text}' has more than two decimal places.",
            "money is stored as whole cents, so fractions of a cent would be lost.",
            "round the amount to cents, e.g. 'tally add 12.50'.",
        )
    return int(value * 100)


def format_cents(cents: int) -> str:
    """Render integer cents as a plain decimal string, e.g. 1250 -> `12.50`."""
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}{cents // 100}.{cents % 100:02d}"


def normalize_category(text: str) -> str:
    """Trim and lowercase a category, refusing empty or oversized values."""
    category = text.strip().lower()
    if not category:
        raise TallyError(
            "A category cannot be empty.",
            "every expense is grouped by category in the summary.",
            "pass a name such as '--category food'.",
        )
    if len(category) > MAX_CATEGORY_CHARS:
        raise TallyError(
            f"Category '{category[:20]}...' is longer than {MAX_CATEGORY_CHARS} characters.",
            "categories are labels shown in a one-line summary.",
            "use a shorter category name.",
        )
    return category


def normalize_note(text: str) -> str:
    """Trim a note and refuse one that would dwarf a ledger line."""
    note = text.strip()
    if len(note) > MAX_NOTE_CHARS:
        raise TallyError(
            f"Note is longer than {MAX_NOTE_CHARS} characters.",
            "notes are shown beside each entry and kept short.",
            "shorten the note.",
        )
    return note


def parse_date(text: str) -> str:
    """Validate an ISO date and return it unchanged, so stored dates sort lexically."""
    try:
        return date.fromisoformat(text.strip()).isoformat()
    except (ValueError, AttributeError) as exc:
        raise TallyError(
            f"'{text}' is not a valid date.",
            "dates are stored as ISO-8601 so the ledger sorts correctly.",
            "pass a date such as '--date 2026-10-19'.",
        ) from exc


def parse_id(text: str) -> int:
    """Convert an expense id such as `3` to a positive integer."""
    try:
        value = int(text.strip())
    except (AttributeError, ValueError) as exc:
        raise TallyError(
            f"'{text}' is not a valid expense id.",
            "ids are the positive whole numbers shown beside each entry by `tally list`.",
            "run `tally list`, then pass the number after '#', e.g. 'tally edit 3 --amount 9.99'.",
        ) from exc
    if value < 1:
        raise TallyError(
            f"Expense id '{text}' must be greater than zero.",
            "ids start at 1 and are assigned one past the highest remaining id.",
            "run `tally list` and pass the number after '#'.",
        )
    return value


def parse_month(text: str) -> str:
    """Validate a month in YYYY-MM format, returning canonical YYYY-MM."""
    try:
        stripped = text.strip()
        parts = stripped.split("-")
        if len(parts) != 2 or len(parts[0]) != 4 or len(parts[1]) != 2:
            raise ValueError("expected YYYY-MM")
        date.fromisoformat(f"{stripped}-01")
        return stripped
    except (ValueError, AttributeError) as exc:
        raise TallyError(
            f"'{text}' is not a valid month.",
            "months are specified in ISO format as YYYY-MM, e.g. 2026-10.",
            "pass a month such as '--month 2026-10'.",
        ) from exc


def resolve_date_range(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    month: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Validate and resolve --from, --to and --month into an ISO (start_date, end_date) pair."""
    if month is not None and (from_date is not None or to_date is not None):
        raise TallyError(
            "Cannot combine --month with --from or --to.",
            "a month filter already specifies a complete date boundary.",
            "use either --month or --from/--to, not both.",
        )
    if month is not None:
        parsed_month = parse_month(month)
        year, m = int(parsed_month[:4]), int(parsed_month[5:7])
        _, last_day = calendar.monthrange(year, m)
        return f"{parsed_month}-01", f"{parsed_month}-{last_day:02d}"

    parsed_from = parse_date(from_date) if from_date is not None else None
    parsed_to = parse_date(to_date) if to_date is not None else None
    if parsed_from is not None and parsed_to is not None and parsed_from > parsed_to:
        raise TallyError(
            f"Start date '{parsed_from}' is after end date '{parsed_to}'.",
            "the start of a date range cannot be later than the end.",
            "ensure --from is earlier than or equal to --to.",
        )
    return parsed_from, parsed_to
