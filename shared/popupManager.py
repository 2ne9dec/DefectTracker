"""
Глобальный менеджер попапов.
Гарантирует, что одновременно открыт только один выпадающий список
(ScrollableDropdown или DefectTree).
"""

_active = None

def register(popup):
    """
    Зарегистрировать новый попап как активный.
    Если был открыт другой — закрыть его.
    """
    global _active
    if _active is not None and _active is not popup:
        try:
            _active._close()
        except Exception:
            pass
    _active = popup

def unregister(popup):
    """Вызывается при закрытии попапа."""
    global _active
    if _active is popup:
        _active = None
