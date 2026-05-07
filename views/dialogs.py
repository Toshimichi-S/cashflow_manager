"""
売上・経費の追加/編集ダイアログ
"""

from __future__ import annotations
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from datetime import datetime
from views.ui_common import (
    COLORS, FONT_NORMAL, FONT_BOLD, FONT_SMALL, FONT_HEADING,
    make_label, make_button, make_entry, make_combobox, make_frame,
)
from models.account_model import get_categories, Category
from models.sale_model import Sale, upsert_sale
from models.expense_model import Expense, upsert_expense


def _validate_amount(value: str) -> bool:
    """金額文字列の検証（カンマ除去後に数値変換できるかチェック）"""
    stripped = value.replace(",", "").replace("，", "")
    try:
        v = float(stripped)
        return v >= 0
    except ValueError:
        return False


def _parse_amount(value: str) -> float:
    return float(value.replace(",", "").replace("，", ""))


class SaleDialog(ctk.CTkToplevel):
    """売上追加/編集ダイアログ"""

    def __init__(self, parent, sale: Sale | None = None, on_save=None):
        super().__init__(parent)
        self.sale = sale
        self.on_save = on_save
        self.title("売上の編集" if sale else "売上を追加")
        self.geometry("480x560")
        self.resizable(False, False)
        self.grab_set()
        self._build_ui()
        if sale:
            self._populate(sale)

    def _build_ui(self):
        pad = {"padx": 20, "pady": 8}
        now = datetime.now()

        make_label(self, "売上名 *", font=FONT_BOLD).pack(anchor="w", **pad)
        self.e_name = make_entry(self, width=420, placeholder="例: 月額コンサルA社")
        self.e_name.pack(**pad)

        make_label(self, "種別 *", font=FONT_BOLD).pack(anchor="w", **pad)
        self.cb_type = make_combobox(self, ["継続（毎月）", "単発"], width=200)
        self.cb_type.pack(anchor="w", **pad)

        make_label(self, "カテゴリ", font=FONT_BOLD).pack(anchor="w", **pad)
        cats = get_categories("sale")
        cat_names = ["（なし）"] + [c.name for c in cats]
        self._cats = cats
        self.cb_cat = make_combobox(self, cat_names, width=300)
        self.cb_cat.pack(anchor="w", **pad)

        make_label(self, "基本金額（円）*", font=FONT_BOLD).pack(anchor="w", **pad)
        self.e_amount = make_entry(self, width=200, placeholder="0")
        self.e_amount.pack(anchor="w", **pad)

        # 開始年月
        row = make_frame(self, fg_color="transparent")
        row.pack(fill="x", **pad)
        make_label(row, "開始年月 *", font=FONT_BOLD).pack(side="left")
        years = [str(y) for y in range(2020, 2035)]
        months = [f"{m}月" for m in range(1, 13)]
        self.cb_sy = make_combobox(row, years, width=90)
        self.cb_sy.set(str(now.year))
        self.cb_sy.pack(side="left", padx=(12, 4))
        self.cb_sm = make_combobox(row, months, width=80)
        self.cb_sm.set(f"{now.month}月")
        self.cb_sm.pack(side="left")

        # 終了年月（任意）
        row2 = make_frame(self, fg_color="transparent")
        row2.pack(fill="x", **pad)
        make_label(row2, "終了年月（空白=無期限）", font=FONT_BOLD).pack(side="left")
        self.cb_ey = make_combobox(row2, [""] + years, width=90)
        self.cb_ey.set("")
        self.cb_ey.pack(side="left", padx=(12, 4))
        self.cb_em = make_combobox(row2, [""] + months, width=80)
        self.cb_em.set("")
        self.cb_em.pack(side="left")

        make_label(self, "メモ", font=FONT_BOLD).pack(anchor="w", **pad)
        self.e_notes = ctk.CTkTextbox(self, width=420, height=60, font=FONT_NORMAL)
        self.e_notes.pack(**pad)

        # ボタン行
        btn_row = make_frame(self, fg_color="transparent")
        btn_row.pack(fill="x", pady=16, padx=20)
        make_button(btn_row, "保存", command=self._save, width=120).pack(side="right", padx=(8, 0))
        make_button(
            btn_row, "キャンセル", command=self.destroy, width=100,
            fg_color=COLORS["border"], hover_color="#CCCCCC",
            text_color=COLORS["text"],
        ).pack(side="right")

    def _populate(self, sale: Sale):
        self.e_name.insert(0, sale.name)
        self.cb_type.set("継続（毎月）" if sale.sale_type == "recurring" else "単発")
        if sale.category_id:
            cats = {c.id: c.name for c in self._cats}
            self.cb_cat.set(cats.get(sale.category_id, "（なし）"))
        self.e_amount.insert(0, str(int(sale.base_amount)))
        self.cb_sy.set(str(sale.start_year))
        self.cb_sm.set(f"{sale.start_month}月")
        if sale.end_year:
            self.cb_ey.set(str(sale.end_year))
        if sale.end_month:
            self.cb_em.set(f"{sale.end_month}月")
        self.e_notes.insert("1.0", sale.notes)

    def _save(self):
        name = self.e_name.get().strip()
        if not name:
            messagebox.showerror("入力エラー", "売上名を入力してください", parent=self)
            return
        amount_str = self.e_amount.get().strip()
        if not _validate_amount(amount_str):
            messagebox.showerror("入力エラー", "金額に正しい数値を入力してください", parent=self)
            return
        amount = _parse_amount(amount_str)

        sale_type = "recurring" if "継続" in self.cb_type.get() else "onetime"
        cat_name = self.cb_cat.get()
        category_id = None
        for c in self._cats:
            if c.name == cat_name:
                category_id = c.id
                break

        start_year = int(self.cb_sy.get())
        start_month = int(self.cb_sm.get().replace("月", ""))
        end_year = int(self.cb_ey.get()) if self.cb_ey.get() else None
        end_month_str = self.cb_em.get().replace("月", "")
        end_month = int(end_month_str) if end_month_str else None
        notes = self.e_notes.get("1.0", "end").strip()

        sale = Sale(
            id=self.sale.id if self.sale else None,
            name=name,
            category_id=category_id,
            sale_type=sale_type,
            base_amount=amount,
            start_year=start_year,
            start_month=start_month,
            end_year=end_year,
            end_month=end_month,
            notes=notes,
        )
        upsert_sale(sale)
        if self.on_save:
            self.on_save()
        self.destroy()


