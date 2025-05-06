import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from src.table import CustomTableWidget
from src.database import Database


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Table Application")
        self.setMinimumSize(800, 400)

        # Инициализация базы данных
        self.database = Database()

        # Основной виджет и компоновка
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Создание таблицы
        self.table = CustomTableWidget(db=self.database)
        layout.addWidget(self.table)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
