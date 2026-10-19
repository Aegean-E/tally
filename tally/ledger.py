"""Expense operations: the one place that assigns ids and computes category totals."""

from typing import Dict, List, Optional

from tally.errors import TallyError
from tally.models import Expense
from tally.storage import StateStore


class Ledger:
    """Add and read expenses through a `StateStore`; it owns no storage logic itself."""

    def __init__(self, store: StateStore):
        self._store = store

    def add(self, amount_cents: int, category: str, note: str, spent_on: str) -> Expense:
        """Record one expense with the next free id."""
        def append(expenses: List[Expense]) -> List[Expense]:
            next_id = max((expense.id for expense in expenses), default=0) + 1
            return [*expenses, Expense(next_id, amount_cents, category, note, spent_on)]

        updated = self._store.update(append)
        return updated[-1]

    def edit(
        self,
        expense_id: int,
        amount_cents: Optional[int] = None,
        category: Optional[str] = None,
        note: Optional[str] = None,
        spent_on: Optional[str] = None,
    ) -> Expense:
        """Change the given fields of one expense, keeping every other field."""
        if all(value is None for value in (amount_cents, category, note, spent_on)):
            raise TallyError(
                "No change requested.",
                "edit needs at least one field to change.",
                "pass --amount, --category, --note or --date.",
            )
        edited: List[Expense] = []

        def change(expenses: List[Expense]) -> List[Expense]:
            for index, expense in enumerate(expenses):
                if expense.id == expense_id:
                    updated = Expense(
                        expense.id,
                        expense.amount_cents if amount_cents is None else amount_cents,
                        expense.category if category is None else category,
                        expense.note if note is None else note,
                        expense.spent_on if spent_on is None else spent_on,
                    )
                    edited.append(updated)
                    return [*expenses[:index], updated, *expenses[index + 1:]]
            raise self._missing(expense_id)

        self._store.update(change)
        return edited[0]

    def remove(self, expense_id: int) -> Expense:
        """Delete one expense and return it."""
        removed: List[Expense] = []

        def drop(expenses: List[Expense]) -> List[Expense]:
            for index, expense in enumerate(expenses):
                if expense.id == expense_id:
                    removed.append(expense)
                    return [*expenses[:index], *expenses[index + 1:]]
            raise self._missing(expense_id)

        self._store.update(drop)
        return removed[0]

    @staticmethod
    def _missing(expense_id: int) -> TallyError:
        """The triad for an id the ledger does not contain."""
        return TallyError(
            f"Expense #{expense_id} does not exist.",
            "the ledger only has the ids that `tally list` shows.",
            "run `tally list` to find the id, then retry.",
        )

    def entries(
        self,
        category: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> List[Expense]:
        """Every expense, oldest first, optionally narrowed to one category or date range."""
        expenses = self._store.read()
        if category is not None:
            expenses = [expense for expense in expenses if expense.category == category]
        if from_date is not None:
            expenses = [expense for expense in expenses if expense.spent_on >= from_date]
        if to_date is not None:
            expenses = [expense for expense in expenses if expense.spent_on <= to_date]
        return sorted(expenses, key=lambda expense: (expense.spent_on, expense.id))

    def summary(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> Dict[str, int]:
        """Total cents per category, with categories in alphabetical order."""
        totals: Dict[str, int] = {}
        for expense in self.entries(from_date=from_date, to_date=to_date):
            totals[expense.category] = totals.get(expense.category, 0) + expense.amount_cents
        return dict(sorted(totals.items()))

    def total(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> int:
        """Total cents across every category in the given date range."""
        return sum(self.summary(from_date=from_date, to_date=to_date).values())
