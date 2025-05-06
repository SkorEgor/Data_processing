import os
import shutil
import sqlite3
import pandas as pd
from src.row_data import RowName, RowData

# Директория хранения данных приложения
PROJECT_DIR: str = "app_data"
FILE_DATA_PATH: str = os.path.join(PROJECT_DIR, "db_data")
DATA_BASE_PATH: str = os.path.join(PROJECT_DIR, "app_data.db")

# Константы таблицы в БД
COLUMN_0_ROW_ID = "id"
COLUMN_1_ROW_NUMBER = "row"
COLUMN_2_WITH_SUB = "with_substance"
COLUMN_3_WITHOUT_SUB = "without_substance"
COLUMN_4_ABSORPTION = "absorption_lines"
COLUMN_5_LABELED = "labeled_data"

# Названия столбцов таблицы
COLUMN_NAMES = ["Удалить", "Данные с веществом", "Данные без вещества", "Линии поглощения", "Размеченные данные"]
# Соответствие индексов столбцов и полей базы данных
COLUMN_TO_FIELD = {
    1: COLUMN_2_WITH_SUB,
    2: COLUMN_3_WITHOUT_SUB,
    3: COLUMN_4_ABSORPTION,
    4: COLUMN_5_LABELED
}


def _db_data_changed(func):
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        if self._db_data_change_call_function is not None:
            self._db_data_change_call_function()
        return result

    return wrapper


