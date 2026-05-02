import customtkinter as ctk

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

SEVERITY_COLORS = {
    "critical": "#e03131",
    "medium": "#e67700",
    "low": "#2f9e44",
}

SEVERITY_LABELS = {
    "critical": "Критичный",
    "medium": "Средний",
    "low": "Низкий",
}