class ExpenseDialog(ctk.CTkToplevel):
    """経費追加/編集ダイアログ"""

    def __init__(self, parent, expense: Expense | None = None, on_save=None):
        super().__init__(parent)
        self.expense = expense
        self.on_save = on_save
        self.title("経費の編集" if expense else "経費を追加")
        self.geometry("480x560")
        self.resizable(False, False)
        self.grab_set()
        self._build_ui()
        if expense:
            self._populate(expense)

    def _build_ui(self):
        pad = {"padx": 20, "pady": 8}
        now = datetime.now()

        make_label(self, "経費名 *", font=FONT_BOLD).pack(anchor="w", **pad)
        self.e_name = make_entry(self, width=420, placeholder="例: 事務所家賃")
        self.e_name.pack(**pad)

        make_label(self, "種別 *", font=FONT_BOLD).pack(anchor="w", **pad)
        self.cb_type = make_combobox(self, ["固定", "変動"], width=200)
        self.cb_type.pack(anchor="w", **pad)

        make_label(self, "カテゴリ", font=FONT_BOLD).pack(anchor="w", **pad)
        cats = get_categories("expense")
        cat_names = ["（なし）"] + [c.name for c in cats]
        self._cats = cats
        self.cb_cat = make_combobox(self, cat_names, width=300)
        self.cb_cat.pack(anchor="w", **pad)

        make_label(self, "基本金額（円）*", font=FONT_BOLD).pack(anchor="w", **pad)
        self.e_amount = make_entry(self, width=200, placeholder="0")
        self.e_amount.pack(anchor="w", **pad)

        row = make_frame(self, fg_color="transparent")
        row.pack(fill="x", **pad)
        make_label(row, "開始年月 *", font=FONT_BOLD).pack(side="left")
        years = [str(y) for y in range(2020, 2035)]
        months = [f"{m}月" for m in range(1, 13)]
        self.cb_sy = make_combobox(row, years, width=90)
        self.cb_sy.set(str(now.year))
        self.cb_sy.pack(side="left", padx=(12, 4))
        self.cb_sm = make_combobox(row, months, width=80)
        self.cb_sm.set(f"{now.month}月")
        self.cb_sm.pack(side="left")

        row2 = make_frame(self, fg_color="transparent")
        row2.pack(fill="x", **pad)
        make_label(row2, "終了年月（空白=無期限）", font=FONT_BOLD).pack(side="left")
        self.cb_ey = make_combobox(row2, [""] + years, width=90)
        self.cb_ey.set("")
        self.cb_ey.pack(side="left", padx=(12, 4))
        self.cb_em = make_combobox(row2, [""] + months, width=80)
        self.cb_em.set("")
        self.cb_em.pack(side="left")

        make_label(self, "メモ", font=FONT_BOLD).pack(anchor="w", **pad)
        self.e_notes = ctk.CTkTextbox(self, width=420, height=60, font=FONT_NORMAL)
        self.e_notes.pack(**pad)

        btn_row = make_frame(self, fg_color="transparent")
        btn_row.pack(fill="x", pady=16, padx=20)
        make_button(btn_row, "保存", command=self._save, width=120).pack(side="right", padx=(8, 0))
        make_button(
            btn_row, "キャンセル", command=self.destroy, width=100,
            fg_color=COLORS["border"], hover_color="#CCCCCC",
            text_color=COLORS["text"],
        ).pack(side="right")

    def _populate(self, expense: Expense):
        self.e_name.insert(0, expense.name)
        self.cb_type.set("固定" if expense.expense_type == "fixed" else "変動")
        if expense.category_id:
            cats = {c.id: c.name for c in self._cats}
            self.cb_cat.set(cats.get(expense.category_id, "（なし）"))
        self.e_amount.insert(0, str(int(expense.base_amount)))
        self.cb_sy.set(str(expense.start_year))
        self.cb_sm.set(f"{expense.start_month}月")
        if expense.end_year:
            self.cb_ey.set(str(expense.end_year))
        if expense.end_month:
            self.cb_em.set(f"{expense.end_month}月")
        self.e_notes.insert("1.0", expense.notes)

    def _save(self):
        name = self.e_name.get().strip()
        if not name:
            messagebox.showerror("入力エラー", "経費名を入力してください", parent=self)
            return
        amount_str = self.e_amount.get().strip()
        if not _validate_amount(amount_str):
            messagebox.showerror("入力エラー", "金額に正しい数値を入力してください", parent=self)
            return
        amount = _parse_amount(amount_str)

        expense_type = "fixed" if self.cb_type.get() == "固定" else "variable"
        cat_name = self.cb_cat.get()
        category_id = None
        for c in self._cats:
            if c.name == cat_name:
                category_id = c.id
                break

        start_year = int(self.cb_sy.get())
        start_month = int(self.cb_sm.get().replace("月", ""))
        end_year = int(self.cb_ey.get()) if self.cb_ey.get() else None
        end_month_str = self.cb_em.get().replace("月", "")
        end_month = int(end_month_str) if end_month_str else None
        notes = self.e_notes.get("1.0", "end").strip()

        expense = Expense(
            id=self.expense.id if self.expense else None,
            name=name,
            category_id=category_id,
            expense_type=expense_type,
            base_amount=amount,
            start_year=start_year,
            start_month=start_month,
            end_year=end_year,
            end_month=end_month,
            notes=notes,
        )
        upsert_expense(expense)
        if self.on_save:
            self.on_save()
        self.destroy()
