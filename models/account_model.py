"""
口座・カテゴリ・設定データアクセスオブジェクト
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from database.db_manager import get_db


# ─── 口座 ──────────────────────────────────────────────

@dataclass
class Account:
    id: Optional[int]
    name: str
    bank_name: str
    acct_type: str = "checking"
    color: str = "#378ADD"
    sort_order: int = 0
    is_active: int = 1


def get_all_accounts() -> list[Account]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM accounts WHERE is_active=1 ORDER BY sort_order, id"
        ).fetchall()
    return [Account(**dict(r)) for r in rows]


def upsert_account(account: Account) -> int:
    sql_insert = """
        INSERT INTO accounts (name, bank_name, acct_type, color, sort_order, is_active, updated_at)
        VALUES (:name, :bank_name, :acct_type, :color, :sort_order, :is_active,
                datetime('now','localtime'))
    """
    sql_update = """
        UPDATE accounts SET
            name=:name, bank_name=:bank_name, acct_type=:acct_type,
            color=:color, sort_order=:sort_order, is_active=:is_active,
            updated_at=datetime('now','localtime')
        WHERE id=:id
    """
    params = {
        "id": account.id, "name": account.name, "bank_name": account.bank_name,
        "acct_type": account.acct_type, "color": account.color,
        "sort_order": account.sort_order, "is_active": account.is_active,
    }
    with get_db() as conn:
        if account.id is None:
            cur = conn.execute(sql_insert, params)
            return cur.lastrowid
        else:
            conn.execute(sql_update, params)
            return account.id


def delete_account(account_id: int) -> None:
    with get_db() as conn:
        conn.execute("UPDATE accounts SET is_active=0 WHERE id=?", (account_id,))


def get_balance(account_id: int, year: int, month: int) -> Optional[float]:
    with get_db() as conn:
        row = conn.execute(
            "SELECT balance FROM account_balances WHERE account_id=? AND year=? AND month=?",
            (account_id, year, month),
        ).fetchone()
    return row["balance"] if row else None


def set_balance(account_id: int, year: int, month: int, balance: float) -> None:
    sql = """
        INSERT INTO account_balances (account_id, year, month, balance, updated_at)
        VALUES (?, ?, ?, ?, datetime('now','localtime'))
        ON CONFLICT(account_id, year, month) DO UPDATE SET
            balance=excluded.balance,
            updated_at=excluded.updated_at
    """
    with get_db() as conn:
        conn.execute(sql, (account_id, year, month, balance))


def get_all_balances_for_month(year: int, month: int) -> list[dict]:
    sql = """
        SELECT a.id, a.name, a.bank_name, a.color,
               COALESCE(ab.balance, 0) AS balance
        FROM accounts a
        LEFT JOIN account_balances ab
            ON ab.account_id = a.id AND ab.year = ? AND ab.month = ?
        WHERE a.is_active = 1
        ORDER BY a.sort_order, a.id
    """
    with get_db() as conn:
        rows = conn.execute(sql, (year, month)).fetchall()
    return [dict(r) for r in rows]


# ─── カテゴリ ───────────────────────────────────────────

@dataclass
class Category:
    id: Optional[int]
    name: str
    type: str   # 'sale' | 'expense' | 'both'


def get_categories(cat_type: Optional[str] = None) -> list[Category]:
    if cat_type:
        sql = "SELECT * FROM categories WHERE type=? OR type='both' ORDER BY name"
        params = (cat_type,)
    else:
        sql = "SELECT * FROM categories ORDER BY type, name"
        params = ()
    with get_db() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [Category(id=r["id"], name=r["name"], type=r["type"]) for r in rows]


def upsert_category(cat: Category) -> int:
    with get_db() as conn:
        if cat.id is None:
            cur = conn.execute(
                "INSERT OR IGNORE INTO categories (name, type) VALUES (?, ?)",
                (cat.name, cat.type),
            )
            return cur.lastrowid
        else:
            conn.execute(
                "UPDATE categories SET name=?, type=? WHERE id=?",
                (cat.name, cat.type, cat.id),
            )
            return cat.id


def delete_category(category_id: int) -> None:
    with get_db() as conn:
        conn.execute("DELETE FROM categories WHERE id=?", (category_id,))


# ─── 設定 ───────────────────────────────────────────────

def get_fiscal_start_month() -> int:
    with get_db() as conn:
        row = conn.execute("SELECT start_month FROM fiscal_settings WHERE id=1").fetchone()
    return row["start_month"] if row else 4


def set_fiscal_start_month(month: int) -> None:
    with get_db() as conn:
        conn.execute(
            "INSERT INTO fiscal_settings (id, start_month) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET start_month=excluded.start_month, "
            "updated_at=datetime('now','localtime')",
            (month,),
        )
