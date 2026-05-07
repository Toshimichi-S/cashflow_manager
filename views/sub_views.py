"""
サブ画面群（売上管理・経費管理・口座管理・予実管理・レポート・設定）
"""

from __future__ import annotations
import tkinter as tk
from tkinter import messagebox, filedialog
import customtkinter as ctk
from datetime import datetime

from views.ui_common import (
    COLORS, FONT_NORMAL, FONT_BOLD, FONT_SMALL, FONT_HEADING,
    make_label, make_button, make_frame, make_entry, make_combobox, make_separator,
    fmt_amount, fmt_diff, diff_color,
)
from views.dialogs import SaleDialog, ExpenseDialog
from models.sale_model import get_sales_for_month, delete_sale, get_all_sales
from models.expense_model import get_expenses_for_month, delete_expense, get_all_expenses
from models.account_model import (
    get_all_accounts, upsert_account, delete_account,
    get_all_balances_for_month, set_balance, Account,
    get_categories, upsert_category, delete_category, Category,
    get_fiscal_start_month, set_fiscal_start_month,
)
from controllers.cashflow_controller import compute_annual_summaries, get_fiscal_months
from utils.export import export_annual_csv, export_annual_excel, backup_database, restore_database


def _fixed_label(parent, text: str, width: int, font=None, text_color=None, **kwargs) -> ctk.CTkLabel:
    """固定幅ラベルを生成する（width は CTkLabel のコンストラクタに渡す）"""
    return ctk.CTkLabel(
        parent, text=text, width=width, anchor="w",
        font=font or FONT_NORMAL,
        text_color=text_color or COLORS["text"],
        **kwargs,
    )


# ─── 売上管理画面 ─────────────────────────────────────

class SalesView(ctk.CTkFrame):
    def __init__(self, parent, year: int, month: int, refresh_cb=None):
        super().__init__(parent, fg_color=COLORS["bg"], corner_radius=0)
        self.year = year
        self.month = month
        self.refresh_cb = refresh_cb
        self._build()

    def refresh(self, year: int, month: int, **_):
        self.year = year
        self.month = month
        for w in self.winfo_children():
            w.destroy()
        self._build()

    def _build(self):
        rows = get_sales_for_month(self.year, self.month)
        total_plan = sum((r["planned"] or r["base_amount"]) for r in rows)

        # ── ツールバー ──
        tb = make_frame(self, fg_color="transparent")
        tb.pack(fill="x", padx=20, pady=(16, 8))
        make_button(tb, "+ 売上を追加", command=self._add, width=130).pack(side="left")
        make_label(
            tb, f"{self.year}年{self.month}月  合計（予定）: {fmt_amount(total_plan)} 円",
            font=FONT_SMALL, text_color=COLORS["text_muted"],
        ).pack(side="right")

        # ── テーブルカード ──
        card = make_frame(self, corner_radius=8)
        card.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # ヘッダ行
        col_defs = [("名称", 180), ("カテゴリ", 120), ("種別", 70),
                    ("予定金額", 100), ("実績金額", 100), ("差異", 90),
                    ("メモ", 140), ("", 60)]
        hdr = make_frame(card, fg_color=COLORS["bg"], corner_radius=0)
        hdr.pack(fill="x", padx=12, pady=4)
        for text, w in col_defs:
            _fixed_label(hdr, text, w, font=FONT_SMALL,
                         text_color=COLORS["text_muted"]).pack(side="left")
        make_separator(card).pack(fill="x", padx=12)

        scroll = ctk.CTkScrollableFrame(card, fg_color="white", corner_radius=0)
        scroll.pack(fill="both", expand=True)

        if not rows:
            make_label(scroll, "データがありません。「+ 売上を追加」から登録してください。",
                       font=FONT_NORMAL, text_color=COLORS["text_muted"]).pack(pady=40)
            return

        for r in rows:
            plan = r["planned"] if r["planned"] is not None else r["base_amount"]
            act  = r["actual"]
            diff = (act - plan) if act is not None else None

            row_fr = make_frame(scroll, fg_color="transparent", corner_radius=0)
            row_fr.pack(fill="x")

            badge_text = "継続" if r["sale_type"] == "recurring" else "単発"
            badge_tc   = "#185FA5" if r["sale_type"] == "recurring" else "#3B6D11"

            _fixed_label(row_fr, r["name"][:18], 180).pack(side="left", padx=(12, 0))
            _fixed_label(row_fr, r["category_name"] or "—", 120,
                         font=FONT_SMALL, text_color=COLORS["text_muted"]).pack(side="left")
            _fixed_label(row_fr, badge_text, 70,
                         font=FONT_SMALL, text_color=badge_tc).pack(side="left")
            _fixed_label(row_fr, fmt_amount(plan), 100,
                         font=FONT_NORMAL, text_color=COLORS["text_muted"],
                         anchor="e").pack(side="left")
            _fixed_label(row_fr, fmt_amount(act) if act is not None else "—", 100,
                         anchor="e").pack(side="left")
            if diff is not None:
                _fixed_label(row_fr, fmt_diff(diff), 90, font=FONT_SMALL,
                             text_color=diff_color(diff, True), anchor="e").pack(side="left")
            else:
                _fixed_label(row_fr, "未入力", 90, font=FONT_SMALL,
                             text_color=COLORS["text_muted"]).pack(side="left")
            _fixed_label(row_fr, r["monthly_notes"] or r["notes"] or "—", 140,
                         font=FONT_SMALL, text_color=COLORS["text_muted"]).pack(side="left")

            sale_id = r["id"]
            make_button(row_fr, "編集", command=lambda sid=sale_id: self._edit(sid),
                        width=55, fg_color=COLORS["bg"], hover_color=COLORS["border"],
                        text_color=COLORS["text"]).pack(side="left", padx=4)
            make_separator(scroll).pack(fill="x", padx=12)

    def _add(self):
        SaleDialog(self, on_save=self._on_save)

    def _edit(self, sale_id: int):
        all_sales = {s.id: s for s in get_all_sales()}
        sale = all_sales.get(sale_id)
        if sale:
            SaleDialog(self, sale=sale, on_save=self._on_save)

    def _on_save(self):
        self.refresh(self.year, self.month)
        if self.refresh_cb:
            self.refresh_cb()


