import os

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
