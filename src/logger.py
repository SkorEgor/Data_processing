import os
import logging

from src.setting import PROJECT_DIR, PATH_LOG_FILE, LOG_LEVEL

# Создание директории если она не существует
os.makedirs(PROJECT_DIR, exist_ok=True)
# Задание конфигурации Logger
logging.basicConfig(
    filename=PATH_LOG_FILE,
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(levelname)s %(module)s ---> %(funcName)s() %(message)s",
    datefmt="%Y.%m.%d %H:%M:%S",
    encoding='utf-8'
)
# Объект логирования
log = logging.getLogger()
