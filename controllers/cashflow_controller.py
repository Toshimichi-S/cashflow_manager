"""
収支集計・年間シミュレーションコントローラ
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from models.sale_model import get_sales_for_month
from models.expense_model import get_expenses_for_month
from models.account_model import get_fiscal_start_month


@dataclass
class MonthlySummary:
    year: int
    month: int
    sale_planned: float = 0.0
    sale_actual: float = 0.0
    expense_planned: float = 0.0
    expense_actual: float = 0.0

    @property
    def profit_planned(self) -> float:
        return self.sale_planned - self.expense_planned

    @property
    def profit_actual(self) -> float:
        return self.sale_actual - self.expense_actual

    @property
    def sale_diff(self) -> float:
        return self.sale_actual - self.sale_planned

    @property
    def expense_diff(self) -> float:
        return self.expense_planned - self.expense_actual

    @property
    def has_actual(self) -> bool:
        return self.sale_actual > 0 or self.expense_actual > 0


def _effective_planned(row: dict) -> float:
    return row["planned"] if row["planned"] is not None else row["base_amount"]


def compute_monthly_summary(year: int, month: int) -> MonthlySummary:
    sales = get_sales_for_month(year, month)
    expenses = get_expenses_for_month(year, month)

    sale_planned = sum(_effective_planned(r) for r in sales)
    sale_actual = sum(r["actual"] for r in sales if r["actual"] is not None)
    expense_planned = sum(_effective_planned(r) for r in expenses)
    expense_actual = sum(r["actual"] for r in expenses if r["actual"] is not None)

    return MonthlySummary(
        year=year, month=month,
        sale_planned=sale_planned, sale_actual=sale_actual,
        expense_planned=expense_planned, expense_actual=expense_actual,
    )


def get_fiscal_months(fiscal_year: int) -> list[tuple[int, int]]:
    start_month = get_fiscal_start_month()
    months = []
    for i in range(12):
        m = (start_month - 1 + i) % 12 + 1
        y = fiscal_year + ((start_month - 1 + i) // 12)
        months.append((y, m))
    return months


def compute_annual_summaries(fiscal_year: int) -> list[MonthlySummary]:
    return [compute_monthly_summary(y, m) for y, m in get_fiscal_months(fiscal_year)]


def detect_negative_months(
    summaries: list[MonthlySummary],
    account_balance: float,
) -> list[tuple[int, int]]:
    negative_months = []
    balance = account_balance
    for s in summaries:
        balance += s.profit_planned
        if balance < 0:
            negative_months.append((s.year, s.month))
    return negative_months
