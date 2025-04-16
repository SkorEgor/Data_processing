from PySide6.QtWidgets import QMainWindow, QPushButton, QFileDialog, QTableWidgetItem, QVBoxLayout, QLineEdit, QLabel, \
    QHeaderView, QApplication
from PySide6.QtCore import Qt, QTimer
from gui import Ui_MainWindow
import pandas as pd
import os
import shutil
import json
import numpy as np
from datetime import datetime
from parsers import parser_all_data, parser_result_data
from plotting import Plotter, DataRow
import logging


class GuiProgram(QMainWindow, Ui_MainWindow):
    def __init__(self):
        """Инициализирует главное окно приложения и создает директории."""
        super().__init__()
        self.setupUi(self)
        self.window_width: int = 10
        self.animation_delay: int = 500  # Уменьшено для быстрого отклика
        self.project_dir: str = "app_data"
        self.state_file: str = os.path.join(self.project_dir, "project_state.json")
        self.log_file: str = os.path.join(self.project_dir, "log.txt")
        os.makedirs(self.project_dir, exist_ok=True)
        logging.basicConfig(
            filename=self.log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            encoding='utf-8'
        )

        self.data_files: pd.DataFrame = pd.DataFrame(
            columns=["with_substance", "without_substance", "result", "labeled"])
        self.selected_row_number: int | None = None
        self.selected_row_data: DataRow = DataRow()

        self.current_frame = 0
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_labeled_data)

        self.init_ui()

    def init_ui(self):
        """Настраивает компоненты интерфейса и загружает сохраненное состояние."""
        self.tableWidget.setColumnCount(5)
        self.tableWidget.setHorizontalHeaderLabels([
            "Удалить", "С веществом", "Без вещества", "Результат", "Размеченные данные"
        ])

        self.plotter = Plotter(self)
        self.layout_plot_1.addWidget(self.plotter)

        self.tableWidget.itemSelectionChanged.connect(self.plot_selected_row)
        self.tableWidget.cellClicked.connect(self.handle_cell_click)

        self.control_layout = QVBoxLayout()
        self.widget_menu.layout().addLayout(self.control_layout, 0, 1)

        self.width_label = QLabel("Ширина окна [шт.]:")
        self.width_input = QLineEdit(str(self.window_width))
        self.width_input.textChanged.connect(self.update_window_width)
        self.control_layout.addWidget(self.width_label)
        self.control_layout.addWidget(self.width_input)

        self.delay_label = QLabel("Задержка анимации [мс]:")
        self.delay_input = QLineEdit(str(self.animation_delay))
        self.delay_input.textChanged.connect(self.update_animation_delay)
        self.control_layout.addWidget(self.delay_label)
        self.control_layout.addWidget(self.delay_input)

        self.mark_button = QPushButton("Разметить")
        self.mark_button.clicked.connect(self.mark_data)
        self.control_layout.addWidget(self.mark_button)

        self.reset_button = QPushButton("Сбросить таблицу")
        self.reset_button.clicked.connect(self.reset_table)
        self.control_layout.addWidget(self.reset_button)

        self.save_all_button = QPushButton("Сохранить общий результат")
        self.save_all_button.clicked.connect(self.save_all_labeled_data)
        self.control_layout.addWidget(self.save_all_button)

        self.control_layout.addStretch()

        for i in range(4):
            self.tableWidget.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)
        self.setWindowTitle("Data Analysis Studio")

        self.load_state()

    def show_status_message(self, message):
        """Отображает сообщение в статус-баре."""
        self.statusbar.showMessage(message, 5000)

    def plot_selected_row(self):
        """Отрисовывает данные выбранной строки."""
        selected = self.tableWidget.selectedItems()
        if not selected:
            logging.info("Нет выбранной строки")
            self.show_status_message("Выберите строку")
            self.plotter.plot_widget.clear()
            return

        row = selected[0].row()
        self.selected_row_number = row
        logging.info(f"Отрисовка строки {row}")

        try:
            row_data = self.data_files.iloc[row]
            self.selected_row_data = DataRow(
                with_substance=pd.read_csv(row_data.get("with_substance")) if row_data.get("with_substance") and os.path.exists(row_data.get("with_substance")) else None,
                without_substance=pd.read_csv(row_data.get("without_substance")) if row_data.get("without_substance") and os.path.exists(row_data.get("without_substance")) else None,
                result=pd.read_csv(row_data.get("result")) if row_data.get("result") and os.path.exists(row_data.get("result")) else None,
                intervals_positive=self.selected_row_data.intervals_positive if row_data.get("labeled") else None,
                intervals_negative=self.selected_row_data.intervals_negative if row_data.get("labeled") else None
            )
            logging.info("Отрисовка данных для строки")
            self.plotter.plot_data(self.selected_row_data)
            logging.info("График успешно отрисован")
            self.show_status_message("График обновлен")
        except (FileNotFoundError, pd.errors.EmptyDataError) as e:
            logging.error(f"Ошибка чтения файлов для строки {row}: {str(e)}")
            self.show_status_message(f"Ошибка чтения данных: {str(e)}")
            self.plotter.plot_widget.clear()

    def update_animation_delay(self, text: str):
        """Обновляет задержку анимации из поля ввода."""
        try:
            self.animation_delay = int(text)
            self.show_status_message(f"Задержка анимации обновлена: {self.animation_delay} мс")
            if self.animation_timer.isActive():
                self.animation_timer.stop()
                self.animation_timer.start(self.animation_delay)
        except ValueError:
            self.show_status_message("Задержка анимации должна быть целым числом")

    def setup_row(self, row: int):
        """Настраивает виджеты для строки таблицы."""
        delete_btn = QPushButton("Удалить")
        delete_btn.clicked.connect(lambda: self.delete_row(row))
        self.tableWidget.setCellWidget(row, 0, delete_btn)

        for col in range(1, 4):
            load_btn = QPushButton("Загрузить")
            load_btn.clicked.connect(lambda ch, r=row, c=col: self.load_file(r, c))
            self.tableWidget.setCellWidget(row, col, load_btn)

        self.tableWidget.setItem(row, 4, QTableWidgetItem(""))

    def copy_file_to_project(self, file_name: str, row: int, data_type: str) -> tuple[str | None, pd.DataFrame | None]:
        """Копирует файл в директорию строки и возвращает путь и DataFrame."""
        if not file_name:
            return None, None
        row_dir = os.path.join(self.project_dir, f"row_{row}")
        os.makedirs(row_dir, exist_ok=True)
        dest_file = os.path.join(row_dir, f"{data_type}.csv")
        with open(file_name, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        df = parser_result_data(lines) if data_type == 'result' else parser_all_data(lines)
        if df is None or df.empty:
            logging.error(f"Нет данных для парсинга в файле {file_name}")
            self.show_status_message("Файл пуст или некорректен")
            return None, None
        df.to_csv(dest_file, index=False)
        return dest_file, df

    def load_file(self, row: int, column: int):
        """Загружает и обрабатывает файл для ячейки таблицы."""
        file_name, _ = QFileDialog.getOpenFileName(self, "Выберите файл", "", "All Files (*)")
        if not file_name:
            return
        self.show_status_message("Обработка файла...")
        data_types = {1: 'with_substance', 2: 'without_substance', 3: 'result'}
        data_type = data_types.get(column)
        dest_file, df = self.copy_file_to_project(file_name, row, data_type)
        if dest_file and df is not None:
            while len(self.data_files) <= row:
                self.data_files.loc[len(self.data_files)] = [None, None, None, None]
            self.data_files.at[row, data_type] = dest_file
            if self.selected_row_number == row:
                setattr(self.selected_row_data, data_type, df)
            file_item = QTableWidgetItem(f"{data_type}.csv")
            file_item.setFlags(file_item.flags() & ~Qt.ItemIsEditable)
            self.tableWidget.setItem(row, column, file_item)
            self.tableWidget.removeCellWidget(row, column)
            if row == self.tableWidget.rowCount() - 1:
                self.add_row()
            self.tableWidget.selectRow(row)
            self.plot_selected_row()
            self.show_status_message("Файл успешно загружен")
        else:
            self.show_status_message("Не удалось загрузить файл")

    def remove_file(self, row: int, column: int):
        """Удаляет файл, связанный с ячейкой таблицы."""
        if column not in range(1, 5):
            return
        data_types = {1: 'with_substance', 2: 'without_substance', 3: 'result', 4: 'labeled'}
        data_type = data_types.get(column)
        if row >= len(self.data_files):
            return
        file_path = self.data_files.at[row, data_type]
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
            self.data_files.at[row, data_type] = None
        if self.selected_row_number == row:
            if data_type == 'with_substance':
                self.selected_row_data.with_substance = None
            elif data_type == 'without_substance':
                self.selected_row_data.without_substance = None
            elif data_type == 'result':
                self.selected_row_data.result = None
            elif data_type == 'labeled':
                self.selected_row_data.intervals_positive = None
                self.selected_row_data.intervals_negative = None
        if column in (1, 2, 3) and self.data_files.at[row, 'labeled'] is not None:
            row_dir = os.path.join(self.project_dir, f"row_{row}")
            for fname in ["positive.npy", "negative.npy"]:
                fpath = os.path.join(row_dir, fname)
                if os.path.exists(fpath):
                    os.remove(fpath)
            self.data_files.at[row, 'labeled'] = None
            self.tableWidget.setItem(row, 4, QTableWidgetItem(""))
        self.tableWidget.removeCellWidget(row, column)
        if column < 4:
            load_btn = QPushButton("Загрузить")
            load_btn.clicked.connect(lambda ch, r=row, c=column: self.load_file(r, c))
            self.tableWidget.setCellWidget(row, column, load_btn)
        if self.selected_row_number == row:
            self.plot_selected_row()

    def add_row(self):
        """Добавляет новую строку в таблицу и создает директорию."""
        row_count = self.tableWidget.rowCount()
        self.tableWidget.insertRow(row_count)
        row_dir = os.path.join(self.project_dir, f"row_{row_count}")
        os.makedirs(row_dir, exist_ok=True)
        self.data_files.loc[row_count] = [None, None, None, None]
        self.setup_row(row_count)

    def delete_row(self, row: int):
        """Удаляет строку таблицы и связанную директорию."""
        if self.tableWidget.rowCount() <= 1:
            return
        row_dir = os.path.join(self.project_dir, f"row_{row}")
        if os.path.exists(row_dir):
            shutil.rmtree(row_dir)
        self.tableWidget.removeRow(row)
        self.data_files = self.data_files.drop(row).reset_index(drop=True)
        for i in range(row, self.tableWidget.rowCount()):
            old_dir = os.path.join(self.project_dir, f"row_{i + 1}")
            new_dir = os.path.join(self.project_dir, f"row_{i}")
            if os.path.exists(old_dir):
                os.rename(old_dir, new_dir)
                for col in ['with_substance', 'without_substance', 'result']:
                    if i < len(self.data_files) and self.data_files.at[i, col]:
                        self.data_files.at[i, col] = os.path.join(new_dir, f"{col}.csv")
        if self.selected_row_number == row:
            self.selected_row_number = None
            self.selected_row_data = DataRow()
        elif self.selected_row_number is not None and self.selected_row_number > row:
            self.selected_row_number -= 1
        self.plot_selected_row()

    def reset_table(self):
        """Сбрасывает таблицу до одной пустой строки."""
        self.stop_animation()
        for row in range(self.tableWidget.rowCount()):
            row_dir = os.path.join(self.project_dir, f"row_{row}")
            if os.path.exists(row_dir):
                shutil.rmtree(row_dir)
        self.tableWidget.setRowCount(1)
        self.data_files = pd.DataFrame(columns=["with_substance", "without_substance", "result", "labeled"])
        self.data_files.loc[0] = [None, None, None, None]
        self.setup_row(0)
        row_dir = os.path.join(self.project_dir, "row_0")
        os.makedirs(row_dir, exist_ok=True)
        self.selected_row_number = None
        self.selected_row_data = DataRow()
        self.plotter.plot_widget.clear()
        self.show_status_message("Таблица сброшена")

    def update_window_width(self, text: str):
        """Обновляет ширину окна из поля ввода."""
        try:
            self.window_width = int(text)
            self.show_status_message(f"Ширина окна обновлена: {self.window_width}")
            self.plot_selected_row()
        except ValueError:
            self.show_status_message("Ширина окна должна быть целым числом")

    def mark_data(self):
        """Создает и сохраняет размеченные данные для выбранной строки."""
        selected = self.tableWidget.selectedItems()
        if not selected:
            self.show_status_message("Выберите строку для разметки")
            return
        row = selected[0].row()
        if row >= len(self.data_files):
            self.show_status_message("Неверная строка")
            return

        row_data = self.data_files.iloc[row]
        temp_data_row = DataRow(
            with_substance=pd.read_csv(row_data.get("with_substance")) if row_data.get("with_substance") and os.path.exists(row_data.get("with_substance")) else None,
            result=pd.read_csv(row_data.get("result")) if row_data.get("result") and os.path.exists(row_data.get("result")) else None
        )

        self.show_status_message("Разметка данных...")
        if not temp_data_row.mark_data(self.window_width):
            self.show_status_message("Не удалось создать интервалы для разметки")
            return

        row_dir = os.path.join(self.project_dir, f"row_{row}")
        os.makedirs(row_dir, exist_ok=True)
        np.save(os.path.join(row_dir, "positive.npy"), temp_data_row.intervals_positive)
        np.save(os.path.join(row_dir, "negative.npy"), temp_data_row.intervals_negative)

        interval_starts = []
        for i in range(len(temp_data_row.intervals_positive)):
            interval_starts.append((i * self.window_width, True))
        for i in range(len(temp_data_row.intervals_negative)):
            interval_starts.append((i * self.window_width, False))
        interval_starts.sort()

        self.data_files.at[row, 'labeled'] = interval_starts
        self.tableWidget.setItem(row, 4, QTableWidgetItem("Размечено"))
        if self.selected_row_number == row:
            self.selected_row_data.intervals_positive = temp_data_row.intervals_positive
            self.selected_row_data.intervals_negative = temp_data_row.intervals_negative

        logging.info(f"Разметка завершена: {len(temp_data_row.intervals_positive)} позитивных, {len(temp_data_row.intervals_negative)} негативных")
        self.show_status_message(f"Разметка завершена, сохранено в {row_dir}")

    def save_all_labeled_data(self):
        """Объединяет и сохраняет все размеченные данные в один файл."""
        self.show_status_message("Сохранение общего результата...")
        all_data = []
        for row in range(len(self.data_files)):
            if self.data_files.at[row, 'labeled'] is not None:
                row_dir = os.path.join(self.project_dir, f"row_{row}")
                positive_file = os.path.join(row_dir, "positive.npy")
                negative_file = os.path.join(row_dir, "negative.npy")
                if os.path.exists(positive_file) and os.path.exists(negative_file):
                    positive = np.load(positive_file)
                    negative = np.load(negative_file)
                    positive_df = pd.DataFrame(positive, columns=[f"gamma_{i}" for i in range(positive.shape[1])])
                    negative_df = pd.DataFrame(negative, columns=[f"gamma_{i}" for i in range(negative.shape[1])])
                    positive_df['label'] = True
                    negative_df['label'] = False
                    positive_df['row'] = row
                    negative_df['row'] = row
                    all_data.extend([positive_df, negative_df])
        if not all_data:
            self.show_status_message("Нет размеченных данных для сохранения")
            return
        combined_df = pd.concat(all_data, ignore_index=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(self.project_dir, f"all_labeled_data_{timestamp}.csv")
        combined_df.to_csv(output_file, index=False)
        self.show_status_message(f"Общий результат сохранен в {output_file}")

    def handle_cell_click(self, row: int, column: int):
        """Обрабатывает клики по ячейкам, включая анимацию для размеченных данных."""
        logging.info(f"Клик по ячейке: строка {row}, столбец {column}")
        self.tableWidget.selectRow(row)  # Всегда устанавливаем выбор
        if column == 4 and row < len(self.data_files) and self.data_files.at[row, 'labeled'] is not None:
            if self.animation_timer.isActive():
                self.stop_animation()
            else:
                self.start_animation(row)
        elif column in (1, 2, 3) and self.tableWidget.item(row, column):
            self.remove_file(row, column)

    def start_animation(self, row: int):
        """Запускает анимацию для указанной строки."""
        self.stop_animation()
        self.selected_row_number = row
        self.tableWidget.selectRow(row)  # Убеждаемся, что строка выбрана
        if row >= len(self.data_files) or self.data_files.at[row, 'labeled'] is None:
            logging.error(f"Нет размеченных данных для строки {row}")
            self.show_status_message("Нет размеченных данных для анимации")
            return
        row_dir = os.path.join(self.project_dir, f"row_{row}")
        positive_file = os.path.join(row_dir, "positive.npy")
        negative_file = os.path.join(row_dir, "negative.npy")
        if not (os.path.exists(positive_file) and os.path.exists(negative_file)):
            logging.error(f"Файлы .npy не найдены в {row_dir}")
            self.show_status_message("Файлы размеченных данных не найдены")
            return

        try:
            self.selected_row_data.intervals_positive = np.load(positive_file, allow_pickle=True)
            self.selected_row_data.intervals_negative = np.load(negative_file, allow_pickle=True)
            logging.info(f"Загружено {len(self.selected_row_data.intervals_positive)} позитивных и {len(self.selected_row_data.intervals_negative)} негативных интервалов")
            if not self.selected_row_data.intervals_positive.size or not self.selected_row_data.intervals_negative.size:
                logging.error(f"Пустые интервалы для строки {row}")
                self.show_status_message("Нет интервалов для анимации")
                return
            self.current_frame = 0
            self.plotter.plot_widget.clear()  # Очищаем перед анимацией
            self.animation_timer.start(self.animation_delay)
            logging.info(f"Запущена анимация для строки {row} с задержкой {self.animation_delay} мс")
            self.show_status_message("Запущена анимация размеченных данных")
        except Exception as e:
            logging.error(f"Ошибка загрузки интервалов: {str(e)}")
            self.show_status_message(f"Ошибка анимации: {str(e)}")

    def stop_animation(self):
        """Останавливает анимацию."""
        if self.animation_timer.isActive():
            self.animation_timer.stop()
            logging.info("Анимация остановлена")
            self.show_status_message("Анимация остановлена")
        self.current_frame = 0
        if self.selected_row_number is not None:
            logging.info(f"Восстановление графика строки {self.selected_row_number}")
            self.plot_selected_row()

    def animate_labeled_data(self):
        """Отрисовывает следующий кадр анимации."""
        if (self.selected_row_data.intervals_positive is None or
            self.selected_row_data.intervals_negative is None):
            logging.error("Анимация прервана: отсутствуют интервалы")
            self.stop_animation()
            return

        total_positive = len(self.selected_row_data.intervals_positive)
        total_negative = len(self.selected_row_data.intervals_negative)
        total_intervals = total_positive + total_negative

        if total_intervals == 0:
            logging.error("Анимация прервана: нет интервалов")
            self.stop_animation()
            return

        if self.current_frame >= total_intervals:
            logging.info("Анимация завершена")
            self.stop_animation()
            return

        try:
            if self.current_frame < total_positive:
                interval = self.selected_row_data.intervals_positive[self.current_frame]
                logging.info(f"Отрисовка позитивного интервала #{self.current_frame + 1}")
                self.plotter.plot_widget.plot_positive_interval(interval)
                self.show_status_message(f"Отрисовка позитивного интервала #{self.current_frame + 1}")
            else:
                interval = self.selected_row_data.intervals_negative[self.current_frame - total_positive]
                logging.info(f"Отрисовка негативного интервала #{self.current_frame + 1 - total_positive}")
                self.plotter.plot_widget.plot_negative(interval)
                self.show_status_message(f"Отрисовка негативного интервала #{self.current_frame + 1 - total_positive}")
            self.current_frame += 1
        except IndexError as e:
            logging.error(f"Ошибка доступа к интервалу, frame={self.current_frame}: {str(e)}")
            self.show_status_message("Ошибка анимации: неверный интервал")
            self.stop_animation()

    def save_state(self):
        """Сохраняет состояние таблицы, ширину окна и выбранную строку в JSON-файл."""
        state = {
            'window_width': self.window_width,
            'animation_delay': self.animation_delay,
            'selected_row': self.selected_row_number,
            'table': []
        }
        for row in range(len(self.data_files)):
            row_data = {
                'with_substance': None,
                'without_substance': None,
                'result': None,
                'labeled': None
            }
            for col in ['with_substance', 'without_substance', 'result']:
                if self.data_files.at[row, col] and os.path.exists(self.data_files.at[row, col]):
                    row_data[col] = f"{col}.csv"
            if self.data_files.at[row, 'labeled'] is not None:
                row_data['labeled'] = "Размечено"
            state['table'].append(row_data)
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f)
        logging.info("Состояние успешно сохранено")

    def load_state(self):
        """Загружает состояние таблицы, ширину окна и выбранную строку из JSON-файла."""
        if not os.path.exists(self.state_file):
            self.tableWidget.setRowCount(1)
            self.data_files.loc[0] = [None, None, None, None]
            self.setup_row(0)
            row_dir = os.path.join(self.project_dir, "row_0")
            os.makedirs(row_dir, exist_ok=True)
            logging.info("Создана пустая таблица с одной строкой")
            return

        with open(self.state_file, 'r', encoding='utf-8') as f:
            state = json.load(f)

        self.window_width = state.get('window_width', 10)
        self.animation_delay = state.get('animation_delay', 500)
        self.width_input.setText(str(self.window_width))
        self.delay_input.setText(str(self.animation_delay))
        logging.info(f"Загружена ширина окна: {self.window_width}, задержка анимации: {self.animation_delay}")

        self.tableWidget.setRowCount(0)
        self.data_files = pd.DataFrame(columns=["with_substance", "without_substance", "result", "labeled"])

        for row_data in state.get('table', []):
            row = self.tableWidget.rowCount()
            row_dir = os.path.join(self.project_dir, f"row_{row}")
            os.makedirs(row_dir, exist_ok=True)
            self.tableWidget.insertRow(row)
            self.data_files.loc[row] = [None, None, None, None]
            self.setup_row(row)

            for col, key in [(1, 'with_substance'), (2, 'without_substance'), (3, 'result')]:
                if row_data.get(key):
                    file_name = row_data[key]
                    file_path = os.path.join(row_dir, file_name)
                    if os.path.exists(file_path):
                        item = QTableWidgetItem(file_name)
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                        self.tableWidget.setItem(row, col, item)
                        self.tableWidget.removeCellWidget(row, col)
                        self.data_files.at[row, key] = file_path
                    else:
                        logging.error(f"Файл не найден: {file_path}")

            if row_data.get('labeled'):
                positive_file = os.path.join(row_dir, "positive.npy")
                negative_file = os.path.join(row_dir, "negative.npy")
                if os.path.exists(positive_file) and os.path.exists(negative_file):
                    item = QTableWidgetItem("Размечено")
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.tableWidget.setItem(row, 4, item)
                    positive = np.load(positive_file, allow_pickle=True)
                    negative = np.load(negative_file, allow_pickle=True)
                    interval_starts = []
                    for i in range(len(positive)):
                        interval_starts.append((i * self.window_width, True))
                    for i in range(len(negative)):
                        interval_starts.append((i * self.window_width, False))
                    interval_starts.sort()
                    self.data_files.at[row, 'labeled'] = interval_starts
                    if state.get('selected_row') == row:
                        self.selected_row_data.intervals_positive = positive
                        self.selected_row_data.intervals_negative = negative

        if self.tableWidget.rowCount() > 0:
            selected_row = state.get('selected_row', 0)
            if selected_row is not None and selected_row < self.tableWidget.rowCount():
                self.selected_row_number = selected_row
                self.tableWidget.selectRow(selected_row)
                self.plot_selected_row()
            else:
                self.tableWidget.selectRow(0)
                self.plot_selected_row()
        logging.info(f"Загружено строк: {self.tableWidget.rowCount()}")