"""
経費データアクセスオブジェクト
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from database.db_manager import get_db


@dataclass
class Expense:
    id: Optional[int]
    name: str
    category_id: Optional[int]
    expense_type: str       # 'fixed' | 'variable'
    base_amount: float
    start_year: int
    start_month: int
    end_year: Optional[int] = None
    end_month: Optional[int] = None
    notes: str = ""
    is_active: int = 1
    category_name: str = ""


@dataclass
class ExpenseMonthly:
    expense_id: int
    year: int
    month: int
    planned: Optional[float]
    actual: Optional[float]
    notes: str = ""


def get_all_expenses(active_only: bool = True) -> list[Expense]:
    sql = """
        SELECT e.*, c.name AS category_name
        FROM expenses e
        LEFT JOIN categories c ON e.category_id = c.id
        WHERE (:active_only = 0 OR e.is_active = 1)
        ORDER BY e.id
    """
    with get_db() as conn:
        rows = conn.execute(sql, {"active_only": int(active_only)}).fetchall()
    return [_row_to_expense(r) for r in rows]


def get_expenses_for_month(year: int, month: int) -> list[dict]:
    sql = """
        SELECT
            e.id, e.name, e.category_id, e.expense_type, e.base_amount,
            e.start_year, e.start_month, e.end_year, e.end_month, e.notes,
            c.name AS category_name,
            em.planned, em.actual, em.notes AS monthly_notes
        FROM expenses e
        LEFT JOIN categories c ON e.category_id = c.id
        LEFT JOIN expense_monthly em
            ON em.expense_id = e.id AND em.year = :year AND em.month = :month
        WHERE e.is_active = 1
          AND (e.start_year < :year OR (e.start_year = :year AND e.start_month <= :month))
          AND (
              e.end_year IS NULL
              OR e.end_year > :year
              OR (e.end_year = :year AND e.end_month >= :month)
          )
        ORDER BY e.expense_type DESC, e.id
    """
    with get_db() as conn:
        rows = conn.execute(sql, {"year": year, "month": month}).fetchall()
    return [dict(r) for r in rows]


def upsert_expense(expense: Expense) -> int:
    sql_insert = """
        INSERT INTO expenses (name, category_id, expense_type, base_amount,
                              start_year, start_month, end_year, end_month, notes, is_active,
                              updated_at)
        VALUES (:name, :category_id, :expense_type, :base_amount,
                :start_year, :start_month, :end_year, :end_month, :notes, :is_active,
                datetime('now','localtime'))
    """
    sql_update = """
        UPDATE expenses SET
            name=:name, category_id=:category_id, expense_type=:expense_type,
            base_amount=:base_amount, start_year=:start_year, start_month=:start_month,
            end_year=:end_year, end_month=:end_month, notes=:notes, is_active=:is_active,
            updated_at=datetime('now','localtime')
        WHERE id=:id
    """
    params = {
        "id": expense.id, "name": expense.name, "category_id": expense.category_id,
        "expense_type": expense.expense_type, "base_amount": expense.base_amount,
        "start_year": expense.start_year, "start_month": expense.start_month,
        "end_year": expense.end_year, "end_month": expense.end_month,
        "notes": expense.notes, "is_active": expense.is_active,
    }
    with get_db() as conn:
        if expense.id is None:
            cur = conn.execute(sql_insert, params)
            return cur.lastrowid
        else:
            conn.execute(sql_update, params)
            return expense.id


def delete_expense(expense_id: int) -> None:
    with get_db() as conn:
        conn.execute("UPDATE expenses SET is_active=0 WHERE id=?", (expense_id,))


def upsert_expense_monthly(em: ExpenseMonthly) -> None:
    sql = """
        INSERT INTO expense_monthly (expense_id, year, month, planned, actual, notes, updated_at)
        VALUES (:expense_id, :year, :month, :planned, :actual, :notes, datetime('now','localtime'))
        ON CONFLICT(expense_id, year, month) DO UPDATE SET
            planned=excluded.planned,
            actual=excluded.actual,
            notes=excluded.notes,
            updated_at=excluded.updated_at
    """
    with get_db() as conn:
        conn.execute(sql, {
            "expense_id": em.expense_id, "year": em.year, "month": em.month,
            "planned": em.planned, "actual": em.actual, "notes": em.notes,
        })


def _row_to_expense(row) -> Expense:
    return Expense(
        id=row["id"], name=row["name"], category_id=row["category_id"],
        expense_type=row["expense_type"], base_amount=row["base_amount"],
        start_year=row["start_year"], start_month=row["start_month"],
        end_year=row["end_year"], end_month=row["end_month"],
        notes=row["notes"], is_active=row["is_active"],
        category_name=row["category_name"] or "",
    )
