from PySide6.QtWidgets import QMainWindow, QPushButton, QFileDialog, QTableWidgetItem, QVBoxLayout, QLineEdit, QLabel, \
    QHeaderView, QApplication, QWidget
from PySide6.QtCore import Qt
from gui import Ui_MainWindow
from collections import namedtuple
import pandas as pd
import os
import shutil
import json
from datetime import datetime
from parsers import parser_all_data, parser_result_data
from plotting import Plotter
import logging

DataRow = namedtuple('DataRow', ['with_substance_file', 'without_substance_file', 'result_file', 'labeled_file'])


class GuiProgram(QMainWindow, Ui_MainWindow):
    def __init__(self):
        """Инициализирует главное окно приложения и создает директории."""
        super().__init__()
        self.setupUi(self)
        self.data_rows: list = []
        self.window_width: int = 10
        self.project_dir: str = "app_data"
        self.state_file: str = os.path.join(self.project_dir, "project_state.json")
        self.log_file: str = os.path.join(self.project_dir, "log.txt")
        os.makedirs(self.project_dir, exist_ok=True)
        logging.basicConfig(filename=self.log_file, level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')
        self.init_ui()

    def init_ui(self):
        """Настраивает компоненты интерфейса и загружает сохраненное состояние."""
        self.tableWidget.setColumnCount(5)
        self.tableWidget.setHorizontalHeaderLabels([
            "Удалить", "С веществом", "Без вещества", "Результат", "Размеченные данные"
        ])

        self.widget_plot = QWidget()
        self.plot_layout = QVBoxLayout(self.widget_plot)
        self.verticalLayout_2.addWidget(self.widget_plot)
        self.plotter: Plotter = Plotter(self.widget_plot, self)

        self.tableWidget.itemSelectionChanged.connect(self.plotter.plot_row_data)
        self.tableWidget.cellClicked.connect(self.handle_cell_click)

        self.control_layout = QVBoxLayout()
        self.widget_menu.layout().addLayout(self.control_layout, 0, 1)

        self.width_label = QLabel("Ширина окна [шт.]:")
        self.width_input = QLineEdit(str(self.window_width))
        self.width_input.textChanged.connect(self.update_window_width)
        self.control_layout.addWidget(self.width_label)
        self.control_layout.addWidget(self.width_input)

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

        QApplication.instance().aboutToQuit.connect(self.save_state)

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

    def copy_file_to_project(self, file_name: str, row: int, data_type: str) -> str:
        """
        Копирует файл в директорию строки и сохраняет как DataFrame.

        Parameters
        ----------
        file_name : str
            Путь к исходному файлу.
        row : int
            Индекс строки таблицы.
        data_type : str
            Тип данных ('with_substance', 'without_substance', 'result').

        Returns
        -------
        str or None
            Путь к сохраненному файлу DataFrame или None при ошибке.
        """
        if not file_name:
            return None
        row_dir = os.path.join(self.project_dir, f"row_{row}")
        os.makedirs(row_dir, exist_ok=True)
        dest_file = os.path.join(row_dir, f"{data_type}.csv")
        try:
            with open(file_name, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            if data_type == 'result':
                df = parser_result_data(lines)
            else:
                df = parser_all_data(lines)
            if df is None or df.empty:
                raise ValueError("Нет данных для парсинга")
            df.to_csv(dest_file, index=False)
            return dest_file
        except Exception as e:
            logging.error(f"Ошибка обработки файла {file_name}: {str(e)}")
            self.statusbar.showMessage(f"Ошибка обработки файла: {str(e)}", 5000)
            if os.path.exists(dest_file):
                os.remove(dest_file)
            return None

    def load_file(self, row: int, column: int):
        """
        Загружает и обрабатывает файл для ячейки таблицы.

        Parameters
        ----------
        row : int
            Индекс строки таблицы.
        column : int
            Индекс столбца таблицы (1-3 для типов данных).
        """
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл", "", "All Files (*)")
        if file_name:
            self.statusbar.showMessage("Обработка файла...", 5000)
            try:
                data_types = {1: 'with_substance', 2: 'without_substance', 3: 'result'}
                data_type = data_types.get(column)
                dest_file = self.copy_file_to_project(file_name, row, data_type)
                if dest_file:
                    current_data = self.data_rows[row]
                    if column == 1:
                        new_data = DataRow(dest_file, current_data.without_substance_file,
                                           current_data.result_file, current_data.labeled_file)
                    elif column == 2:
                        new_data = DataRow(current_data.with_substance_file, dest_file,
                                           current_data.result_file, current_data.labeled_file)
                    elif column == 3:
                        new_data = DataRow(current_data.with_substance_file,
                                           current_data.without_substance_file, dest_file,
                                           current_data.labeled_file)
                    self.data_rows[row] = new_data

                    file_item = QTableWidgetItem(f"{data_type}.csv")
                    file_item.setFlags(file_item.flags() & ~Qt.ItemIsEditable)
                    self.tableWidget.setItem(row, column, file_item)
                    self.tableWidget.removeCellWidget(row, column)

                    if row == self.tableWidget.rowCount() - 1:
                        self.add_row()

                    self.tableWidget.selectRow(row)
                    self.plotter.plot_row_data()
                    self.statusbar.showMessage("Файл успешно загружен", 5000)
                else:
                    self.statusbar.showMessage("Не удалось загрузить файл", 5000)
            except Exception as e:
                logging.error(f"Ошибка загрузки файла {file_name}: {str(e)}")
                self.statusbar.showMessage(f"Ошибка загрузки файла: {str(e)}", 5000)

    def remove_file(self, row: int, column: int):
        """
        Удаляет файл, связанный с ячейкой таблицы.

        Parameters
        ----------
        row : int
            Индекс строки таблицы.
        column : int
            Индекс столбца таблицы (1-4).
        """
        if column not in range(1, 5):
            return
        current_data = self.data_rows[row]
        file_map = {
            1: current_data.with_substance_file,
            2: current_data.without_substance_file,
            3: current_data.result_file,
            4: current_data.labeled_file
        }
        file_path = file_map.get(column)
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                self.statusbar.showMessage(f"Файл {file_path} удален", 5000)
            except Exception as e:
                logging.error(f"Ошибка удаления файла {file_path}: {str(e)}")
                self.statusbar.showMessage(f"Ошибка удаления файла: {str(e)}", 5000)

        # Удаляем labeled_file, если изменились данные в столбцах 1-3
        if column in (1, 2, 3) and current_data.labeled_file and os.path.exists(current_data.labeled_file):
            try:
                os.remove(current_data.labeled_file)
                self.statusbar.showMessage(f"Размеченные данные удалены из-за изменения данных", 5000)
                self.data_rows[row] = self.data_rows[row]._replace(labeled_file=None)
                self.tableWidget.setItem(row, 4, QTableWidgetItem(""))
            except Exception as e:
                logging.error(f"Ошибка удаления размеченных данных {current_data.labeled_file}: {str(e)}")
                self.statusbar.showMessage(f"Ошибка удаления размеченных данных: {str(e)}", 5000)

        if column == 1:
            self.data_rows[row] = self.data_rows[row]._replace(with_substance_file=None)
        elif column == 2:
            self.data_rows[row] = self.data_rows[row]._replace(without_substance_file=None)
        elif column == 3:
            self.data_rows[row] = self.data_rows[row]._replace(result_file=None)
        elif column == 4:
            self.data_rows[row] = self.data_rows[row]._replace(labeled_file=None)

        self.tableWidget.removeCellWidget(row, column)
        if column < 4:
            load_btn = QPushButton("Загрузить")
            load_btn.clicked.connect(lambda ch, r=row, c=column: self.load_file(r, c))
            self.tableWidget.setCellWidget(row, column, load_btn)
        else:
            self.tableWidget.setItem(row, 4, QTableWidgetItem(""))
        self.plotter.plot_row_data()

    def add_row(self):
        """Добавляет новую строку в таблицу и создает директорию."""
        row_count = self.tableWidget.rowCount()
        self.tableWidget.insertRow(row_count)
        row_dir = os.path.join(self.project_dir, f"row_{row_count}")
        os.makedirs(row_dir, exist_ok=True)
        self.data_rows.append(DataRow(None, None, None, None))
        self.setup_row(row_count)

    def delete_row(self, row: int):
        """
        Удаляет строку таблицы и связанную директорию.

        Parameters
        ----------
        row : int
            Индекс строки таблицы.
        """
        if self.tableWidget.rowCount() > 1:
            row_dir = os.path.join(self.project_dir, f"row_{row}")
            try:
                if os.path.exists(row_dir):
                    shutil.rmtree(row_dir)
                    self.statusbar.showMessage(f"Строка {row} удалена", 5000)
            except Exception as e:
                logging.error(f"Ошибка удаления директории {row_dir}: {str(e)}")
                self.statusbar.showMessage(f"Ошибка удаления папки: {str(e)}", 5000)
            self.tableWidget.removeRow(row)
            del self.data_rows[row]
            for i in range(row, self.tableWidget.rowCount()):
                old_dir = os.path.join(self.project_dir, f"row_{i + 1}")
                new_dir = os.path.join(self.project_dir, f"row_{i}")
                if os.path.exists(old_dir):
                    try:
                        os.rename(old_dir, new_dir)
                        current_data = self.data_rows[i]
                        new_data = DataRow(
                            os.path.join(new_dir, "with_substance.csv") if current_data.with_substance_file else None,
                            os.path.join(new_dir,
                                         "without_substance.csv") if current_data.without_substance_file else None,
                            os.path.join(new_dir, "result.csv") if current_data.result_file else None,
                            os.path.join(new_dir, "labeled.csv") if current_data.labeled_file else None
                        )
                        self.data_rows[i] = new_data
                    except Exception as e:
                        logging.error(f"Ошибка переименования директории {old_dir} в {new_dir}: {str(e)}")
            self.plotter.plot_row_data()

    def reset_table(self):
        """Сбрасывает таблицу до одной пустой строки."""
        self.plotter.stop_animation()
        try:
            for row in range(self.tableWidget.rowCount()):
                row_dir = os.path.join(self.project_dir, f"row_{row}")
                if os.path.exists(row_dir):
                    shutil.rmtree(row_dir)
        except Exception as e:
            logging.error(f"Ошибка очистки директорий: {str(e)}")
            self.statusbar.showMessage(f"Ошибка очистки данных: {str(e)}", 5000)
        self.tableWidget.setRowCount(1)
        self.data_rows = [DataRow(None, None, None, None)]
        self.setup_row(0)
        row_dir = os.path.join(self.project_dir, "row_0")
        os.makedirs(row_dir, exist_ok=True)
        self.plotter.plot_widget.clear()
        self.statusbar.showMessage("Таблица сброшена", 5000)

    def update_window_width(self, text: str):
        """Обновляет ширину окна из поля ввода."""
        try:
            self.window_width = int(text)
            self.statusbar.showMessage(f"Ширина окна обновлена: {text}", 5000)
        except ValueError:
            self.statusbar.showMessage("Ширина окна должна быть целым числом", 5000)

    def mark_data(self):
        """Создает и сохраняет размеченные данные для выбранной строки."""
        selected = self.tableWidget.selectedItems()
        if not selected:
            self.statusbar.showMessage("Выберите строку для разметки", 5000)
            return
        row = selected[0].row()
        data = self.data_rows[row]
        if not (data.with_substance_file and os.path.exists(data.with_substance_file) and
                data.result_file and os.path.exists(data.result_file)):
            self.statusbar.showMessage("Для разметки нужны данные с веществом и результат", 5000)
            return

        self.statusbar.showMessage("Разметка данных...", 5000)

        try:
            df_with = pd.read_csv(data.with_substance_file)
            df_result = pd.read_csv(data.result_file)
            freq_with, gamma_with = df_with['frequency'], df_with['gamma']
            result_freq = df_result['frequency']

            if not result_freq.size:
                self.statusbar.showMessage("Нет точек поглощения для разметки", 5000)
                return

            labeled_data = []
            half_window = self.window_width // 2

            # Интервалы с линией поглощения (True)
            used_indices = set()
            for point_freq in result_freq:
                idx = min(range(len(freq_with)), key=lambda i: abs(freq_with[i] - point_freq))
                start = idx - half_window
                end = idx + half_window
                # Пропускаем, если интервал выходит за границы или не равен window_width
                if start < 0 or end > len(freq_with) or (end - start) != self.window_width:
                    continue
                freq_segment = freq_with[start:end].tolist()
                gamma_segment = gamma_with[start:end].tolist()
                labeled_data.append((freq_segment, gamma_segment, True))
                used_indices.update(range(start, end))

            # Интервалы без линии поглощения (False)
            unmarked_count = len(labeled_data)
            i = 0
            while len(labeled_data) < unmarked_count * 2 and i < len(freq_with):
                start = i - half_window
                end = i + half_window
                if start >= 0 and end <= len(freq_with) and (end - start) == self.window_width:
                    if not any(start <= idx < end for idx in used_indices):
                        freq_segment = freq_with[start:end].tolist()
                        gamma_segment = gamma_with[start:end].tolist()
                        labeled_data.append((freq_segment, gamma_segment, False))
                        used_indices.update(range(start, end))
                i += 1

            if not labeled_data:
                self.statusbar.showMessage("Не удалось создать интервалы для разметки", 5000)
                return

            # Формируем DataFrame с явными группами
            frequencies = []
            gammas = []
            labels = []
            for freq_segment, gamma_segment, label in labeled_data:
                if len(freq_segment) != self.window_width or len(gamma_segment) != self.window_width:
                    logging.warning(f"Пропущен интервал с неверной длиной: {len(freq_segment)}")
                    continue
                frequencies.extend(freq_segment)
                gammas.extend(gamma_segment)
                labels.extend([label] * self.window_width)

            if not frequencies:
                self.statusbar.showMessage("Не удалось сформировать данные для разметки", 5000)
                return

            df = pd.DataFrame({
                'frequency': frequencies,
                'gamma': gammas,
                'label': labels
            })

            output_file = os.path.join(self.project_dir, f"row_{row}", "labeled.csv")
            df.to_csv(output_file, index=False)

            self.data_rows[row] = DataRow(data.with_substance_file, data.without_substance_file,
                                          data.result_file, output_file)
            self.tableWidget.setItem(row, 4, QTableWidgetItem("labeled.csv"))

            logging.info(
                f"Разметка завершена: {len(labeled_data) // 2} интервалов True, {len(labeled_data) // 2} интервалов False")
            self.statusbar.showMessage(f"Разметка завершена, сохранено в {output_file}", 5000)
        except Exception as e:
            logging.error(f"Ошибка разметки для строки {row}: {str(e)}")
            self.statusbar.showMessage(f"Ошибка разметки: {str(e)}", 5000)

    def save_all_labeled_data(self):
        """Объединяет и сохраняет все размеченные данные в один файл."""
        self.statusbar.showMessage("Сохранение общего результата...", 5000)

        try:
            all_labeled_data = []
            for row, data in enumerate(self.data_rows):
                if data.labeled_file and os.path.exists(data.labeled_file):
                    try:
                        df = pd.read_csv(data.labeled_file)
                        df['row'] = row
                        all_labeled_data.append(df)
                    except Exception as e:
                        logging.error(f"Ошибка чтения размеченных данных {data.labeled_file}: {str(e)}")
                        self.statusbar.showMessage(f"Ошибка чтения данных строки {row}: {str(e)}", 5000)
                        self.remove_file(row, 4)

            if not all_labeled_data:
                self.statusbar.showMessage("Нет размеченных данных для сохранения", 5000)
                return

            combined_df = pd.concat(all_labeled_data, ignore_index=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(self.project_dir, f"all_labeled_data_{timestamp}.csv")
            combined_df.to_csv(output_file, index=False)

            self.statusbar.showMessage(f"Общий результат сохранен в {output_file}", 5000)
        except Exception as e:
            logging.error(f"Ошибка сохранения общего результата: {str(e)}")
            self.statusbar.showMessage(f"Ошибка сохранения общего результата: {str(e)}", 5000)

    def handle_cell_click(self, row: int, column: int):
        """
        Обрабатывает клики по ячейкам, включая анимацию для размеченных данных.

        Parameters
        ----------
        row : int
            Индекс строки таблицы.
        column : int
            Индекс столбца таблицы.
        """
        logging.info(f"Клик по ячейке: строка {row}, столбец {column}")
        if column == 4 and self.data_rows[row].labeled_file and os.path.exists(self.data_rows[row].labeled_file):
            logging.info(f"Запуск анимации для строки {row}")
            self.plotter.start_animation(row)
            self.statusbar.showMessage("Запущена анимация размеченных данных", 5000)
        elif column in (1, 2, 3) and self.tableWidget.item(row, column):
            self.remove_file(row, column)

    def save_state(self):
        """Сохраняет состояние таблицы, ширину окна и выбранную строку в JSON-файл."""
        state = {
            'window_width': self.window_width,
            'selected_row': None,
            'table': []
        }
        selected = self.tableWidget.selectedItems()
        if selected:
            state['selected_row'] = selected[0].row()

        for row in range(self.tableWidget.rowCount()):
            row_data = {
                'with_substance': None,
                'without_substance': None,
                'result': None,
                'labeled': None
            }
            for col, key in [(1, 'with_substance'), (2, 'without_substance'),
                             (3, 'result'), (4, 'labeled')]:
                if self.data_rows[row]._asdict().get(f"{key}_file") and \
                        os.path.exists(self.data_rows[row]._asdict()[f"{key}_file"]):
                    row_data[key] = f"{key}.csv"
            state['table'].append(row_data)

        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f)
            logging.info("Состояние успешно сохранено")
        except Exception as e:
            logging.error(f"Ошибка сохранения состояния: {str(e)}")
            self.statusbar.showMessage(f"Ошибка сохранения состояния: {str(e)}", 5000)

    def load_state(self):
        """Загружает состояние таблицы, ширину окна и выбранную строку из JSON-файла."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)

                self.window_width = state.get('window_width', 10)
                self.width_input.setText(str(self.window_width))
                logging.info(f"Загружена ширина окна: {self.window_width}")

                self.tableWidget.setRowCount(0)
                self.data_rows = []

                for row_data in state.get('table', []):
                    row = self.tableWidget.rowCount()
                    row_dir = os.path.join(self.project_dir, f"row_{row}")
                    os.makedirs(row_dir, exist_ok=True)
                    self.tableWidget.insertRow(row)
                    new_row = DataRow(None, None, None, None)
                    self.data_rows.append(new_row)
                    self.setup_row(row)

                    for col, key in [(1, 'with_substance'), (2, 'without_substance'),
                                     (3, 'result'), (4, 'labeled')]:
                        if row_data.get(key):
                            file_name = row_data[key]
                            file_path = os.path.join(row_dir, file_name)
                            logging.info(f"Проверка файла: {file_path}")
                            if os.path.exists(file_path):
                                if col < 4:
                                    item = QTableWidgetItem(file_name)
                                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                                    self.tableWidget.setItem(row, col, item)
                                    self.tableWidget.removeCellWidget(row, col)
                                else:
                                    item = QTableWidgetItem(file_name)
                                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                                    self.tableWidget.setItem(row, col, item)
                                if col == 1:
                                    self.data_rows[row] = self.data_rows[row]._replace(with_substance_file=file_path)
                                elif col == 2:
                                    self.data_rows[row] = self.data_rows[row]._replace(without_substance_file=file_path)
                                elif col == 3:
                                    self.data_rows[row] = self.data_rows[row]._replace(result_file=file_path)
                                elif col == 4:
                                    self.data_rows[row] = self.data_rows[row]._replace(labeled_file=file_path)
                            else:
                                logging.error(f"Файл не найден: {file_path}")
                                self.statusbar.showMessage(f"Файл {file_name} не найден", 5000)

                if self.tableWidget.rowCount() > 0:
                    selected_row = state.get('selected_row', 0)
                    if selected_row is not None and selected_row < self.tableWidget.rowCount():
                        self.tableWidget.selectRow(selected_row)
                    else:
                        self.tableWidget.selectRow(0)
                    self.plotter.plot_row_data()
                logging.info(f"Загружено строк: {self.tableWidget.rowCount()}")
        except Exception as e:
            logging.error(f"Ошибка загрузки состояния: {str(e)}")
            self.statusbar.showMessage(f"Ошибка загрузки состояния: {str(e)}", 5000)

        if self.tableWidget.rowCount() == 0:
            self.tableWidget.setRowCount(1)
            self.data_rows.append(DataRow(None, None, None, None))
            self.setup_row(0)
            row_dir = os.path.join(self.project_dir, "row_0")
            os.makedirs(row_dir, exist_ok=True)
            logging.info("Создана пустая таблица с одной строкой")