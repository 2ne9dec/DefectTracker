import datetime

def fmt_date(date_str: str) -> str:
    """
    Форматирует дату из формата БД (ГГГГ-ММ-ДД) в отображаемый вид (ДД.ММ.ГГГГ).

    "2024-03-15" → "15.03.2024"
    "" или "-"   → "-"
    """
    if not date_str or date_str == "-":
        return "-"
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")
    except (ValueError, TypeError):
        return date_str

def parse_date_input(s: str) -> str | None:
    """
    Парсит дату из пользовательского ввода в формат для записи в БД (ГГГГ-ММ-ДД).

    Поддерживает: "ДД.ММ.ГГГГ" и "ГГГГ-ММ-ДД".
    Возвращает None если ни один формат не подошёл.
    """
    s = s.strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None