# ─── 経費管理画面 ─────────────────────────────────────

class ExpenseView(ctk.CTkFrame):
    def __init__(self, parent, year: int, month: int, refresh_cb=None):
        super().__init__(parent, fg_color=COLORS["bg"], corner_radius=0)
        self.year = year
        self.month = month
        self.refresh_cb = refresh_cb
        self._build()

    def refresh(self, year: int, month: int, **_):
        self.year = year
        self.month = month
        for w in self.winfo_children():
            w.destroy()
        self._build()

    def _build(self):
        rows = get_expenses_for_month(self.year, self.month)
        total_plan = sum((r["planned"] or r["base_amount"]) for r in rows)

        tb = make_frame(self, fg_color="transparent")
        tb.pack(fill="x", padx=20, pady=(16, 8))
        make_button(tb, "+ 経費を追加", command=self._add, width=130).pack(side="left")
        make_label(
            tb, f"{self.year}年{self.month}月  合計（予定）: {fmt_amount(total_plan)} 円",
            font=FONT_SMALL, text_color=COLORS["text_muted"],
        ).pack(side="right")

        card = make_frame(self, corner_radius=8)
        card.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        col_defs = [("名称", 180), ("カテゴリ", 120), ("種別", 70),
                    ("予定金額", 100), ("実績金額", 100), ("差異", 90),
                    ("メモ", 140), ("", 60)]
        hdr = make_frame(card, fg_color=COLORS["bg"], corner_radius=0)
        hdr.pack(fill="x", padx=12, pady=4)
        for text, w in col_defs:
            _fixed_label(hdr, text, w, font=FONT_SMALL,
                         text_color=COLORS["text_muted"]).pack(side="left")
        make_separator(card).pack(fill="x", padx=12)

        scroll = ctk.CTkScrollableFrame(card, fg_color="white", corner_radius=0)
        scroll.pack(fill="both", expand=True)

        if not rows:
            make_label(scroll, "データがありません。「+ 経費を追加」から登録してください。",
                       font=FONT_NORMAL, text_color=COLORS["text_muted"]).pack(pady=40)
            return

        for r in rows:
            plan = r["planned"] if r["planned"] is not None else r["base_amount"]
            act  = r["actual"]
            diff = (plan - act) if act is not None else None  # 節約をプラスで表現

            row_fr = make_frame(scroll, fg_color="transparent", corner_radius=0)
            row_fr.pack(fill="x")

            badge_text = "固定" if r["expense_type"] == "fixed" else "変動"
            badge_tc   = "#854F0B" if r["expense_type"] == "fixed" else "#993C1D"

            _fixed_label(row_fr, r["name"][:18], 180).pack(side="left", padx=(12, 0))
            _fixed_label(row_fr, r["category_name"] or "—", 120,
                         font=FONT_SMALL, text_color=COLORS["text_muted"]).pack(side="left")
            _fixed_label(row_fr, badge_text, 70,
                         font=FONT_SMALL, text_color=badge_tc).pack(side="left")
            _fixed_label(row_fr, fmt_amount(plan), 100,
                         text_color=COLORS["text_muted"], anchor="e").pack(side="left")
            _fixed_label(row_fr, fmt_amount(act) if act is not None else "—",
                         100, anchor="e").pack(side="left")
            if diff is not None:
                _fixed_label(row_fr, fmt_diff(diff), 90, font=FONT_SMALL,
                             text_color=diff_color(diff, True), anchor="e").pack(side="left")
            else:
                _fixed_label(row_fr, "未入力", 90, font=FONT_SMALL,
                             text_color=COLORS["text_muted"]).pack(side="left")
            _fixed_label(row_fr, r["monthly_notes"] or r["notes"] or "—", 140,
                         font=FONT_SMALL, text_color=COLORS["text_muted"]).pack(side="left")

            exp_id = r["id"]
            make_button(row_fr, "編集", command=lambda eid=exp_id: self._edit(eid),
                        width=55, fg_color=COLORS["bg"], hover_color=COLORS["border"],
                        text_color=COLORS["text"]).pack(side="left", padx=4)
            make_separator(scroll).pack(fill="x", padx=12)

    def _add(self):
        ExpenseDialog(self, on_save=self._on_save)

    def _edit(self, expense_id: int):
        all_exp = {e.id: e for e in get_all_expenses()}
        expense = all_exp.get(expense_id)
        if expense:
            ExpenseDialog(self, expense=expense, on_save=self._on_save)

    def _on_save(self):
        self.refresh(self.year, self.month)
        if self.refresh_cb:
            self.refresh_cb()


