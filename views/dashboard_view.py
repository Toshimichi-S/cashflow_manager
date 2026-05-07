"""
ダッシュボード画面
予実KPIカード・月別収支グラフ・詳細テーブル・口座残高を表示する
"""

from __future__ import annotations
import tkinter as tk
from datetime import datetime
import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.font_manager as fm

from views.ui_common import (
    COLORS, FONT_NORMAL, FONT_BOLD, FONT_SMALL, FONT_KPI, FONT_HEADING,
    make_label, make_frame, make_separator, fmt_amount, fmt_diff, diff_color,
)
from controllers.cashflow_controller import (
    compute_monthly_summary, compute_annual_summaries,
    get_fiscal_months, detect_negative_months, MonthlySummary,
)
from models.account_model import get_all_balances_for_month, get_fiscal_start_month
from models.sale_model import get_sales_for_month
from models.expense_model import get_expenses_for_month


# matplotlibで日本語フォントを設定
def _setup_mpl_font():
    for fname in fm.findSystemFonts():
        try:
            prop = fm.FontProperties(fname=fname)
            name = prop.get_name()
            if any(jp in name for jp in ["Gothic", "Meiryo", "Hiragino", "Yu Gothic"]):
                plt.rcParams["font.family"] = name
                return
        except Exception:
            pass
    plt.rcParams["font.family"] = "sans-serif"

_setup_mpl_font()
plt.rcParams["axes.unicode_minus"] = False


