import sys
import traceback
from functools import partial
from PySide6.QtWidgets import QApplication, QMessageBox

from src.gui_logic import GuiProgram


def handle_exception(app, exc_type, exc_value, exc_traceback):
    """Глобальный обработчик исключений."""
    print("Произошла необработанная ошибка:", file=sys.stderr)
    traceback.print_exception(exc_type, exc_value, exc_traceback)
    parent = app.activeWindow()
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
