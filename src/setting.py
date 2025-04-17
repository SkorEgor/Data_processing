import os
from dotenv import load_dotenv

load_dotenv()

# Директория проекта
MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
# Режим отладки
DEBUG_ALL: bool = os.getenv("DEBUG_ALL", "False").lower() == "true"
# Уровень логирования
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG_ALL else "INFO").upper()

# Директория хранения данных приложения
PROJECT_DIR: str = "app_data"
# Имя файла и путь к файлу для сохранения состояния приложения
STATE_FILE: str = "project_state.json"
PATH_STATE_FILE: str = os.path.join(PROJECT_DIR, STATE_FILE)
# Имя файла и путь для сохранения состояния приложения
LOG_FILE: str = "log.txt"
PATH_LOG_FILE: str = os.path.join(PROJECT_DIR, LOG_FILE)
# Значения по умолчанию
DEFAULT_WINDOW_WIDTH: int = 20
DEFAULT_ANIMATION_DELAY: int = 500
# Определение приложения
ORGANIZATION: str = "Institute for Physics of Microstructures RAS"
APPLICATION: str = "Data Analysis Studio"
RESULTS_FORMATTER_VERSION: str = "1.0.0"
