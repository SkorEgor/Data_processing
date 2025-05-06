import os
import pandas as pd
from typing import Callable
from PySide6.QtCore import QSize
from PySide6.QtGui import QPixmap, Qt, QPainter, QPen, QIcon
from PySide6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QAbstractItemView, QPushButton, QFrame, QHeaderView, QFileDialog
)

from src.constant import COLUMN_TO_FIELD
from src.database import Database
from src.row_data import RowName


# ----------------------------------------------------------------------------------------------------------------------
#                                                 КНОПКИ ТАБЛИЦЫ
# ----------------------------------------------------------------------------------------------------------------------
class RedCrossButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Создаем пиксельную карту для иконки (24x24)
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.transparent)

        # Рисуем красный крестик
        painter = QPainter(pixmap)
        pen = QPen(Qt.red, 2)
        painter.setPen(pen)
        painter.drawLine(6, 6, 18, 18)
        painter.drawLine(6, 18, 18, 6)
        painter.end()

        # Устанавливаем иконку
        self.setIcon(QIcon(pixmap))
        self.setIconSize(QSize(24, 24))

        # Настраиваем кнопку
        self.setFixedSize(32, 32)
        self.setStyleSheet("QPushButton { border: none; }")


def _parser_all_data(string_list):
    frequency_list = list()
    gamma_list = list()
    skipping_first_line = True

    for line in string_list:
        if skipping_first_line:
            skipping_first_line = False
            continue
        if line[0] == "*":
            break
        row = line.split()
        frequency_list.append(float(row[1]))
        gamma_list.append(float(row[4]))

    return frequency_list, gamma_list


class LoadDataButton(QPushButton):
    def __init__(
            self,
            db: Database,
            db_field_name: str,
            row_id: int,
            file_name: str | None = None,
            updated_data_in_row: Callable[[int], None] = None,
            parent=None
    ):
        super().__init__("Load Data", parent)
        self.db = db
        self.row_id = row_id
        self.field = db_field_name
        self.file_name = file_name
        self.setStyleSheet("QPushButton { text-align: center; }")
        self.clicked.connect(self.load_and_parse_file)
        if self.file_name:
            self.setText(self.file_name)
        self.updated_data_in_row = updated_data_in_row

    def load_and_parse_file(self):
        # Открываем диалог выбора файла
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File", "", "All Files (*)")
        if not file_path:
            return
        try:
            # Читаем файл
            with open(file_path, 'r') as file:
                lines = file.readlines()
            # Парсим данные
            frequency, gamma = _parser_all_data(lines)
            # Создаем DataFrame
            df = pd.DataFrame({
                'frequency': frequency,
                'gamma': gamma
            })
            # Извлекаем имя файла
            file_name = os.path.basename(file_path)
            # Сохраняем данные
            self.db.set_data(id=self.row_id, field=self.field, field_value=file_name, file_data=df)
            # Сохраняем имя файла и обновляем текст кнопки
            self.file_name = file_name
            self.setText(file_name)
            # Вызываем сообщение, что данные обновились
            self.updated_data_in_row(self.row_id)
        except Exception as e:
            print(f"Error loading file: {e}")


# ----------------------------------------------------------------------------------------------------------------------
#                                                 ТАБЛИЦА
# ----------------------------------------------------------------------------------------------------------------------
COLUMN_NAMES = ["Удалить", "Данные с веществом", "Данные без вещества", "Линии поглощения", "Размеченные данные"]