# ─── 口座管理画面 ─────────────────────────────────────

class AccountsView(ctk.CTkFrame):
    def __init__(self, parent, year: int, month: int, refresh_cb=None):
        super().__init__(parent, fg_color=COLORS["bg"], corner_radius=0)
        self.year = year
        self.month = month
        self.refresh_cb = refresh_cb
        self._build()

    def refresh(self, year: int, month: int, **_):
        self.year = year
        self.month = month
        for w in self.winfo_children():
            w.destroy()
        self._build()

    def _build(self):
        accounts = get_all_accounts()
        balances = {a["id"]: a["balance"] for a in get_all_balances_for_month(self.year, self.month)}

        tb = make_frame(self, fg_color="transparent")
        tb.pack(fill="x", padx=20, pady=(16, 8))
        make_button(tb, "+ 口座を追加", command=self._add_account, width=130).pack(side="left")

        scroll = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        if not accounts:
            make_label(scroll, "口座が登録されていません。「+ 口座を追加」から登録してください。",
                       font=FONT_NORMAL, text_color=COLORS["text_muted"]).pack(pady=40)
            return

        for acct in accounts:
            bal = balances.get(acct.id, 0.0)
            card = make_frame(scroll, corner_radius=8)
            card.pack(fill="x", pady=(0, 10))

            info_row = make_frame(card, fg_color="transparent")
            info_row.pack(fill="x", padx=14, pady=(12, 4))
            make_label(info_row, f"{acct.bank_name}  {acct.name}", font=FONT_BOLD).pack(side="left")

            bal_color = COLORS["danger"] if bal < 0 else COLORS["text"]
            make_label(card, f"{fmt_amount(bal)} 円",
                       font=("Yu Gothic UI", 20, "bold"),
                       text_color=bal_color).pack(anchor="w", padx=14)

            edit_row = make_frame(card, fg_color="transparent")
            edit_row.pack(fill="x", padx=14, pady=(4, 12))
            make_label(edit_row, f"{self.year}年{self.month}月 残高を更新:",
                       font=FONT_SMALL, text_color=COLORS["text_muted"]).pack(side="left")
            entry = make_entry(edit_row, width=140, placeholder=str(int(bal)))
            entry.pack(side="left", padx=8)

            def _save(e=entry, aid=acct.id):
                val_str = e.get().replace(",", "")
                try:
                    val = float(val_str)
                    set_balance(aid, self.year, self.month, val)
                    self.refresh(self.year, self.month)
                    if self.refresh_cb:
                        self.refresh_cb()
                except ValueError:
                    messagebox.showerror("入力エラー", "正しい金額を入力してください")

            make_button(edit_row, "保存", command=_save, width=70).pack(side="left")
            make_button(
                edit_row, "削除",
                command=lambda aid=acct.id: self._delete_account(aid),
                width=55, fg_color=COLORS["danger"], hover_color="#B04020",
            ).pack(side="right")

    def _add_account(self):
        dlg = ctk.CTkToplevel(self)
        dlg.title("口座を追加")
        dlg.geometry("360x260")
        dlg.grab_set()

        make_label(dlg, "口座名 *", font=FONT_BOLD).pack(anchor="w", padx=20, pady=(16, 4))
        e_name = make_entry(dlg, width=300, placeholder="例: 普通預金A")
        e_name.pack(padx=20)

        make_label(dlg, "銀行名", font=FONT_BOLD).pack(anchor="w", padx=20, pady=(12, 4))
        e_bank = make_entry(dlg, width=300, placeholder="例: ○○銀行")
        e_bank.pack(padx=20)

        def _save():
            name = e_name.get().strip()
            if not name:
                messagebox.showerror("入力エラー", "口座名を入力してください", parent=dlg)
                return
            acct = Account(id=None, name=name, bank_name=e_bank.get().strip())
            upsert_account(acct)
            dlg.destroy()
            self.refresh(self.year, self.month)

        make_button(dlg, "保存", command=_save, width=120).pack(pady=20)

    def _delete_account(self, account_id: int):
        if messagebox.askyesno("確認", "この口座を削除しますか？"):
            delete_account(account_id)
            self.refresh(self.year, self.month)


