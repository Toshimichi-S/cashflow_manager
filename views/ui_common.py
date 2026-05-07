"""
共通UIウィジェット・カラー・フォント定義
CustomTkinter のスタイルを一元管理する
"""

from __future__ import annotations
import customtkinter as ctk

# ─── カラーパレット ────────────────────────────────────
COLORS = {
    "primary":    "#185FA5",
    "primary_lt": "#E6F1FB",
    "success":    "#1D9E75",
    "success_lt": "#EAF3DE",
    "danger":     "#D85A30",
    "danger_lt":  "#FAECE7",
    "warning":    "#BA7517",
    "warning_lt": "#FAEEDA",
    "text":       "#1A1A1A",
    "text_muted": "#666666",
    "border":     "#DDDDDD",
    "bg":         "#F4F4F4",
    "card":       "#FFFFFF",
    "sidebar":    "#F0F0F0",
}

FONT_NORMAL  = ("Yu Gothic UI", 13)
FONT_BOLD    = ("Yu Gothic UI", 13, "bold")
FONT_SMALL   = ("Yu Gothic UI", 11)
FONT_HEADING = ("Yu Gothic UI", 16, "bold")
FONT_KPI     = ("Yu Gothic UI", 22, "bold")


def configure_appearance() -> None:
    """アプリ全体の外観を設定する"""
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")


# ─── 共通ウィジェット ─────────────────────────────────

def make_label(parent, text: str, font=None, text_color=None, **kwargs) -> ctk.CTkLabel:
    return ctk.CTkLabel(
        parent, text=text,
        font=font or FONT_NORMAL,
        text_color=text_color or COLORS["text"],
        **kwargs,
    )


def make_button(
    parent, text: str, command=None,
    fg_color=None, hover_color=None, width=120, **kwargs
) -> ctk.CTkButton:
    return ctk.CTkButton(
        parent, text=text, command=command, width=width,
        fg_color=fg_color or COLORS["primary"],
        hover_color=hover_color or "#0F4A80",
        font=FONT_NORMAL,
        **kwargs,
    )


def make_entry(parent, width=200, placeholder="", **kwargs) -> ctk.CTkEntry:
    return ctk.CTkEntry(
        parent, width=width,
        placeholder_text=placeholder,
        font=FONT_NORMAL,
        **kwargs,
    )


def make_combobox(parent, values: list[str], width=200, **kwargs) -> ctk.CTkComboBox:
    return ctk.CTkComboBox(
        parent, values=values, width=width,
        font=FONT_NORMAL,
        **kwargs,
    )


def make_frame(parent, fg_color=None, corner_radius=8, **kwargs) -> ctk.CTkFrame:
    return ctk.CTkFrame(
        parent,
        fg_color=fg_color or COLORS["card"],
        corner_radius=corner_radius,
        **kwargs,
    )


def make_separator(parent) -> ctk.CTkFrame:
    return ctk.CTkFrame(parent, height=1, fg_color=COLORS["border"], corner_radius=0)


def fmt_amount(val: float) -> str:
    """金額を日本式にフォーマットする（例: 1,234,567）"""
    return f"{int(val):,}"


def fmt_diff(val: float) -> str:
    """差異を符号付きでフォーマットする"""
    if val > 0:
        return f"+{int(val):,}"
    elif val < 0:
        return f"{int(val):,}"
    return "±0"


def diff_color(val: float, positive_good: bool = True) -> str:
    """差異に応じた文字色を返す"""
    if val == 0:
        return COLORS["text_muted"]
    if positive_good:
        return COLORS["success"] if val > 0 else COLORS["danger"]
    else:
        return COLORS["danger"] if val > 0 else COLORS["success"]