class DashboardView(ctk.CTkFrame):
    def __init__(self, parent, fiscal_year: int, year: int, month: int):
        super().__init__(parent, fg_color=COLORS["bg"], corner_radius=0)
        self.fiscal_year = fiscal_year
        self.year = year
        self.month = month
        self._build()

    def refresh(self, fiscal_year: int, year: int, month: int):
        self.fiscal_year = fiscal_year
        self.year = year
        self.month = month
        for w in self.winfo_children():
            w.destroy()
        self._build()

    def _build(self):
        summary = compute_monthly_summary(self.year, self.month)
        annual = compute_annual_summaries(self.fiscal_year)
        accounts = get_all_balances_for_month(self.year, self.month)
        sales = get_sales_for_month(self.year, self.month)
        expenses = get_expenses_for_month(self.year, self.month)

        total_balance = sum(a["balance"] for a in accounts)
        negative_months = detect_negative_months(annual, total_balance)

        # スクロール可能コンテナ
        scroll = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        scroll.pack(fill="both", expand=True, padx=0, pady=0)
        content = scroll

        pad = {"padx": 20, "pady": (0, 12)}

        # ─── マイナス警告 ─────────────────────────────────
        if negative_months:
            labels = ", ".join(f"{y}年{m}月" for y, m in negative_months[:3])
            alert = make_frame(content, fg_color=COLORS["warning_lt"], corner_radius=6)
            alert.pack(fill="x", padx=20, pady=(16, 0))
            make_label(
                alert,
                f"⚠  {labels}：口座残高がマイナスになる見込みです",
                font=FONT_SMALL,
                text_color=COLORS["warning"],
            ).pack(padx=12, pady=8, anchor="w")

        # ─── 予実KPIカード ────────────────────────────────
        kpi_row = make_frame(content, fg_color="transparent")
        kpi_row.pack(fill="x", padx=20, pady=(16, 0))
        kpi_row.columnconfigure((0, 1, 2), weight=1)

        self._kpi_card(kpi_row, 0, "今月の売上",
                       summary.sale_planned, summary.sale_actual, positive_good=True)
        self._kpi_card(kpi_row, 1, "今月の経費",
                       summary.expense_planned, summary.expense_actual, positive_good=False)
        self._kpi_card(kpi_row, 2, "今月の収支",
                       summary.profit_planned, summary.profit_actual, positive_good=True)

        # ─── 月別収支グラフ ────────────────────────────────
        chart_card = make_frame(content, corner_radius=8)
        chart_card.pack(fill="x", padx=20, pady=(16, 12))
        make_label(
            chart_card, "月別収支 — 予定 vs 実績",
            font=FONT_BOLD, text_color=COLORS["text_muted"],
        ).pack(anchor="w", padx=14, pady=(10, 4))
        self._draw_bar_chart(chart_card, annual)

        # ─── 詳細テーブル（売上・経費） ──────────────────
        two_col = make_frame(content, fg_color="transparent")
        two_col.pack(fill="x", **pad)
        two_col.columnconfigure((0, 1), weight=1)

        self._detail_table(two_col, 0, "売上 詳細", sales, kind="sale")
        self._detail_table(two_col, 1, "経費 詳細", expenses, kind="expense")

        # ─── 口座残高 ─────────────────────────────────────
        acct_card = make_frame(content, corner_radius=8)
        acct_card.pack(fill="x", **pad)
        make_label(
            acct_card, "口座残高（今月）",
            font=FONT_BOLD, text_color=COLORS["text_muted"],
        ).pack(anchor="w", padx=14, pady=(10, 4))
        self._account_row(acct_card, accounts)

        # 下余白
        make_frame(content, fg_color="transparent", height=20).pack()

    def _kpi_card(self, parent, col: int, title: str,
                  planned: float, actual: float, positive_good: bool):
        card = make_frame(parent, corner_radius=8)
        card.grid(row=0, column=col, sticky="nsew", padx=(0, 8) if col < 2 else 0)

        make_label(card, title, font=FONT_SMALL, text_color=COLORS["text_muted"]).pack(
            anchor="w", padx=14, pady=(12, 4)
        )
        # 予定
        make_label(card, f"予定  {fmt_amount(planned)}",
                   font=FONT_SMALL, text_color=COLORS["text_muted"]).pack(anchor="w", padx=14)
        # 実績
        actual_color = diff_color(actual - planned, positive_good) if actual != 0 else COLORS["text_muted"]
        make_label(card, f"実績  {fmt_amount(actual)}",
                   font=("Yu Gothic UI", 18, "bold"),
                   text_color=actual_color if actual != 0 else COLORS["text_muted"],
                   ).pack(anchor="w", padx=14, pady=(2, 0))
        # 差異
        diff = actual - planned
        diff_str = fmt_diff(diff)
        diff_col = diff_color(diff, positive_good)
        pct = f"（{diff / planned * 100:+.1f}%）" if planned != 0 else ""
        make_label(card, f"予定比 {diff_str} {pct}",
                   font=FONT_SMALL, text_color=diff_col).pack(anchor="w", padx=14, pady=(2, 12))

    def _draw_bar_chart(self, parent, summaries: list[MonthlySummary]):
        fig, ax = plt.subplots(figsize=(9, 2.4), dpi=96)
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")

        fiscal_months = get_fiscal_months(self.fiscal_year)
        labels = [f"{m}月" for _, m in fiscal_months]
        x = range(len(summaries))
        bar_w = 0.35

        plans = [s.profit_planned for s in summaries]
        actuals = [s.profit_actual if s.has_actual else None for s in summaries]

        # 予定バー（薄い青）
        ax.bar([i - bar_w / 2 for i in x], plans, bar_w,
               color="#B5D4F4", label="予定", zorder=2)
        # 実績バー（緑/赤）
        for i, val in enumerate(actuals):
            if val is not None:
                color = COLORS["success"] if val >= 0 else COLORS["danger"]
                ax.bar(i + bar_w / 2, val, bar_w, color=color, zorder=2)

        ax.axhline(0, color="#AAAAAA", linewidth=0.8, zorder=1)
        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, fontsize=9)
        ax.yaxis.set_major_formatter(
            matplotlib.ticker.FuncFormatter(lambda v, _: f"{int(v/10000)}万")
        )
        ax.tick_params(axis="both", labelsize=9, colors="#888888")
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.spines["bottom"].set_color("#EEEEEE")
        ax.grid(axis="y", color="#EEEEEE", linewidth=0.5, zorder=0)
        ax.legend(fontsize=8, loc="upper right", framealpha=0)

        fig.tight_layout(pad=0.4)
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="x", padx=14, pady=(0, 10))
        plt.close(fig)

    def _detail_table(self, parent, col: int, title: str, rows: list[dict], kind: str):
        card = make_frame(parent, corner_radius=8)
        card.grid(row=0, column=col, sticky="nsew", padx=(0, 8) if col == 0 else 0)
        make_label(card, title, font=FONT_BOLD, text_color=COLORS["text_muted"]).pack(
            anchor="w", padx=12, pady=(10, 4)
        )

        # ヘッダ
        hdr = make_frame(card, fg_color=COLORS["bg"], corner_radius=0)
        hdr.pack(fill="x", padx=12)
        hdr.columnconfigure(0, weight=1)
        hdr.columnconfigure((1, 2, 3), minsize=80)
        for ci, text in enumerate(["項目", "予定", "実績", "差異"]):
            make_label(hdr, text, font=FONT_SMALL,
                       text_color=COLORS["text_muted"]).grid(
                row=0, column=ci, sticky="w" if ci == 0 else "e", padx=4, pady=3
            )
        make_separator(card).pack(fill="x", padx=12)

        def _effective_planned(r):
            return r["planned"] if r["planned"] is not None else r["base_amount"]

        total_plan = total_act = 0.0
        for r in rows:
            plan = _effective_planned(r)
            act = r["actual"]
            total_plan += plan
            if act is not None:
                total_act += act

            diff = (act - plan) if act is not None else None

            row_fr = make_frame(card, fg_color="transparent", corner_radius=0)
            row_fr.pack(fill="x", padx=12)
            row_fr.columnconfigure(0, weight=1)
            row_fr.columnconfigure((1, 2, 3), minsize=80)

            # 項目名（長い場合は省略）
            name = r["name"][:14] + "…" if len(r["name"]) > 14 else r["name"]
            make_label(row_fr, name, font=FONT_SMALL).grid(row=0, column=0, sticky="w", padx=4, pady=2)
            make_label(row_fr, fmt_amount(plan), font=FONT_SMALL,
                       text_color=COLORS["text_muted"]).grid(row=0, column=1, sticky="e", padx=4)
            act_str = fmt_amount(act) if act is not None else "—"
            make_label(row_fr, act_str, font=FONT_SMALL).grid(row=0, column=2, sticky="e", padx=4)
            if diff is not None:
                dc = diff_color(diff, positive_good=(kind == "sale"))
                make_label(row_fr, fmt_diff(diff), font=FONT_SMALL,
                           text_color=dc).grid(row=0, column=3, sticky="e", padx=4)
            else:
                make_label(row_fr, "—", font=FONT_SMALL,
                           text_color=COLORS["text_muted"]).grid(row=0, column=3, sticky="e", padx=4)
            make_separator(card).pack(fill="x", padx=12)

        # 合計行
        total_diff = total_act - total_plan
        tot_fr = make_frame(card, fg_color=COLORS["bg"], corner_radius=0)
        tot_fr.pack(fill="x", padx=12, pady=(0, 10))
        tot_fr.columnconfigure(0, weight=1)
        tot_fr.columnconfigure((1, 2, 3), minsize=80)
        make_label(tot_fr, "合計", font=FONT_BOLD).grid(row=0, column=0, sticky="w", padx=4, pady=3)
        make_label(tot_fr, fmt_amount(total_plan), font=FONT_BOLD,
                   text_color=COLORS["text_muted"]).grid(row=0, column=1, sticky="e", padx=4)
        make_label(tot_fr, fmt_amount(total_act), font=FONT_BOLD).grid(row=0, column=2, sticky="e", padx=4)
        dc = diff_color(total_diff, positive_good=(kind == "sale"))
        make_label(tot_fr, fmt_diff(total_diff), font=FONT_BOLD,
                   text_color=dc).grid(row=0, column=3, sticky="e", padx=4)

    def _account_row(self, parent, accounts: list[dict]):
        row = make_frame(parent, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(0, 12))

        total = sum(a["balance"] for a in accounts)
        all_accounts = accounts + [{"name": "合計残高", "bank_name": "", "balance": total, "color": "#185FA5"}]

        for acct in all_accounts:
            bal = acct["balance"]
            card = make_frame(row, corner_radius=6)
            card.pack(side="left", fill="both", expand=True, padx=(0, 8))

            make_label(card, acct["name"], font=FONT_SMALL,
                       text_color=COLORS["text_muted"]).pack(anchor="w", padx=10, pady=(8, 2))
            col = COLORS["danger"] if bal < 0 else COLORS["text"]
            make_label(card, f"{fmt_amount(bal)} 円", font=FONT_BOLD,
                       text_color=col).pack(anchor="w", padx=10, pady=(0, 8))
