"""
Константы стилей CustomTkinter — цвета кнопок, шрифты, отступы.
Импортируйте отсюда вместо хардкода в каждом виджете.
"""

import customtkinter as ctk

# Основные цвета кнопок
BTN_PRIMARY = "#2b579a"
BTN_PRIMARY_HOVER = "#3a6abf"
BTN_DANGER = "#a00"
BTN_DANGER_HOVER = "#c00"
BTN_SUCCESS = "#217346"
BTN_SUCCESS_HOVER = "#1a5c38"
BTN_NEUTRAL = "gray35"
BTN_NEUTRAL_HOVER = "gray50"
BTN_WARNING = "#e67700"
BTN_WARNING_HOVER = "#b35900"

# Цвета фона
BG_HEADER = "#1a3a6b"
BG_INFO_BAR = "#243e6b"
BG_INPUT = "gray17"
BG_ROW_EVEN = "gray20"
BG_ROW_ODD = "gray18"

# Стандартные шрифты
def font_bold(size: int = 13) -> ctk.CTkFont:
    return ctk.CTkFont(size=size, weight="bold")

def font_normal(size: int = 11) -> ctk.CTkFont:
    return ctk.CTkFont(size=size)

def font_header() -> ctk.CTkFont:
    return ctk.CTkFont(family="Segoe UI", size=18, weight="bold")
