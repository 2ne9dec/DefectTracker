import sqlite3
import os

from app.config import DB_PATH
from app.logger import get_logger

logger = get_logger(__name__)

# ─────────────────────────── ВЕРИФИКАЦИЯ ────────────────────────────────────

def verify_database(conn: sqlite3.Connection) -> None:
    """Быстрая проверка целостности после инициализации."""
    cursor = conn.cursor()
    errors = []

    cursor.execute("""
        SELECT COUNT(*) FROM Line l
        LEFT JOIN Voltage v ON l.voltage_id = v.id
        WHERE v.id IS NULL
    """)
    if cursor.fetchone()[0] > 0:
        errors.append("❌ Найдены линии без напряжения")

    cursor.execute("""
        SELECT COUNT(*) FROM DefectType dt
        LEFT JOIN Element e ON dt.element_id = e.id
        WHERE e.id IS NULL
    """)
    if cursor.fetchone()[0] > 0:
        errors.append("❌ Найдены дефекты без элемента")

    cursor.execute("""
        SELECT COUNT(*) FROM InspectionSheet ish
        WHERE NOT EXISTS (SELECT 1 FROM Filial f WHERE f.id = ish.filial_id)
          OR NOT EXISTS (SELECT 1 FROM Voltage v WHERE v.id = ish.voltage_id)
          OR NOT EXISTS (SELECT 1 FROM Line l WHERE l.id = ish.line_id)
    """)
    if cursor.fetchone()[0] > 0:
        errors.append("❌ Найдены акты с битыми ссылками")

    cursor.execute("SELECT COUNT(*) FROM DefectRecord")
    logger.info(f"📈 DefectRecord записей: {cursor.fetchone()[0]}")

    if errors:
        for err in errors:
            logger.error(err)
        raise RuntimeError("❌ Верификация БД не пройдена")
    logger.info("✅ Верификация БД пройдена")

# ─────────────────────────── ИНИЦИАЛИЗАЦИЯ ──────────────────────────────────