class CustomTableWidget(QTableWidget):
    def __init__(
            self,
            db: Database,
            callback_change_active_row=None,
            parent=None
    ):
        super().__init__(parent)
        self.db = db
        self.callback_change_active_row = callback_change_active_row
        # Добавить кэширование при работе с одной строкой
        # Настройка таблицы и создание первой строки
        self.setup_table()
        self._load_table_data()
        # Подключаем сигнал изменения выделения
        self.itemSelectionChanged.connect(self.handle_selection_changed)

    def setup_table(self) -> None:
        # Настройка стиля и поведения
        # - Устанавливаем стиль тени рамки таблицы на "Raised" (приподнятая тень, создает эффект 3D)
        self.setFrameShadow(QFrame.Raised)
        # - Отключает возможность редактирования ячеек таблицы пользователем
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # - Полностью отключает функциональность перетаскивания и сброса (drag-and-drop) в таблице
        self.setDragDropMode(QAbstractItemView.NoDragDrop)
        # - Отключает чередование цветов фона для строк (все строки будут одного цвета)
        self.setAlternatingRowColors(False)
        # - Разрешает выбор только строк (одна строка за раз)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        # - Ограничивает поведение выбора только строками (столбцы не выбираются)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        # - Отключает подсветку/выделение заголовков столбцов
        self.horizontalHeader().setHighlightSections(False)
        # - Отключает кнопку выбора всей таблицы (левый верхний угол)
        self.setCornerButtonEnabled(False)
        self.setStyleSheet("QTableWidget::item:selected { background-color: #b3d9ff; }")

        # Настройка основных свойств таблицы
        # - Устанавливает количество столбцов
        self.setColumnCount(len(COLUMN_NAMES))
        # - Задает названия столбцов
        for i, name in enumerate(COLUMN_NAMES):
            self.setHorizontalHeaderItem(i, QTableWidgetItem(name))
        # Настройка ширины столбцов
        # - Первый столбец подстраивается под ширину заголовка
        self.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        # - Остальные столбцы растягиваются для заполнения пространства
        for col in range(1, len(COLUMN_NAMES)):
            self.horizontalHeader().setSectionResizeMode(col, QHeaderView.Stretch)

    def _fill_row(self, row_id: int, row_number: int, row_name: RowName | None = None) -> None:
        delete_button = RedCrossButton()
        delete_button.clicked.connect(lambda: self.delete_row(row_id))
        self.setCellWidget(row_number, 0, delete_button)
        # Проходим по полям, связанным с кнопками
        for col, field in COLUMN_TO_FIELD.items():
            # Получаем имя файла для текущего поля
            file_name = None if row_name is None else getattr(row_name, field)
            # Создаем кнопку
            button = LoadDataButton(
                db=self.db,
                row_id=row_id,
                db_field_name=field,
                file_name=file_name,
                updated_data_in_row=self.updated_data_in_row
            )
            # Устанавливаем кнопку в ячейку
            self.setCellWidget(row_number, col, button)

    def _load_table_data(self):
        """Загружает данные из базы и обновляет таблицу."""
        # Очищаем таблицу
        self.setRowCount(0)
        # Получаем данные из базы
        rows = self.db.get_names_all_rows()
        # Если данных нет, добавляем пустую строку и выходим
        if not rows:
            self.add_row_to_end()
            return
        # Устанавливаем количество строк в таблице
        self.setRowCount(len(rows))
        # Заполняем таблицу данными
        for row_id, row_number, row_names in rows:
            self._fill_row(row_id, row_number, row_names)

    def updated_data_in_row(self, row_id: int) -> None:
        # Если это последняя строка, добавляем одну в конец
        if self.rowCount() - 1 == self.db.get_row_number_by_id(row_id):
            self.add_row_to_end()

        row_data = self.db.get_data_row(row_id)
        self.callback_change_active_row(row_data)

    def add_row_to_end(self) -> None:
        """Добавляет новую пустую строку в конец таблицы."""
        # Увеличиваем количество строк
        self.setRowCount(self.rowCount() + 1)
        # Создаем новую запись в базе данных и получаем её ID
        row_id, row_number = self.db.add_row_to_end()
        # Заполняем строку
        self._fill_row(row_id, row_number)

    def delete_row(self, row_id: int) -> None:
        """Удаление строки выбранной в таблице"""
        # Если это последняя строка, добавляем одну в конец, а выбранную удаляем
        if self.rowCount() - 1 == self.db.get_row_number_by_id(row_id):
            self.add_row_to_end()
        # Удаляем строку из таблицы
        self.removeRow(self.db.get_row_number_by_id(row_id))
        self.db.delete_row(row_id)

    def handle_selection_changed(self):
        """Обработчик изменения выделенной строки."""
        if self.callback_change_active_row:
            # Получаем индекс выделенной строки
            selected_rows = self.selectedRows()
            if selected_rows:
                row_number = selected_rows[0]
                # Получаем row_id для строки
                for row_id, rn, _ in self.db.get_names_all_rows():
                    if rn == row_number:
                        row_data = self.db.get_data_row(row_id)
                        self.callback_change_active_row(row_data)
                        break

    def selectedRows(self):
        """Возвращает список индексов выделенных строк."""
        return [index.row() for index in self.selectionModel().selectedRows()]