# ─── 予実管理画面 ─────────────────────────────────────

class YojitsuView(ctk.CTkFrame):
    def __init__(self, parent, fiscal_year: int, refresh_cb=None):
        super().__init__(parent, fg_color=COLORS["bg"], corner_radius=0)
        self.fiscal_year = fiscal_year
        self.refresh_cb = refresh_cb
        self._build()

    def refresh(self, fiscal_year: int, **_):
        self.fiscal_year = fiscal_year
        for w in self.winfo_children():
            w.destroy()
        self._build()

    def _build(self):
        summaries = compute_annual_summaries(self.fiscal_year)
        fiscal_months = get_fiscal_months(self.fiscal_year)

        tb = make_frame(self, fg_color="transparent")
        tb.pack(fill="x", padx=20, pady=(16, 8))
        make_label(tb, f"{self.fiscal_year}年度  年間予実比較", font=FONT_BOLD).pack(side="left")
        make_button(tb, "↓ CSV",   command=self._export_csv,   width=90).pack(side="right", padx=(8, 0))
        make_button(tb, "↓ Excel", command=self._export_excel, width=100).pack(side="right")

        card = make_frame(self, corner_radius=8)
        card.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        COL_W = 100
        cols = ["月", "売上（予）", "売上（実）", "売上差異",
                "経費（予）", "経費（実）", "経費差異",
                "収支（予）", "収支（実）", "収支差異"]
        hdr = make_frame(card, fg_color=COLORS["bg"], corner_radius=0)
        hdr.pack(fill="x", padx=12, pady=4)
        for text in cols:
            _fixed_label(hdr, text, COL_W, font=FONT_SMALL,
                         text_color=COLORS["text_muted"]).pack(side="left")
        make_separator(card).pack(fill="x", padx=12)

        scroll = ctk.CTkScrollableFrame(card, fg_color="white", corner_radius=0)
        scroll.pack(fill="both", expand=True)

        now = datetime.now()
        for s, (y, m) in zip(summaries, fiscal_months):
            is_future = (y > now.year) or (y == now.year and m > now.month)
            row_fr = make_frame(scroll, fg_color="transparent", corner_radius=0)
            row_fr.pack(fill="x")

            vals = [
                f"{m}月",
                fmt_amount(s.sale_planned),
                fmt_amount(s.sale_actual) if s.has_actual else "—",
                fmt_diff(s.sale_diff)     if s.has_actual else "—",
                fmt_amount(s.expense_planned),
                fmt_amount(s.expense_actual) if s.has_actual else "—",
                fmt_diff(s.expense_diff)     if s.has_actual else "—",
                fmt_amount(s.profit_planned),
                fmt_amount(s.profit_actual)  if s.has_actual else "—",
                fmt_diff(s.profit_actual - s.profit_planned) if s.has_actual else "—",
            ]
            diff_col_indices = {3, 6, 9}

            for ci, val in enumerate(vals):
                is_diff = (ci + 1) in diff_col_indices
                if is_diff and s.has_actual and val not in ("—", "±0"):
                    try:
                        num = float(val.replace(",", "").replace("+", ""))
                        tc = diff_color(num, True)
                    except ValueError:
                        tc = COLORS["text_muted"]
                elif is_future or ci == 0:
                    tc = COLORS["text_muted"]
                else:
                    tc = COLORS["text"]
                _fixed_label(row_fr, val, COL_W, font=FONT_SMALL, text_color=tc).pack(side="left")

            make_separator(scroll).pack(fill="x", padx=12)

    def _export_csv(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile=f"cashflow_{self.fiscal_year}.csv",
        )
        if path:
            export_annual_csv(self.fiscal_year, path)
            messagebox.showinfo("完了", f"CSVを保存しました:\n{path}")

    def _export_excel(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=f"cashflow_{self.fiscal_year}.xlsx",
        )
        if path:
            try:
                export_annual_excel(self.fiscal_year, path)
                messagebox.showinfo("完了", f"Excelを保存しました:\n{path}")
            except RuntimeError as e:
                messagebox.showerror("エラー", str(e))


