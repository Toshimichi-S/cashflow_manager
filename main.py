"""
CashFlow Manager — エントリーポイント
実行: python main.py
"""

import sys
import os
import logging

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from database.db_manager import initialize_database
from views.main_window import MainWindow


def main():
    # DB初期化（初回のみスキーマ作成）
    initialize_database()

    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
