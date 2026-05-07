"""
メインウィンドウ
サイドバーナビゲーションと各画面の切り替えを管理する
"""

from __future__ import annotations
from datetime import datetime
import customtkinter as ctk

from views.ui_common import (
    COLORS, FONT_NORMAL, FONT_BOLD, FONT_SMALL, FONT_HEADING,
    make_label, make_button, make_frame, make_combobox, make_separator,
    configure_appearance,
)
from views.dashboard_view import DashboardView
from views.sub_views import (
    SalesView, ExpenseView, AccountsView, YojitsuView, SettingsView,
)
from models.account_model import get_fiscal_start_month


NAV_ITEMS = [
    ("dashboard", "ダッシュボード"),
    ("sales",     "売上管理"),
    ("expenses",  "経費管理"),
    ("accounts",  "口座管理"),
    ("yojitsu",   "予実管理"),
    ("settings",  "設定"),
]


class MainWindow(ctk.CTk):
    def __init__(self):
        configure_appearance()
        super().__init__()

        self.title("CashFlow Manager")
        self.geometry("1200x760")
        self.minsize(960, 640)

        now = datetime.now()
        self._year = now.year
        self._month = now.month
        self._fiscal_year = self._calc_fiscal_year(now.year, now.month)
        self._current_screen = "dashboard"
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._active_view: ctk.CTkFrame | None = None

        self._build_layout()
        self._show_screen("dashboard")

    def _calc_fiscal_year(self, year: int, month: int) -> int:
        start_month = get_fiscal_start_month()
        return year if month >= start_month else year - 1

    def _build_layout(self):
        # 左サイドバー
        self._sidebar = make_frame(self, fg_color=COLORS["sidebar"],
                                   corner_radius=0, width=200)
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)

        # ロゴ
        logo = make_frame(self._sidebar, fg_color="transparent")
        logo.pack(fill="x", padx=16, pady=(16, 12))
        make_label(logo, "CashFlow Manager", font=FONT_BOLD).pack(anchor="w")
        make_label(logo, "キャッシュフロー管理", font=FONT_SMALL,
                   text_color=COLORS["text_muted"]).pack(anchor="w")
        make_separator(self._sidebar).pack(fill="x", padx=10)

        # ナビゲーション
        nav_frame = make_frame(self._sidebar, fg_color="transparent")
        nav_frame.pack(fill="x", pady=8)
        for key, label in NAV_ITEMS:
            btn = ctk.CTkButton(
                nav_frame, text=label, anchor="w",
                fg_color="transparent", hover_color=COLORS["border"],
                text_color=COLORS["text"], font=FONT_NORMAL,
                corner_radius=6, height=36,
                command=lambda k=key: self._show_screen(k),
            )
            btn.pack(fill="x", padx=8, pady=1)
            self._nav_buttons[key] = btn

        make_separator(self._sidebar).pack(fill="x", padx=10, side="bottom", pady=(0, 12))

        # メインエリア
        main_frame = make_frame(self, fg_color=COLORS["bg"], corner_radius=0)
        main_frame.pack(side="left", fill="both", expand=True)

        # トップバー
        self._topbar = make_frame(main_frame, fg_color=COLORS["card"],
                                  corner_radius=0, height=52)
        self._topbar.pack(fill="x", side="top")
        self._topbar.pack_propagate(False)

        self._title_label = make_label(self._topbar, "", font=FONT_HEADING)
        self._title_label.pack(side="left", padx=20, pady=12)

        # 年月セレクター
        sel_frame = make_frame(self._topbar, fg_color="transparent")
        sel_frame.pack(side="right", padx=16, pady=8)

        years = [str(y) for y in range(2020, 2035)]
        self._cb_year = make_combobox(sel_frame, years, width=90)
        self._cb_year.set(str(self._fiscal_year))
        self._cb_year.pack(side="left", padx=(0, 4))
        make_label(sel_frame, "年度", font=FONT_SMALL,
                   text_color=COLORS["text_muted"]).pack(side="left", padx=(0, 12))

        months = [f"{m}月" for m in range(1, 13)]
        self._cb_month = make_combobox(sel_frame, months, width=80)
        self._cb_month.set(f"{self._month}月")
        self._cb_month.pack(side="left", padx=(0, 4))
        make_button(
            sel_frame, "表示", command=self._on_period_change,
            width=60, fg_color=COLORS["primary"],
        ).pack(side="left")

        # コンテンツエリア
        self._content = make_frame(main_frame, fg_color=COLORS["bg"], corner_radius=0)
        self._content.pack(fill="both", expand=True)

    def _on_period_change(self):
        try:
            self._fiscal_year = int(self._cb_year.get())
        except ValueError:
            return
        month_str = self._cb_month.get().replace("月", "")
        try:
            self._month = int(month_str)
        except ValueError:
            return
        # 選択した月が年度の何年になるか計算
        start_month = get_fiscal_start_month()
        if self._month >= start_month:
            self._year = self._fiscal_year
        else:
            self._year = self._fiscal_year + 1
        self._show_screen(self._current_screen, force_rebuild=True)

    def _show_screen(self, key: str, force_rebuild: bool = False):
        # ナビボタンの選択状態を更新
        for k, btn in self._nav_buttons.items():
            btn.configure(
                fg_color=COLORS["primary"] if k == key else "transparent",
                text_color="white" if k == key else COLORS["text"],
            )

        title_map = {
            "dashboard": "ダッシュボード",
            "sales":     "売上管理",
            "expenses":  "経費管理",
            "accounts":  "口座管理",
            "yojitsu":   "予実管理",
            "settings":  "設定",
        }
        self._title_label.configure(text=title_map.get(key, key))
        self._current_screen = key

        # 既存ビューを同じキーなら refresh、違うキーなら再生成
        if (
            self._active_view is not None
            and getattr(self._active_view, "_screen_key", None) == key
            and not force_rebuild
        ):
            if hasattr(self._active_view, "refresh"):
                self._active_view.refresh(
                    fiscal_year=self._fiscal_year,
                    year=self._year,
                    month=self._month,
                )
            return

        # 古いビューを破棄
        if self._active_view is not None:
            self._active_view.destroy()

        refresh_cb = lambda: self._show_screen(self._current_screen, force_rebuild=True)

        if key == "dashboard":
            view = DashboardView(self._content, self._fiscal_year, self._year, self._month)
        elif key == "sales":
            view = SalesView(self._content, self._year, self._month, refresh_cb=refresh_cb)
        elif key == "expenses":
            view = ExpenseView(self._content, self._year, self._month, refresh_cb=refresh_cb)
        elif key == "accounts":
            view = AccountsView(self._content, self._year, self._month, refresh_cb=refresh_cb)
        elif key == "yojitsu":
            view = YojitsuView(self._content, self._fiscal_year, refresh_cb=refresh_cb)
        elif key == "settings":
            view = SettingsView(self._content, refresh_cb=refresh_cb)
        else:
            return

        view._screen_key = key
        view.pack(fill="both", expand=True)
        self._active_view = view