def setup_database(db_path: str = DB_PATH, force_reset: bool = False) -> None:
    """
    Создаёт схему БД и заполняет справочники.

    :param db_path:     Путь к файлу БД (по умолчанию из config.py).
    :param force_reset: Если True — удалить существующую БД перед созданием.
    """
    if os.path.exists(db_path):
        if not force_reset:
            logger.warning(f"💾 База {db_path} уже существует. Используйте force_reset=True для сброса")
            return
        try:
            os.remove(db_path)
            logger.info(f"🗑️ Старая база {db_path} удалена")
        except OSError as e:
            logger.error(f"❌ Не удалось удалить {db_path}: {e}")
            raise

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.cursor()

        # ── Схема ──────────────────────────────────────────────────────────
        cursor.executescript("""
            PRAGMA foreign_keys = ON;

            CREATE TABLE Filial (
                id   INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            );

            CREATE TABLE Voltage (
                id        INTEGER PRIMARY KEY,
                name      TEXT NOT NULL,
                filial_id INTEGER,
                UNIQUE(name, filial_id),
                FOREIGN KEY(filial_id) REFERENCES Filial(id)
            );

            CREATE TABLE Line (
                id         INTEGER PRIMARY KEY,
                name       TEXT NOT NULL,
                voltage_id INTEGER,
                pole_count INTEGER DEFAULT 0,
                UNIQUE(name, voltage_id),
                FOREIGN KEY(voltage_id) REFERENCES Voltage(id)
            );

            CREATE TABLE Element (
                id   INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            );

            CREATE TABLE DefectType (
                id         INTEGER PRIMARY KEY,
                name       TEXT NOT NULL,
                element_id INTEGER NOT NULL,
                severity   TEXT CHECK(severity IN ('low', 'medium', 'critical')) NOT NULL,
                UNIQUE(name, element_id),
                FOREIGN KEY(element_id) REFERENCES Element(id)
            );

            CREATE TABLE InspectionSheet (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                filial_id    INTEGER NOT NULL,
                voltage_id   INTEGER NOT NULL,
                line_id      INTEGER NOT NULL,
                created_date TEXT NOT NULL,
                created_by   TEXT NOT NULL,
                status       TEXT DEFAULT 'active'
                            CHECK(status IN ('active', 'archived', 'draft')),
                FOREIGN KEY(filial_id)  REFERENCES Filial(id),
                FOREIGN KEY(voltage_id) REFERENCES Voltage(id),
                FOREIGN KEY(line_id)    REFERENCES Line(id)
            );

            CREATE TABLE DefectRecord (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                sheet_id       INTEGER NOT NULL,
                pole_number    INTEGER NOT NULL,
                defect_id      INTEGER NOT NULL,
                date_found     TEXT NOT NULL,
                inspector_find TEXT,
                date_fixed     TEXT,
                inspector_fix  TEXT,
                is_fixed       INTEGER DEFAULT 0 CHECK(is_fixed IN (0, 1)),
                FOREIGN KEY(sheet_id)  REFERENCES InspectionSheet(id),
                FOREIGN KEY(defect_id) REFERENCES DefectType(id)
            );

            CREATE INDEX IF NOT EXISTS idx_sheet_line      ON InspectionSheet(line_id);
            CREATE INDEX IF NOT EXISTS idx_sheet_status    ON InspectionSheet(status);
            CREATE INDEX IF NOT EXISTS idx_sheet_date      ON InspectionSheet(created_date);
            CREATE INDEX IF NOT EXISTS idx_sheet_composite ON InspectionSheet(line_id, status);
            CREATE INDEX IF NOT EXISTS idx_defect_sheet    ON DefectRecord(sheet_id);
            CREATE INDEX IF NOT EXISTS idx_defect_fixed    ON DefectRecord(is_fixed, date_fixed);
            CREATE INDEX IF NOT EXISTS idx_defect_type     ON DefectType(element_id, severity);
            CREATE INDEX IF NOT EXISTS idx_voltage_filial  ON Voltage(filial_id);
            CREATE INDEX IF NOT EXISTS idx_line_voltage    ON Line(voltage_id);
        """)
        logger.info("✅ Таблицы и индексы созданы")

        # ── Справочники ────────────────────────────────────────────────────
        filials = [
            ("Гомельские ЭС",),
            ("Жлобинские ЭС",),
            ("Мозырские ЭС",),
            ("Речицкие ЭС",),
        ]
        cursor.executemany("INSERT INTO Filial (name) VALUES (?)", filials)

        voltages = [
            ("ВЛ-35 кВ", 2),
            ("ВЛ-110 кВ", 2),
            ("ВЛ-220 кВ", 2),
            ("ВЛ-330 кВ", 2),
            ("ВЛ-750 кВ", 2),
        ]
        cursor.executemany("INSERT INTO Voltage (name, filial_id) VALUES (?, ?)", voltages)

        voltage_lookup = {
            (name, filial_id): vid
            for vid, name, filial_id in cursor.execute("SELECT id, name, filial_id FROM Voltage").fetchall()
        }
        logger.info(f"🔍 Voltage lookup: {len(voltage_lookup)} записей")

        # ── Вспомогательные функции ────────────────────────────────────────

        def count_poles(range_str) -> int:
            if range_str is None:
                return 0
            range_str = str(range_str).strip()
            if not range_str or range_str.lower() == "none":
                return 0
            total = 0
            for r in range_str.split("\n"):
                r = r.strip()
                if "-" in r:
                    parts = r.split("-")
                    if len(parts) == 2:
                        try:
                            start, end = int(parts[0].strip()), int(parts[1].strip())
                            total += max(0, end - start + 1)
                        except ValueError as e:
                            logger.warning(f"⚠️ Неверный формат диапазона '{r}': {e}")
            if total <= 0:
                logger.warning(f"⚠️ Пустой или невалидный диапазон опор: '{range_str}'")
                return 0
            return total

        def insert_lines(lines_data: list, default_filial_id: int = 2) -> None:
            for name, voltage_name, pole_count in lines_data:
                vid = voltage_lookup.get((voltage_name, default_filial_id))
                if not vid:
                    logger.error(f"❌ Не найдено напряжение: '{voltage_name}', filial_id={default_filial_id}")
                    continue
                cursor.execute(
                    "INSERT INTO Line (name, voltage_id, pole_count) VALUES (?, ?, ?)",
                    (name, vid, pole_count),
                )

        # ── Линии ──────────────────────────────────────────────────────────
        lines_330 = [
            ("№ 338 Жлобин 330 - Могилев", "ВЛ-330 кВ", count_poles("250-431")),
            ("№ 431 Жлобин Западная - Мирадино", "ВЛ-330 кВ", count_poles("108-223")),
            ("№ 551 Жлобин Западная - Сталь", "ВЛ-330 кВ", count_poles("1-23")),
            ("№ 552 Жлобин Западная - Прокат", "ВЛ-330 кВ", count_poles("1-10")),
            ("№ 553 Жлобин Западная - Металлургическая", "ВЛ-330 кВ", count_poles("1-17")),
            ("№ 554 Жлобин 330 - Металлургическая", "ВЛ-330 кВ", count_poles("1-97")),
        ]

        lines_110 = [
            ("Жлобин Западная - Прокат", "ВЛ-110 кВ", count_poles("1-12")),
            ("Жлобин Западная - Сталь", "ВЛ-110 кВ", count_poles("1-18")),
            ("Металлургическая - Корд", "ВЛ-110 кВ", count_poles("1-19")),
            ("Металлургическая - Сортовая", "ВЛ-110 кВ", count_poles("1-11")),
            ("Металлургическая - Сталь", "ВЛ-110 кВ", count_poles("1-18")),
            ("Металлургическая - Прокат", "ВЛ-110 кВ", count_poles("1-12")),
            ("Жлобин Западная - Корд", "ВЛ-110 кВ", count_poles("1-19")),
            ("Жлобин Западная - Сортовая", "ВЛ-110 кВ", count_poles("1-23")),
            ("Жлобин Западная - Лукское", "ВЛ-110 кВ", count_poles("1-61")),
            ("Жлобин Западная - Тяговая №1", "ВЛ-110 кВ", count_poles("1-20")),
            ("Жлобин Западная - Тяговая №2", "ВЛ-110 кВ", count_poles("1-18")),
            ("Жлобин Западная - Жлобин Северная №1", "ВЛ-110 кВ", count_poles("1-62")),
            ("Жлобин Западная - Жлобин Северная №2", "ВЛ-110 кВ", count_poles("1-36")),
            ("Жлобин Западная - Лебедевка", "ВЛ-110 кВ", count_poles("1-72")),
            ("Жлобин Западная - Жлобин 330", "ВЛ-110 кВ", count_poles("1-161")),
            ("отп. № 1 к ПС ФИМ от Жлобин Западная - Жлобин 330", "ВЛ-110 кВ", count_poles("1-3")),
            ("Жлобин Западная - Жлобин 110", "ВЛ-110 кВ", count_poles("1-44")),
            ("отп. № 1 к ПС ФИМ от Жлобин Западная - Жлобин 110", "ВЛ-110 кВ", count_poles("1-4")),
            ("Заводская - Жлобин 110", "ВЛ-110 кВ", count_poles("13-159")),
            ("отп. № 1 к ПС Забродье от Заводская - Жлобин 110", "ВЛ-110 кВ", count_poles("1-4")),
            ("отп. № 2 к ПС Мормаль от Заводская - Жлобин 110", "ВЛ-110 кВ", count_poles("1-26")),
            ("отп. № 3 к ПС Стрешин от Заводская - Жлобин 110", "ВЛ-110 кВ", count_poles("1-43")),
            ("Жлобин 330 - Диапроектор", "ВЛ-110 кВ", count_poles("1-141")),
            ("Жлобин 330 - Жлобин 110", "ВЛ-110 кВ", count_poles("1-116")),
            ("отп. № 1 К ПС Лебедевка от Жлобин 330 - Жлобин 110", "ВЛ-110 кВ", count_poles("1-30")),
            ("Жлобин 330 - Вирская №1", "ВЛ-110 кВ", count_poles("1-76")),
            ("Жлобин 330 - Вирская №2", "ВЛ-110 кВ", count_poles("1-77")),
            ("Жлобин 330 - Металлургическая № 1", "ВЛ-110 кВ", count_poles("1-162")),
            ("Жлобин 330 - Металлургическая № 2", "ВЛ-110 кВ", count_poles("1-162")),
            ("Жлобин 330 - Буда Кошелёво", "ВЛ-110 кВ", count_poles("1-71")),
            ("отп. № 1 к ПС Пиревичи от Жлобин 330 - Буда Кошелёво", "ВЛ-110 кВ", count_poles("1-21")),
            ("Жлобин 330 - Рогинь", "ВЛ-110 кВ", count_poles("1-13")),
            ("Жлобин 330 - Меркуловичи отп. № 1 к ПС Белицкое", "ВЛ-110 кВ", count_poles("1-128")),
            ("Жлобин 110 - Буда Кошелёво", "ВЛ-110 кВ", count_poles("1-85")),
            ("отп. № 1 к ПС Пиревичи от Жлобин 110 - Буда Кошелёво", "ВЛ-110 кВ", count_poles("1-21")),
            ("отп. № 2 к ПС Четверни от Жлобин 110 - Буда Кошелёво", "ВЛ-110 кВ", count_poles("1-2")),
            ("Диапроектор - Задрутье отп. к ПС Станьковская", "ВЛ-110 кВ", count_poles("1-51")),
            ("отп. № 1 к ПС Станьковская от Диапроектор - Задрутье", "ВЛ-110 кВ", count_poles("1-41")),
            ("Диапроектор - Старое Село", "ВЛ-110 кВ", count_poles("1-40")),
            ("Чечерск - Рогинь отп. №1 к ПС Крутое", "ВЛ-110 кВ", count_poles("1-106")),
            ("отп. № 1 к ПС Крутое от Чечерск - Рогинь", "ВЛ-110 кВ", count_poles("1-39")),
            ("Чечерск - Светиловичи", "ВЛ-110 кВ", count_poles("1-80")),
            ("отп. № 2 к ПС Крутое Чечерск - Светиловичи", "ВЛ-110 кВ", count_poles("1-40")),
            ("Корма - Меркуловичи", "ВЛ-110 кВ", count_poles("1-90")),
            ("Корма - Большой Осов отп. № 1 к ПС Волынцы", "ВЛ-110 кВ", count_poles("1-95")),
            ("Лукское - Задрутье", "ВЛ-110 кВ", count_poles("1-49")),
            ("Старое Село - Тощица", "ВЛ-110 кВ", count_poles("1-105")),
            ("Забродье - ТЭЦ 7", "ВЛ-110 кВ", count_poles("26-45")),
            ("отп. № 1 к ПС Стрешин от Забродье - ТЭЦ 7", "ВЛ-110 кВ", count_poles("1-129")),
        ]

        lines_35 = [
            ("Жлобин 110 - Бобовка", "ВЛ-35 кВ", count_poles("1-72")),
            ("Жлобин 110 - Малевичи", "ВЛ-35 кВ", count_poles("1-83")),
            ("Жлобин 110 - Солоное", "ВЛ-35 кВ", count_poles("1-35")),
            ("Красный Берег - Щедрин", "ВЛ-35 кВ", count_poles("1-73")),
            ("Красный Берег - Новый Остров", "ВЛ-35 кВ", count_poles("1-39")),
            ("Красный Берег - Малевичи", "ВЛ-35 кВ", count_poles("1-70")),
            ("Задрутье - Рогачёв", "ВЛ-35 кВ", count_poles("1-18")),
            ("Задрутье - Крушиновка", "ВЛ-35 кВ", count_poles("1-98")),
            ("отп. № 1 к ПС Рогачёв от Задрутье - Крушиновка", "ВЛ-35 кВ", count_poles("1-12")),
            ("Задрутье - Дворец", "ВЛ-35 кВ", count_poles("1-93")),
            ("отп. № 1 к ПС Новый Остров от Задрутье - Дворец", "ВЛ-35 кВ", count_poles("1-59")),
            ("Задрутье - Довск отп. К ПС Гадиловичи", "ВЛ-35 кВ", count_poles("1-175")),
            ("Корма - Староград", "ВЛ-35 кВ", count_poles("1-65")),
            ("Корма - Журавичи", "ВЛ-35 кВ", count_poles("1-141")),
            ("Корма - Коселяцкая", "ВЛ-35 кВ", count_poles("1-53")),
            ("Корма - Чечерск", "ВЛ-35 кВ", count_poles("1-152")),
            ("отп. № 1 к ПС Лужок от Корма - Чечерск", "ВЛ-35 кВ", count_poles("1-14")),
            ("Довск - Слобода", "ВЛ-35 кВ", count_poles("1-71")),
            ("Довск - Староград", "ВЛ-35 кВ", count_poles("1-60")),
            ("Белицкое - Бобовка", "ВЛ-35 кВ", count_poles("1-92")),
            ("Белицкое - Городец", "ВЛ-35 кВ", count_poles("1-42")),
            ("Щедрин - Паричи", "ВЛ-35 кВ", count_poles("1-53")),
            ("Щедрин - Плесовичи", "ВЛ-35 кВ", count_poles("1-71")),
            ("Солоное - Стрешин", "ВЛ-35 кВ", count_poles("1-86")),
            ("Станьковская - Крушиновка", "ВЛ-35 кВ", count_poles("1-82")),
            ("Слобода - Журавичи", "ВЛ-35 кВ", count_poles("1-94")),
            ("Коселяцкая - Гайшин", "ВЛ-35 кВ", count_poles("1-69")),
            ("Чечерск - Нисимковичи", "ВЛ-35 кВ", count_poles("1-79")),
            ("Волынцы - Полесье", "ВЛ-35 кВ", count_poles("1-94")),
        ]

        try:
            insert_lines(lines_330, default_filial_id=2)
            insert_lines(lines_110, default_filial_id=2)
            insert_lines(lines_35, default_filial_id=2)

            elements = [
                ("Геометрия",),
                ("Деревья",),
                ("ДКР",),
                ("Гаситель вибрации",),
                ("Грозотрос",),
                ("Дистанционная распорка",),
                ("Заземление",),
                ("Изолятор-грозотроса",),
                ("Натяжная гирлянда",),
                ("Обводная гирлянда",),
                ("Поддерживающая гирлянда",),
                ("Подвесная гирлянда",),
                ("Изолятор керамический (фарфоровый)",),
                ("Изолятор полимерный",),
                ("Информационный знак",),
                ("Опора",),
                ("Тросовая оттяжка опоры",),
                ("Посторонние предметы",),
                ("Провод",),
                ("Траверса",),
                ("Устройство отпугивания птиц",),
                ("Фундамент, Ригель",),
                ("Шлейф",),
                ("Шунт-грозотроса",),
                ("Разрядник",),
            ]
            cursor.executemany("INSERT INTO Element (name) VALUES (?)", elements)

            elem_ids = {name: id_ for id_, name in cursor.execute("SELECT id, name FROM Element").fetchall()}

            defects = []
            defect_templates = {
                "Геометрия": [
                    ("Грозотрос-Разрегулировка стрелы провеса", "medium"),
                    ("Провод-Разрегулировка стрелы провеса", "medium"),
                ],
                "Деревья": [
                    ("Расстояние до крайнего провода меньше 4-6 м", "critical"),
                    ("Угрожающее (наклонённое)", "critical"),
                    ("Угрожающее (сухостойное)", "critical"),
                ],
                "ДКР": [
                    ("Высотой более 4 м", "critical"),
                ],
                "Гаситель вибрации": [
                    ("Неправильно установлен", "medium"),
                    ("Отсутствует", "critical"),
                    ("Отсутствует Груз(ы)", "medium"),
                    ("Провисание Груза(ов)", "low"),
                    ("Смещён с места установки", "medium"),
                ],
                "Грозотрос": [
                    ("Обрыв", "critical"),
                    ("Обрыв проволок верхнего повива (расплетение)", "critical"),
                    ("Оплавление", "critical"),
                    ("Повреждение соединительного зажима", "critical"),
                    ("Разрегулировка искрового промежутка", "medium"),
                ],
                "Дистанционная распорка": [
                    ("Отсутствует", "critical"),
                    ("Раскрутился зажим", "medium"),
                    ("Сломана", "critical"),
                    ("Смещена", "medium"),
                ],
                "Заземление": [
                    ("Выпахан (на поверхности земли)", "medium"),
                    ("Отсутствие выпуска контура заземления", "critical"),
                    ("Обрыв заземляющего спуска на опоре", "critical"),
                ],
                "Изолятор-грозотроса": [
                    ("Загрязнение птичьим пометом", "low"),
                    ("Разрушен", "critical"),
                    ("Отсутствие замка", "medium"),
                    ("Следы перекрытия", "critical"),
                    ("Загрязнение от выбросов промышленными предприятиями", "medium"),
                ],
                "Натяжная гирлянда": [
                    ("Загрязнение птичьим пометом", "low"),
                    ("Отсутствие замка", "medium"),
                    ("Разрушен изолятор", "critical"),
                    ("Следы перекрытия", "critical"),
                ],
                "Обводная гирлянда": [
                    ("Загрязнение птичьим пометом", "low"),
                    ("Отсутствие замка", "medium"),
                    ("Разрушен изолятор", "critical"),
                    ("Следы перекрытия", "critical"),
                ],
                "Поддерживающая гирлянда": [
                    ("Загрязнение птичьим пометом", "low"),
                    ("Отсутствие замка", "medium"),
                    ("Разрушен изолятор", "critical"),
                    ("Следы перекрытия", "critical"),
                ],
                "Подвесная гирлянда": [
                    ("Загрязнение птичьим пометом", "low"),
                    ("Отсутствие замка", "medium"),
                    ("Разрушен изолятор", "critical"),
                    ("Следы перекрытия", "critical"),
                    ("Отклонение от вертикального положения", "medium"),
                ],
                "Изолятор керамический (фарфоровый)": [
                    ("Загрязнение птичьим пометом", "low"),
                    ("Следы перекрытия", "critical"),
                    ("Разрушен изолятор", "critical"),
                    ("Механическое повреждение - Трещины", "critical"),
                ],
                "Изолятор полимерный": [
                    ("Загрязнение птичьим пометом", "low"),
                    ("Следы перекрытия", "critical"),
                ],
                "Информационный знак": [
                    ("Информация не обновлена (невозможно прочесть)", "low"),
                    ("Отсутствует нумерации", "low"),
                    ("Отсутствует предупреждающий плакат", "medium"),
                    ("Отсутствует расцветка фаз", "low"),
                    ("Отсутствует Знак Ловить рыбу опасно для жизни", "medium"),
                    ("Отсутствует наименование ВЛ", "low"),
                ],
                "Опора": [
                    ("Коррозия металла – поверхностная", "medium"),
                    ("Коррозия металла – сквозная", "critical"),
                    ("Опора железобетонная - выкрашивание бетона, скол, раковина", "medium"),
                    ("Опора железобетонная - оголение и коррозия арматуры каркаса", "critical"),
                    ("Опора железобетонная - сквозная выбоина (дыра в опоре)", "critical"),
                    ("Опора железобетонная – трещина", "critical"),
                    ("Опора железобетонная – изгиб стойки", "critical"),
                    ("Опора металлическая - отсутствие деталей элементов", "medium"),
                    ("Ослабление болтовых соединений", "medium"),
                    ("Отклонение по вертикали (вдоль и поперек ВЛ)", "critical"),
                    ("Смещение перпендикулярно оси (опора установлена не по оси ВЛ)", "critical"),
                ],
                "Тросовая оттяжка опоры": [
                    ("Коррозия", "medium"),
                    ("Ослабление", "medium"),
                    ("Отсутствие контргайки на U-образном болте", "low"),
                    ("Отсутствие смазки", "low"),
                    ("Отсутствие хомутов (бандажей)", "medium"),
                    ("Отсутствие шплинтов в клиньях тросовых оттяжек", "medium"),
                    ("Повреждение", "medium"),
                    ("Повреждение U-образных болтов", "medium"),
                    ("Расплетение повива тросовой оттяжки", "critical"),
                    ("Обрыв проволок тросовой оттяжки", "critical"),
                ],
                "Посторонние предметы": [
                    ("Гнездо в теле металлической опоры", "medium"),
                    ("Гнездо на оголовнике железобетонной опоры", "medium"),
                    ("Гнездо на траверсе", "medium"),
                    ("Гнездо на тросостойке", "medium"),
                    ("Наброс ветки", "low"),
                    ("Наброс другое", "low"),
                    ("Наброс проволоки на траверсу с шунтированием изоляторов", "critical"),
                    ("Падение дерева без обрыва провода", "critical"),
                    ("Падение дерева с обрывом провода", "critical"),
                ],
                "Провод": [
                    ("Вспучивание верхнего повива", "critical"),
                    ("Обрыв проволок верхнего повива (расплетение)", "critical"),
                    ("Оплавление", "critical"),
                    ("Повреждение соединительного зажима", "critical"),
                    ("Обрыв: провод 1", "critical"),
                    ("Обрыв: провод 2", "critical"),
                    ("Обрыв: провод 3", "critical"),
                ],
                "Траверса": [
                    ("Деформация", "critical"),
                    ("Деформация оттяжки траверсы", "critical"),
                    ("Неправильная установка элементов для крепления КГП (скопление воды)", "medium"),
                    ("Обрыв тяга траверсы", "critical"),
                    ("Разворот траверс железобетонной опоры относительно оси ВЛ", "critical"),
                ],
                "Устройство отпугивания птиц": [
                    ("Отсутствует (100%)", "medium"),
                    ("Повреждено", "low"),
                ],
                "Фундамент, Ригель": [
                    ("Механическое повреждение", "critical"),
                    ("Подмывание грунта", "critical"),
                    ("Оголён (не засыпан грунтом)", "medium"),
                    ("Разрушен (трещины, сколы)", "critical"),
                ],
                "Шлейф": [
                    ("Вспучивание верхнего повива", "critical"),
                    ("Обрыв", "critical"),
                    ("Обрыв проволок верхнего повива (расплетение)", "critical"),
                    ("Раковины сварного соединения", "medium"),
                ],
                "Шунт-грозотроса": [
                    ("Оборван", "critical"),
                    ("Отсоединен, не закреплён", "medium"),
                    ("Отсутствует", "critical"),
                    ("Перегорел", "critical"),
                ],
                "Разрядник": [
                    ("Разрегулирован роговой разрядник", "medium"),
                    ("Поврежден роговой разрядник (отсутствует 1 рог)", "critical"),
                    ("Разрушен стеклянный индикатор срабатывания мультикамерного разрядника (РМК-35)", "critical"),
                ],
            }

            for elem_name, defect_list in defect_templates.items():
                elem_id = elem_ids.get(elem_name)
                if elem_id:
                    for dname, severity in defect_list:
                        defects.append((dname, elem_id, severity))

            if defects:
                cursor.executemany(
                    "INSERT INTO DefectType (name, element_id, severity) VALUES (?, ?, ?)",
                    defects,
                )

            conn.commit()
            logger.info("✅ База данных заполнена")

        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"❌ Ошибка при заполнении БД: {e}")
            raise

        verify_database(conn)

    logger.info(
        f"📊 Статистика: Филиалов: {len(filials)}, " f"Элементов: {len(elements)}, " f"Дефектов: {len(defects)}"
    )

