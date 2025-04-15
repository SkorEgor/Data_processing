import sys
import traceback
from functools import partial

from PySide6.QtWidgets import QApplication, QMessageBox
from gui_logic import GuiProgram
from src.plot_widget import DataPlotWidget
from src.app_exception import AppException


def handle_exception(app, exc_type, exc_value, exc_traceback):
    """Глобальный обработчик исключений."""
    print("Произошла необработанная ошибка:", file=sys.stderr)
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    parent = app.activeWindow()
    if isinstance(exc_value, AppException):
        QMessageBox.warning(parent, exc_value.title, exc_value.message)
    else:
        QMessageBox.critical(parent, "Необработанная ошибка", str(exc_value))


def main():
    # Инициализация приложения
    app = QApplication(sys.argv)
    # Установка обработчика исключений ДО запуска диалога
    sys.excepthook = partial(handle_exception, app)
    # Запуск диалога
    window = GuiProgram()
    window.show()
    # Используем только один event loop и передаем результат в sys.exit
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
