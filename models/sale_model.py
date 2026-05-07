"""
売上データアクセスオブジェクト
全クエリはパラメータ化クエリを使用する
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from database.db_manager import get_db


@dataclass
class Sale:
    id: Optional[int]
    name: str
    category_id: Optional[int]
    sale_type: str          # 'recurring' | 'onetime'
    base_amount: float
    start_year: int
    start_month: int
    end_year: Optional[int] = None
    end_month: Optional[int] = None
    notes: str = ""
    is_active: int = 1
    category_name: str = ""


@dataclass
class SaleMonthly:
    sale_id: int
    year: int
    month: int
    planned: Optional[float]
    actual: Optional[float]
    notes: str = ""


def get_all_sales(active_only: bool = True) -> list[Sale]:
    sql = """
        SELECT s.*, c.name AS category_name
        FROM sales s
        LEFT JOIN categories c ON s.category_id = c.id
        WHERE (:active_only = 0 OR s.is_active = 1)
        ORDER BY s.id
    """
    with get_db() as conn:
        rows = conn.execute(sql, {"active_only": int(active_only)}).fetchall()
    return [_row_to_sale(r) for r in rows]


def get_sales_for_month(year: int, month: int) -> list[dict]:
    """指定月に有効な売上と月別データを結合して返す"""
    sql = """
        SELECT
            s.id, s.name, s.category_id, s.sale_type, s.base_amount,
            s.start_year, s.start_month, s.end_year, s.end_month, s.notes,
            c.name AS category_name,
            sm.planned, sm.actual, sm.notes AS monthly_notes
        FROM sales s
        LEFT JOIN categories c ON s.category_id = c.id
        LEFT JOIN sale_monthly sm
            ON sm.sale_id = s.id AND sm.year = :year AND sm.month = :month
        WHERE s.is_active = 1
          AND (s.start_year < :year OR (s.start_year = :year AND s.start_month <= :month))
          AND (
              s.end_year IS NULL
              OR s.end_year > :year
              OR (s.end_year = :year AND s.end_month >= :month)
          )
          AND (s.sale_type = 'recurring'
               OR (s.start_year = :year AND s.start_month = :month))
        ORDER BY s.id
    """
    with get_db() as conn:
        rows = conn.execute(sql, {"year": year, "month": month}).fetchall()
    return [dict(r) for r in rows]


def upsert_sale(sale: Sale) -> int:
    sql_insert = """
        INSERT INTO sales (name, category_id, sale_type, base_amount,
                           start_year, start_month, end_year, end_month, notes, is_active,
                           updated_at)
        VALUES (:name, :category_id, :sale_type, :base_amount,
                :start_year, :start_month, :end_year, :end_month, :notes, :is_active,
                datetime('now','localtime'))
    """
    sql_update = """
        UPDATE sales SET
            name=:name, category_id=:category_id, sale_type=:sale_type,
            base_amount=:base_amount, start_year=:start_year, start_month=:start_month,
            end_year=:end_year, end_month=:end_month, notes=:notes, is_active=:is_active,
            updated_at=datetime('now','localtime')
        WHERE id=:id
    """
    params = {
        "id": sale.id, "name": sale.name, "category_id": sale.category_id,
        "sale_type": sale.sale_type, "base_amount": sale.base_amount,
        "start_year": sale.start_year, "start_month": sale.start_month,
        "end_year": sale.end_year, "end_month": sale.end_month,
        "notes": sale.notes, "is_active": sale.is_active,
    }
    with get_db() as conn:
        if sale.id is None:
            cur = conn.execute(sql_insert, params)
            return cur.lastrowid
        else:
            conn.execute(sql_update, params)
            return sale.id


def delete_sale(sale_id: int) -> None:
    with get_db() as conn:
        conn.execute("UPDATE sales SET is_active=0 WHERE id=?", (sale_id,))


def upsert_sale_monthly(sm: SaleMonthly) -> None:
    sql = """
        INSERT INTO sale_monthly (sale_id, year, month, planned, actual, notes, updated_at)
        VALUES (:sale_id, :year, :month, :planned, :actual, :notes, datetime('now','localtime'))
        ON CONFLICT(sale_id, year, month) DO UPDATE SET
            planned=excluded.planned,
            actual=excluded.actual,
            notes=excluded.notes,
            updated_at=excluded.updated_at
    """
    with get_db() as conn:
        conn.execute(sql, {
            "sale_id": sm.sale_id, "year": sm.year, "month": sm.month,
            "planned": sm.planned, "actual": sm.actual, "notes": sm.notes,
        })


def _row_to_sale(row) -> Sale:
    return Sale(
        id=row["id"], name=row["name"], category_id=row["category_id"],
        sale_type=row["sale_type"], base_amount=row["base_amount"],
        start_year=row["start_year"], start_month=row["start_month"],
        end_year=row["end_year"], end_month=row["end_month"],
        notes=row["notes"], is_active=row["is_active"],
        category_name=row["category_name"] or "",
    )
