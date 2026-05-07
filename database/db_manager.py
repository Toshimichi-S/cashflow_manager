"""
データベース管理モジュール
SQLiteへの接続・スキーマ初期化・マイグレーションを担当する
セキュリティ: パラメータ化クエリを徹底し、SQLインジェクションを防止する
"""

import sqlite3
import os
import logging
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DB_DIR = Path.home() / "cashflow_manager"
DB_PATH = DB_DIR / "cashflow.db"


def get_db_path() -> Path:
    return DB_PATH


def initialize_database() -> None:
    """DBディレクトリを作成し、スキーマを初期化する"""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    with _get_connection() as conn:
        _create_schema(conn)
        _insert_defaults(conn)
    logger.info(f"Database initialized at {DB_PATH}")


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def get_db():
    """コンテキストマネージャでDB接続を提供し、確実にクローズする"""
    conn = _get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS fiscal_settings (
            id          INTEGER PRIMARY KEY CHECK (id = 1),
            start_month INTEGER NOT NULL DEFAULT 4 CHECK (start_month BETWEEN 1 AND 12),
            created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS categories (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL UNIQUE,
            type       TEXT NOT NULL CHECK (type IN ('sale', 'expense', 'both')),
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS accounts (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            bank_name  TEXT NOT NULL DEFAULT '',
            acct_type  TEXT NOT NULL DEFAULT 'checking',
            color      TEXT NOT NULL DEFAULT '#378ADD',
            sort_order INTEGER NOT NULL DEFAULT 0,
            is_active  INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS account_balances (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id  INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            year        INTEGER NOT NULL,
            month       INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
            balance     REAL NOT NULL DEFAULT 0,
            updated_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            UNIQUE (account_id, year, month)
        );

        CREATE TABLE IF NOT EXISTS sales (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
            sale_type   TEXT NOT NULL DEFAULT 'recurring' CHECK (sale_type IN ('recurring','onetime')),
            base_amount REAL NOT NULL DEFAULT 0 CHECK (base_amount >= 0),
            start_year  INTEGER NOT NULL,
            start_month INTEGER NOT NULL CHECK (start_month BETWEEN 1 AND 12),
            end_year    INTEGER,
            end_month   INTEGER CHECK (end_month BETWEEN 1 AND 12),
            notes       TEXT NOT NULL DEFAULT '',
            is_active   INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
            created_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at  TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS sale_monthly (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id  INTEGER NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
            year     INTEGER NOT NULL,
            month    INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
            planned  REAL CHECK (planned >= 0),
            actual   REAL CHECK (actual >= 0),
            notes    TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            UNIQUE (sale_id, year, month)
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            category_id  INTEGER REFERENCES categories(id) ON DELETE SET NULL,
            expense_type TEXT NOT NULL DEFAULT 'fixed' CHECK (expense_type IN ('fixed','variable')),
            base_amount  REAL NOT NULL DEFAULT 0 CHECK (base_amount >= 0),
            start_year   INTEGER NOT NULL,
            start_month  INTEGER NOT NULL CHECK (start_month BETWEEN 1 AND 12),
            end_year     INTEGER,
            end_month    INTEGER CHECK (end_month BETWEEN 1 AND 12),
            notes        TEXT NOT NULL DEFAULT '',
            is_active    INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0,1)),
            created_at   TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS expense_monthly (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            expense_id INTEGER NOT NULL REFERENCES expenses(id) ON DELETE CASCADE,
            year       INTEGER NOT NULL,
            month      INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
            planned    REAL CHECK (planned >= 0),
            actual     REAL CHECK (actual >= 0),
            notes      TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            UNIQUE (expense_id, year, month)
        );
    """)


def _insert_defaults(conn: sqlite3.Connection) -> None:
    """初回起動時のデフォルトデータを投入する"""
    conn.execute(
        "INSERT OR IGNORE INTO fiscal_settings (id, start_month) VALUES (1, 4)"
    )
    default_categories = [
        ("コンサルティング", "sale"),
        ("システム開発", "sale"),
        ("製品販売", "sale"),
        ("その他売上", "sale"),
        ("人件費", "expense"),
        ("家賃・賃料", "expense"),
        ("通信費", "expense"),
        ("広告費", "expense"),
        ("交通費", "expense"),
        ("消耗品費", "expense"),
        ("その他経費", "expense"),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO categories (name, type) VALUES (?, ?)",
        default_categories,
    )
    conn.commit()
