"""Expense operations: the one place that assigns ids and computes category totals."""

from typing import Dict, List, Optional

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

    def entries(self, category: Optional[str] = None) -> List[Expense]:
        """Every expense, oldest first, optionally narrowed to one normalized category."""
        expenses = self._store.read()
        if category is not None:
            expenses = [expense for expense in expenses if expense.category == category]
        return sorted(expenses, key=lambda expense: (expense.spent_on, expense.id))

    def summary(self) -> Dict[str, int]:
        """Total cents per category, with categories in alphabetical order."""
        totals: Dict[str, int] = {}
        for expense in self._store.read():
            totals[expense.category] = totals.get(expense.category, 0) + expense.amount_cents
        return dict(sorted(totals.items()))

    def total(self) -> int:
        """Total cents across every category."""
        return sum(self.summary().values())