class Database:
    def __init__(self, data_change_call_function: callable = None):
        """Инициализация базы данных и создание таблицы если она не создана"""
        # Создание директории проекта, если она не существует
        os.makedirs(PROJECT_DIR, exist_ok=True)
        os.makedirs(FILE_DATA_PATH, exist_ok=True)
        os.makedirs(os.path.dirname(DATA_BASE_PATH), exist_ok=True)
        # Подключение к базе данных
        try:
            self.conn = sqlite3.connect(DATA_BASE_PATH)
            self.cursor = self.conn.cursor()
            self._create_table()
            self._create_triggers()
            self._db_data_change_call_function = data_change_call_function
        except sqlite3.OperationalError as e:
            print(f"Failed to connect to database: {e}")
            raise

    def _create_table(self):
        """Создание таблицы file_name"""
        self.cursor.execute(f'''
            CREATE TABLE IF NOT EXISTS file_name (
                {COLUMN_0_ROW_ID} INTEGER PRIMARY KEY AUTOINCREMENT,
                {COLUMN_1_ROW_NUMBER} INTEGER UNIQUE,
                {COLUMN_2_WITH_SUB} TEXT,
                {COLUMN_3_WITHOUT_SUB} TEXT,
                {COLUMN_4_ABSORPTION} TEXT,
                {COLUMN_5_LABELED} TEXT
            )
        ''')
        self.conn.commit()

    def _create_triggers(self):
        """Создание триггеров для управления полем row"""
        self.cursor.execute(f'''
            CREATE TRIGGER IF NOT EXISTS auto_increment_row
            AFTER INSERT ON file_name
            WHEN NEW.{COLUMN_1_ROW_NUMBER} IS NULL
            BEGIN
                UPDATE file_name
                SET {COLUMN_1_ROW_NUMBER} = (SELECT COALESCE(MAX({COLUMN_1_ROW_NUMBER}), -1) + 1 
                FROM file_name WHERE {COLUMN_0_ROW_ID} != NEW.{COLUMN_0_ROW_ID})
                WHERE {COLUMN_0_ROW_ID} = NEW.{COLUMN_0_ROW_ID};
            END;
        ''')
        self.cursor.execute(f'''
            CREATE TRIGGER IF NOT EXISTS shift_row_after_delete
            AFTER DELETE ON file_name
            BEGIN
                UPDATE file_name
                SET {COLUMN_1_ROW_NUMBER} = {COLUMN_1_ROW_NUMBER} - 1
                WHERE {COLUMN_1_ROW_NUMBER} > OLD.{COLUMN_1_ROW_NUMBER};
            END;
        ''')
        self.conn.commit()

    def _get_row_directory(self, id: int) -> str:
        """Возвращает путь к директории для строки с заданным id"""
        return os.path.join(FILE_DATA_PATH, str(id))

    def add_row_to_end(self) -> tuple[int, int]:
        """
        Создание новой строки и возврат ее идентификатора и номера строки.
        Создает директорию для строки.
        """
        self.cursor.execute(f'INSERT INTO file_name ({COLUMN_1_ROW_NUMBER}) VALUES (NULL)')
        row_id = self.cursor.lastrowid
        self.cursor.execute(f'SELECT {COLUMN_1_ROW_NUMBER} FROM file_name WHERE {COLUMN_0_ROW_ID} = ?', (row_id,))
        row_number = self.cursor.fetchone()[0]
        # Создание директории для новой строки
        os.makedirs(self._get_row_directory(row_id), exist_ok=True)
        self.conn.commit()
        return row_id, row_number

    def delete_row(self, id: int) -> bool:
        """
        Удаление строки и соответствующей директории по id.
        Возвращает True при успехе, False если строка не найдена.
        """
        self.cursor.execute(f'SELECT {COLUMN_0_ROW_ID} FROM file_name WHERE {COLUMN_0_ROW_ID} = ?', (id,))
        if not self.cursor.fetchone():
            return False

        # Удаление директории строки
        row_dir = self._get_row_directory(id)
        if os.path.exists(row_dir):
            shutil.rmtree(row_dir)

        self.cursor.execute(f'DELETE FROM file_name WHERE {COLUMN_0_ROW_ID} = ?', (id,))
        self.conn.commit()
        return True

    def set_data(self, id: int, field: str, field_value: str, file_data: pd.DataFrame) -> bool:
        """
        Установка значения для указанного поля в строке с заданным id.
        Если значение - DataFrame, сохраняет его как CSV в директории строки с уникальным именем.
        Возвращает True при успехе, False если поле невалидно или строка не найдена.
        """
        valid_fields = [COLUMN_2_WITH_SUB, COLUMN_3_WITHOUT_SUB, COLUMN_4_ABSORPTION, COLUMN_5_LABELED]
        if field not in valid_fields:
            return False

        self.cursor.execute(f'SELECT {COLUMN_0_ROW_ID} FROM file_name WHERE {COLUMN_0_ROW_ID} = ?', (id,))
        if not self.cursor.fetchone():
            return False

        row_dir = self._get_row_directory(id)
        os.makedirs(row_dir, exist_ok=True)
        file_path = os.path.join(row_dir, field_value)
        file_data.to_csv(file_path, index=False)

        self.cursor.execute(f'UPDATE file_name SET {field} = ? WHERE {COLUMN_0_ROW_ID} = ?', (field_value, id))
        self.conn.commit()
        return True

    # ------------------------------------------------------------------------------------------------------------------
    #                                                 GET
    # ------------------------------------------------------------------------------------------------------------------
    def get_row_number_by_id(self, row_id: int) -> int | None:
        """
        Возвращает значение COLUMN_1_ROW_NUMBER для строки с заданным COLUMN_0_ROW_ID.
        Возвращает None, если строка с указанным row_id не найдена.
        """
        self.cursor.execute(f'SELECT {COLUMN_1_ROW_NUMBER} FROM file_name WHERE {COLUMN_0_ROW_ID} = ?', (row_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def _row_data_formation(self, row: tuple) -> tuple[int, int, RowName]:
        """Формирует данные строки из кортежа, возвращая row_id, row_number и RowName."""
        column_names = [COLUMN_0_ROW_ID, COLUMN_1_ROW_NUMBER, COLUMN_2_WITH_SUB, COLUMN_3_WITHOUT_SUB,
                        COLUMN_4_ABSORPTION, COLUMN_5_LABELED]
        row_dict = dict(zip(column_names, row))
        row_name = RowName(
            with_substance=row_dict[COLUMN_2_WITH_SUB],
            without_substance=row_dict[COLUMN_3_WITHOUT_SUB],
            absorption_lines=row_dict[COLUMN_4_ABSORPTION],
            labeled_data=row_dict[COLUMN_5_LABELED]
        )
        return row_dict[COLUMN_0_ROW_ID], row_dict[COLUMN_1_ROW_NUMBER], row_name

    def get_names_row(self, row_id: int) -> tuple[int, int, RowName] | None:
        """Возвращает данные в формате row_id, row_number, RowName или None, если не найдена."""
        self.cursor.execute(f'SELECT * FROM file_name WHERE {COLUMN_0_ROW_ID} = ?', (row_id,))
        row = self.cursor.fetchone()
        if not row:
            return None
        return self._row_data_formation(row)

    def get_names_all_rows(self) -> list[tuple[int, int, RowName]]:
        """
        Возвращает все строки из таблицы в виде списка кортежей row_id,row_number,RowName,отсортированных по row_number
        """
        self.cursor.execute(f'SELECT * FROM file_name ORDER BY {COLUMN_1_ROW_NUMBER}')
        rows = self.cursor.fetchall()
        return [self._row_data_formation(row) for row in rows]

    def get_data_row(self, row_id: int) -> tuple[int, int, RowData] | None:
        """
        Возвращает данные строки по row_id в формате (row_id, row_number, RowData) или None, если строка не найдена.
        Читает CSV-файлы из директории строки для заполнения полей RowData.
        """
        # Получаем данные строки из базы
        self.cursor.execute(f'SELECT * FROM file_name WHERE {COLUMN_0_ROW_ID} = ?', (row_id,))
        row = self.cursor.fetchone()
        if not row:
            return None

        # Формируем row_id, row_number и RowName
        row_id, row_number, row_name = self._row_data_formation(row)

        # Создаем объект RowData
        row_data = RowData(data_change_call_function=self._db_data_change_call_function)
        row_dir = self._get_row_directory(row_id)

        # Маппинг полей RowName к RowData
        field_mapping = {
            'with_substance': row_name.with_substance,
            'without_substance': row_name.without_substance,
            'absorption_lines': row_name.absorption_lines,
            'labeled_data': row_name.labeled_data
        }

        # Заполняем поля RowData
        for field, file_name in field_mapping.items():
            if file_name and os.path.exists(file_path := os.path.join(row_dir, file_name)):
                try:
                    setattr(row_data, field, pd.read_csv(file_path))
                except Exception as e:
                    print(f"Error reading CSV file {file_path}: {e}")

        return row_id, row_number, row_data

    def clear_all_data(self) -> None:
        """Очистка таблицы и удаление всех директорий строк."""
        # Удаление всех строк из таблицы
        self.cursor.execute('DELETE FROM file_name')

        # Удаление всех директорий
        for item in os.listdir(FILE_DATA_PATH):
            item_path = os.path.join(FILE_DATA_PATH, item)
            shutil.rmtree(item_path)

        self.conn.commit()

    def __del__(self):
        """Закрытие соединения с базой данных при уничтожении объекта."""
        self.conn.close()