# ─────────────────────────── ПРОВЕРКА СОВМЕСТИМОСТИ ─────────────────────────

def ensure_db(db_path: str = DB_PATH) -> bool:
    """
    Проверяет наличие и совместимость схемы БД при старте приложения.

    Returns:
        True  — БД готова к работе.
        False — пользователь отказался от пересоздания (приложение должно завершиться).
    """
    import tkinter.messagebox as msg

    conn_tmp = None
    try:
        conn_tmp = sqlite3.connect(db_path)
        c = conn_tmp.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='InspectionSheet'")
        has_sheet = c.fetchone() is not None

        has_old_schema = False
        if has_sheet:
            c.execute("PRAGMA table_info(DefectRecord)")
            has_old_schema = "element_id" in [col[1] for col in c.fetchall()]

        if not has_sheet or has_old_schema:
            conn_tmp.close()
            conn_tmp = None
            if msg.askyesno(
                "Обновление БД",
                "Обнаружена несовместимая версия базы данных.\n"
                "Требуется пересоздание (старые данные будут удалены).\n"
                "Продолжить?",
            ):
                try:
                    os.remove(db_path)
                except FileNotFoundError:
                    pass
                setup_database(db_path=db_path, force_reset=True)
                return True
            else:
                return False
        return True

    except Exception as e:
        logger.error(f"DB init error: {e}")
        import tkinter.messagebox as msg_err

        msg_err.showerror("Ошибка", str(e))
        return False
    finally:
        if conn_tmp:
            try:
                conn_tmp.close()
            except Exception:
                pass