# ─── 設定画面 ─────────────────────────────────────────

class SettingsView(ctk.CTkFrame):
    def __init__(self, parent, refresh_cb=None):
        super().__init__(parent, fg_color=COLORS["bg"], corner_radius=0)
        self.refresh_cb = refresh_cb
        self._build()

    def refresh(self, **_):
        for w in self.winfo_children():
            w.destroy()
        self._build()

    def _build(self):
        scroll = ctk.CTkScrollableFrame(self, fg_color=COLORS["bg"], corner_radius=0)
        scroll.pack(fill="both", expand=True, padx=20, pady=16)

        # 年度設定
        card = make_frame(scroll, corner_radius=8)
        card.pack(fill="x", pady=(0, 12))
        make_label(card, "年度設定", font=FONT_BOLD).pack(anchor="w", padx=14, pady=(12, 4))
        make_separator(card).pack(fill="x", padx=14)
        row = make_frame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=10)
        make_label(row, "会計年度の開始月:", font=FONT_NORMAL).pack(side="left")
        current = get_fiscal_start_month()
        months = [f"{m}月" for m in range(1, 13)]
        cb = make_combobox(row, months, width=120)
        cb.set(f"{current}月")
        cb.pack(side="left", padx=12)

        def _save_fiscal():
            m = int(cb.get().replace("月", ""))
            set_fiscal_start_month(m)
            messagebox.showinfo("保存", "年度設定を保存しました")
            if self.refresh_cb:
                self.refresh_cb()

        make_button(row, "保存", command=_save_fiscal, width=80).pack(side="left")

        # カテゴリ管理
        card2 = make_frame(scroll, corner_radius=8)
        card2.pack(fill="x", pady=(0, 12))
        make_label(card2, "カテゴリ管理", font=FONT_BOLD).pack(anchor="w", padx=14, pady=(12, 4))
        make_separator(card2).pack(fill="x", padx=14)
        self._build_category_section(card2)

        # バックアップ
        card3 = make_frame(scroll, corner_radius=8)
        card3.pack(fill="x", pady=(0, 12))
        make_label(card3, "データバックアップ", font=FONT_BOLD).pack(anchor="w", padx=14, pady=(12, 4))
        make_separator(card3).pack(fill="x", padx=14)
        btn_row = make_frame(card3, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=12)
        make_button(btn_row, "バックアップを保存", command=self._backup, width=160).pack(side="left", padx=(0, 8))
        make_button(
            btn_row, "バックアップから復元", command=self._restore,
            width=170, fg_color=COLORS["danger"], hover_color="#B04020",
        ).pack(side="left")

    def _build_category_section(self, parent):
        cats = get_categories()
        cat_frame = make_frame(parent, fg_color="transparent")
        cat_frame.pack(fill="x", padx=14, pady=8)

        for cat in cats:
            row = make_frame(cat_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            tc = "#185FA5" if cat.type == "sale" else "#854F0B"
            make_label(row, cat.name, font=FONT_SMALL, text_color=tc).pack(side="left")
            make_label(row, f"（{'売上' if cat.type == 'sale' else '経費'}）",
                       font=FONT_SMALL, text_color=COLORS["text_muted"]).pack(side="left", padx=6)
            make_button(
                row, "削除",
                command=lambda cid=cat.id: self._delete_cat(cid),
                width=55, fg_color=COLORS["danger"], hover_color="#B04020",
            ).pack(side="right")

        add_row = make_frame(parent, fg_color=COLORS["bg"], corner_radius=6)
        add_row.pack(fill="x", padx=14, pady=(4, 12))
        e_cat_name = make_entry(add_row, width=180, placeholder="カテゴリ名")
        e_cat_name.pack(side="left", padx=(10, 6), pady=8)
        cb_type = make_combobox(add_row, ["売上", "経費"], width=90)
        cb_type.set("売上")
        cb_type.pack(side="left", padx=(0, 6))

        def _add_cat():
            name = e_cat_name.get().strip()
            if not name:
                return
            t = "sale" if cb_type.get() == "売上" else "expense"
            upsert_category(Category(id=None, name=name, type=t))
            self.refresh()

        make_button(add_row, "+ 追加", command=_add_cat, width=80).pack(side="left")

    def _delete_cat(self, cat_id: int):
        if messagebox.askyesno("確認", "このカテゴリを削除しますか？"):
            delete_category(cat_id)
            self.refresh()

    def _backup(self):
        dest = filedialog.askdirectory(title="バックアップ保存先を選択")
        if dest:
            path = backup_database(dest)
            messagebox.showinfo("完了", f"バックアップを保存しました:\n{path}")

    def _restore(self):
        path = filedialog.askopenfilename(
            title="バックアップファイルを選択",
            filetypes=[("SQLite DB", "*.db")],
        )
        if path:
            if messagebox.askyesno("警告", "現在のデータが上書きされます。復元しますか？"):
                restore_database(path)
                messagebox.showinfo("完了", "データを復元しました。アプリを再起動してください。")
