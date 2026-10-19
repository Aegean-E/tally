"""Command-line interface: `add`, `list` and `summary` over one ledger file."""

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Optional, Sequence

from tally.errors import TallyError
from tally.ledger import Ledger
from tally.models import (
    format_cents,
    normalize_category,
    normalize_note,
    parse_amount,
    parse_date,
    parse_id,
)
from tally.storage import StateStore

DEFAULT_DB = "tally.json"


def build_parser() -> argparse.ArgumentParser:
    """The command grammar; `--db` selects the ledger file for every command."""
    parser = argparse.ArgumentParser(
        prog="tally",
        description="A dependency-free, local-first expense ledger.",
    )
    parser.add_argument(
        "--db",
        default=DEFAULT_DB,
        help=f"ledger file to use (default: {DEFAULT_DB})",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    add = commands.add_parser("add", help="record an expense")
    add.add_argument("amount", help="amount spent, e.g. 12.50")
    add.add_argument("--category", "-c", default="general", help="category label (default: general)")
    add.add_argument("--note", "-n", default="", help="short note about the expense")
    add.add_argument("--date", "-d", default=None, help="ISO date (default: today)")

    listing = commands.add_parser("list", help="list expenses, oldest first")
    listing.add_argument("--category", "-c", default=None, help="only this category")

    commands.add_parser("summary", help="show totals per category")

    edit = commands.add_parser("edit", help="change fields of an existing expense")
    edit.add_argument("expense_id", help="id shown by list")
    edit.add_argument("--amount", "-a", default=None, help="new amount, e.g. 12.50")
    edit.add_argument("--category", "-c", default=None, help="new category label")
    edit.add_argument("--note", "-n", default=None, help="new note; an empty value clears it")
    edit.add_argument("--date", "-d", default=None, help="new ISO date, e.g. 2026-10-19")

    remove = commands.add_parser("remove", help="delete an expense by id")
    remove.add_argument("expense_id", help="id shown by list")
    return parser


def run_add(ledger: Ledger, args: argparse.Namespace) -> None:
    """Validate the arguments, record the expense and echo it."""
    expense = ledger.add(
        amount_cents=parse_amount(args.amount),
        category=normalize_category(args.category),
        note=normalize_note(args.note),
        spent_on=parse_date(args.date or date.today().isoformat()),
    )
    note = f"  {expense.note}" if expense.note else ""
    print(
        f"Added #{expense.id}: {format_cents(expense.amount_cents)} "
        f"[{expense.category}] on {expense.spent_on}{note}"
    )


def run_edit(ledger: Ledger, args: argparse.Namespace) -> None:
    """Apply the given fields and echo the updated expense."""
    updated = ledger.edit(
        parse_id(args.expense_id),
        amount_cents=parse_amount(args.amount) if args.amount is not None else None,
        category=normalize_category(args.category) if args.category is not None else None,
        note=normalize_note(args.note) if args.note is not None else None,
        spent_on=parse_date(args.date) if args.date is not None else None,
    )
    note = f"  {updated.note}" if updated.note else ""
    print(
        f"Updated #{updated.id}: {format_cents(updated.amount_cents)} "
        f"[{updated.category}] on {updated.spent_on}{note}"
    )


def run_remove(ledger: Ledger, args: argparse.Namespace) -> None:
    """Delete one expense and echo what was removed."""
    removed = ledger.remove(parse_id(args.expense_id))
    note = f"  {removed.note}" if removed.note else ""
    print(
        f"Removed #{removed.id}: {format_cents(removed.amount_cents)} "
        f"[{removed.category}] on {removed.spent_on}{note}"
    )


def run_list(ledger: Ledger, args: argparse.Namespace) -> None:
    """Print one line per expense, or say the ledger is empty."""
    category = normalize_category(args.category) if args.category else None
    expenses = ledger.entries(category)
    if not expenses:
        print("No expenses recorded.")
        return
    for expense in expenses:
        note = f"  {expense.note}" if expense.note else ""
        print(
            f"#{expense.id:<3} {expense.spent_on}  {format_cents(expense.amount_cents):>10}  "
            f"{expense.category}{note}"
        )


def run_summary(ledger: Ledger) -> None:
    """Print per-category totals and the grand total."""
    totals = ledger.summary()
    if not totals:
        print("No expenses recorded.")
        return
    width = max(len(category) for category in totals)
    for category, cents in totals.items():
        print(f"{category:<{width}}  {format_cents(cents):>10}")
    print(f"{'total':<{width}}  {format_cents(sum(totals.values())):>10}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run one command; user errors print the Why/Fix triad and exit 1."""
    args = build_parser().parse_args(argv)
    ledger = Ledger(StateStore(Path(args.db)))
    try:
        if args.command == "add":
            run_add(ledger, args)
        elif args.command == "edit":
            run_edit(ledger, args)
        elif args.command == "remove":
            run_remove(ledger, args)
        elif args.command == "list":
            run_list(ledger, args)
        else:
            run_summary(ledger)
    except TallyError as error:
        print(error.render(), file=sys.stderr)
        return 1
    return 0
