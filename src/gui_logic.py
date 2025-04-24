import os
import json
import shutil
import numpy as np
import pandas as pd
from datetime import datetime
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QMainWindow, QPushButton, QFileDialog, QTableWidgetItem, QVBoxLayout, QLineEdit, QLabel, QHeaderView, QInputDialog
)
from plotting import Plotter, DataRow
from parsers import parser_all_data, parser_result_data
from logger import log
from gui import Ui_MainWindow
from src.setting import PROJECT_DIR, PATH_STATE_FILE, DEFAULT_WINDOW_WIDTH, DEFAULT_ANIMATION_DELAY


class GuiProgram(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.window_width = DEFAULT_WINDOW_WIDTH
        self.animation_delay = DEFAULT_ANIMATION_DELAY
        os.makedirs(PROJECT_DIR, exist_ok=True)

        self.data_files = pd.DataFrame(columns=["with_substance", "without_substance", "result", "labeled"])
        self.selected_row_number = None
        self.selected_row_data = DataRow()
        self.current_frame = 0
        self.animation_timer = QTimer()
        self.init_ui()

    def init_ui(self):
        """Настраивает интерфейс."""
        self.plotter = Plotter(self)
        self.layout_plot_1.addWidget(self.plotter)
        self.tableWidget.itemSelectionChanged.connect(self.plot_selected_row)
        self.tableWidget.cellClicked.connect(self.handle_cell_click)

        self.control_layout = QVBoxLayout()
        self.widget_menu.layout().addLayout(self.control_layout, 0, 1)

        # Создаем и сохраняем поля ввода
        self.width_input = self._add_control(
            "Ширина окна [шт.]:", self.update_window_width, str(self.window_width)
        )
        self.delay_input = self._add_control(
            "Задержка анимации [мс]:", self.update_animation_delay, str(self.animation_delay)
        )

        for text, slot in [
            ("Разметить", self.mark_data),
            ("Сбросить таблицу", self.reset_table),
            ("Сохранить общий результат", self.save_all_labeled_data),
            ("Интерполировать данные", self.interpolate_selected_row)
        ]:
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            self.control_layout.addWidget(btn)

        self.control_layout.addStretch()
        self.tableWidget.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.setWindowTitle("Data Analysis Studio")
        self.load_state()

    def _add_control(self, label_text: str, slot, default_text: str):
        """Добавляет метку и поле ввода."""
        label = QLabel(label_text)
        input_field = QLineEdit(default_text)
        input_field.textChanged.connect(slot)
        self.control_layout.addWidget(label)
        self.control_layout.addWidget(input_field)
        return input_field

    def plot_selected_row(self):
        """Отрисовывает данные выбранной строки."""
        selected = self.tableWidget.selectedItems()
        if not selected:
            log.info("Нет выбранной строки")
            self._show_status_message("Выберите строку")
            self.plotter.plot_widget.clear()
            return

        row = selected[0].row()
        self.selected_row_number = row
        row_data = self.data_files.iloc[row]
        row_dir = self.ensure_row_dir(row)
        self.selected_row_data = DataRow(
            with_substance_path=os.path.join(row_dir, row_data["with_substance"]) if row_data[
                "with_substance"] else None,
            without_substance_path=os.path.join(row_dir, row_data["without_substance"]) if row_data[
                "without_substance"] else None,
            result_path=os.path.join(row_dir, row_data["result"]) if row_data["result"] else None
        )
        log.info("Отрисовка данных для строки")
        self.plotter.plot_widget.plot_row(self.selected_row_data)
        self._show_status_message("График обновлен")

    def ensure_row_dir(self, row: int) -> str:
        """Создает и возвращает директорию для строки."""
        row_dir = os.path.join(PROJECT_DIR, f"row_{row}")
        os.makedirs(row_dir, exist_ok=True)
        return row_dir

    def load_file(self, row: int, column: int):
        """Загружает файл в ячейку."""
        file_name, _ = QFileDialog.getOpenFileName(self, "Выберите файл", "", "All Files (*)")
        if not file_name:
            return
        data_types = {1: "with_substance", 2: "without_substance", 3: "result"}
        data_type = data_types.get(column)
        row_dir = self.ensure_row_dir(row)
        new_file_name, dest_file = self._process_file(file_name, row_dir, data_type)
        if dest_file:
            while len(self.data_files) <= row:
                self.data_files.loc[len(self.data_files)] = [None, None, None, None]
            self.data_files.at[row, data_type] = new_file_name
            self._update_table_cell(row, column, new_file_name)
            if row == self.tableWidget.rowCount() - 1:
                self.add_row()
            self.tableWidget.selectRow(row)
            self.plot_selected_row()
            self._show_status_message("Файл загружен")

    def _process_file(self, file_name: str, row_dir: str, data_type: str) -> tuple[str | None, str | None]:
        """Обрабатывает и сохраняет файл."""
        with open(file_name, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        df = parser_result_data(lines) if data_type == 'result' else parser_all_data(lines)
        if df is None or df.empty:
            log.error(f"Нет данных в файле {file_name}")
            self._show_status_message("Файл пуст")
            return None, None
        new_file_name = os.path.splitext(os.path.basename(file_name))[0] + ".csv"
        dest_file = os.path.join(row_dir, new_file_name)
        df.to_csv(dest_file, index=False)
        self.save_state()
        return new_file_name, dest_file

    def _update_table_cell(self, row: int, column: int, text: str):
        """Обновляет ячейку таблицы."""
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        self.tableWidget.setItem(row, column, item)
        self.tableWidget.removeCellWidget(row, column)

    def remove_file(self, row: int, column: int):
        """Удаляет файл из ячейки."""
        data_types = {1: "with_substance", 2: "without_substance", 3: "result", 4: "labeled"}
        data_type = data_types.get(column)
        if row >= len(self.data_files) or not self.data_files.at[row, data_type]:
            return
        file_path = os.path.join(self.ensure_row_dir(row), self.data_files.at[row, data_type])
        if os.path.exists(file_path):
            os.remove(file_path)
            self.data_files.at[row, data_type] = None
        if column == 4:
            for fname in ["positive.npy", "negative.npy", "output_positive.npy", "output_negative.npy"]:
                fpath = os.path.join(self.ensure_row_dir(row), fname)
                if os.path.exists(fpath):
                    os.remove(fpath)
            self.tableWidget.setItem(row, 4, QTableWidgetItem(""))
        if column < 4:
            load_btn = QPushButton("Загрузить")
            load_btn.clicked.connect(lambda: self.load_file(row, column))
            self.tableWidget.setCellWidget(row, column, load_btn)
        if self.selected_row_number == row:
            self.plot_selected_row()

    def add_row(self):
        """Добавляет новую строку в таблицу."""
        row = self.tableWidget.rowCount()
        self.tableWidget.insertRow(row)
        self.data_files.loc[row] = [None, None, None, None]
        self.setup_row(row)

    def setup_row(self, row: int):
        """Настраивает виджеты строки."""
        delete_btn = QPushButton("Удалить")
        delete_btn.clicked.connect(lambda: self.delete_row(row))
        self.tableWidget.setCellWidget(row, 0, delete_btn)
        for col in range(1, 4):
            load_btn = QPushButton("Загрузить")
            load_btn.clicked.connect(lambda ch, r=row, c=col: self.load_file(r, c))
            self.tableWidget.setCellWidget(row, col, load_btn)
        self.tableWidget.setItem(row, 4, QTableWidgetItem(""))

    def delete_row(self, row: int):
        """Удаляет строку."""
        if self.tableWidget.rowCount() <= 1:
            return
        row_dir = self.ensure_row_dir(row)
        if os.path.exists(row_dir):
            shutil.rmtree(row_dir)
        self.tableWidget.removeRow(row)
        self.data_files = self.data_files.drop(row).reset_index(drop=True)
        for i in range(row, self.tableWidget.rowCount()):
            old_dir = os.path.join(PROJECT_DIR, f"row_{i + 1}")
            new_dir = os.path.join(PROJECT_DIR, f"row_{i}")
            if os.path.exists(old_dir):
                os.rename(old_dir, new_dir)
                for col in ["with_substance", "without_substance", "result"]:
                    if i < len(self.data_files) and self.data_files.at[i, col]:
                        self.data_files.at[i, col] = os.path.basename(self.data_files.at[i, col])
        if self.selected_row_number == row:
            self.selected_row_number = None
            self.selected_row_data = DataRow()
        elif self.selected_row_number and self.selected_row_number > row:
            self.selected_row_number -= 1
        self.plot_selected_row()

    def reset_table(self):
        """Сбрасывает таблицу."""
        self.stop_animation()
        for row in range(self.tableWidget.rowCount()):
            row_dir = os.path.join(PROJECT_DIR, f"row_{row}")
            if os.path.exists(row_dir):
                shutil.rmtree(row_dir)
        self.tableWidget.setRowCount(1)
        self.data_files = pd.DataFrame(columns=["with_substance", "without_substance", "result", "labeled"])
        self.data_files.loc[0] = [None, None, None, None]
        self.setup_row(0)
        self.selected_row_number = None
        self.selected_row_data = DataRow()
        self.plotter.plot_widget.clear()
        self._show_status_message("Таблица сброшена")

    def update_window_width(self, text: str):
        """Обновляет ширину окна."""
        try:
            self.window_width = int(text)
            self._show_status_message(f"Ширина окна: {self.window_width}")
            self.plot_selected_row()
        except ValueError:
            self._show_status_message("Ширина окна должна быть числом")

    def update_animation_delay(self, text: str):
        """Обновляет задержку анимации."""
        try:
            self.animation_delay = int(text)
            self._show_status_message(f"Задержка анимации: {self.animation_delay} мс")
            if self.animation_timer.isActive():
                self.animation_timer.stop()
                self.animation_timer.start(self.animation_delay)
        except ValueError:
            self._show_status_message("Задержка анимации должна быть числом")

    def mark_data(self):
        """Размечает данные выбранной строки."""
        if not self.selected_row_number_valid():
            return
        row = self.selected_row_number
        self._show_status_message("Разметка данных...")

        # Получаем данные
        with_substance = self.selected_row_data.get_with_substance()
        result = self.selected_row_data.get_result()
        if with_substance is None or result is None:
            self._show_status_message("Для разметки нужны данные с веществом и результат")
            log.error("Отсутствуют данные with_substance или result")
            return

        freq_with = with_substance['frequency']
        gamma_with = with_substance['gamma']
        result_freq = result['frequency']
        if freq_with.empty or gamma_with.empty or result_freq.empty:
            self._show_status_message("Данные пусты или некорректны")
            log.error("Пустые столбцы frequency или gamma")
            return

        labeled_data = []
        half_window = self.window_width // 2

        # Позитивные интервалы (с точками поглощения)
        for point_freq in result_freq:
            idx = min(range(len(freq_with)), key=lambda i: abs(freq_with[i] - point_freq))
            start = max(0, idx - half_window)
            end = min(len(freq_with), idx + half_window + 1)
            if start == 0:
                prefix = [freq_with.iloc[0]] * (half_window - idx)
                freq_segment = prefix + freq_with.iloc[:end].tolist()
                gamma_segment = [gamma_with.iloc[0]] * (half_window - idx) + gamma_with.iloc[:end].tolist()
            elif end == len(freq_with):
                suffix = [freq_with.iloc[-1]] * (half_window - (len(freq_with) - idx - 1))
                freq_segment = freq_with.iloc[start:].tolist() + suffix
                gamma_segment = gamma_with.iloc[start:].tolist() + [gamma_with.iloc[-1]] * (
                            half_window - (len(freq_with) - idx - 1))
            else:
                freq_segment = freq_with.iloc[start:end].tolist()
                gamma_segment = gamma_with.iloc[start:end].tolist()
            labeled_data.append((freq_segment, gamma_segment, True))

        # Индексы, занятые позитивными интервалами
        point_indices = [min(range(len(freq_with)), key=lambda i: abs(freq_with[i] - f)) for f in result_freq]
        used_indices = set()
        for idx in point_indices:
            used_indices.update(range(max(0, idx - half_window), min(len(freq_with), idx + half_window + 1)))

        # Негативные интервалы (без точек поглощения)
        unmarked_count = len(labeled_data)
        i = 0
        while len(labeled_data) < unmarked_count * 2 and i < len(freq_with):
            if i not in used_indices:
                start = max(0, i - half_window)
                end = min(len(freq_with), i + half_window + 1)
                if not any(start <= idx < end for idx in used_indices):
                    if start == 0:
                        prefix = [freq_with.iloc[0]] * (half_window - i)
                        freq_segment = prefix + freq_with.iloc[:end].tolist()
                        gamma_segment = [gamma_with.iloc[0]] * (half_window - i) + gamma_with.iloc[:end].tolist()
                    elif end == len(freq_with):
                        suffix = [freq_with.iloc[-1]] * (half_window - (len(freq_with) - i - 1))
                        freq_segment = freq_with.iloc[start:].tolist() + suffix
                        gamma_segment = gamma_with.iloc[start:].tolist() + [gamma_with.iloc[-1]] * (
                                    half_window - (len(freq_with) - i - 1))
                    else:
                        freq_segment = freq_with.iloc[start:end].tolist()
                        gamma_segment = gamma_with.iloc[start:end].tolist()
                    labeled_data.append((freq_segment, gamma_segment, False))
                    used_indices.update(range(start, end))
            i += 1

        # Создаем DataFrame для размеченных данных
        df = pd.DataFrame({
            'frequency': [f for freq_segment, _, _ in labeled_data for f in freq_segment],
            'gamma': [g for _, gamma_segment, _ in labeled_data for g in gamma_segment],
            'label': [l for _, _, l in labeled_data for _ in range(len(labeled_data[0][0]))]
        })

        # Сохраняем в CSV
        row_dir = self.ensure_row_dir(row)
        output_file = os.path.join(row_dir, f"labeled_data_row_{row}.csv")
        df.to_csv(output_file, index=False)

        # Обновляем DataRow и таблицу
        self.data_files.at[row, "labeled"] = os.path.basename(output_file)
        self._update_table_cell(row, 4, "Размечено")
        self.save_state()  # Сохраняем состояние после разметки
        self._show_status_message(f"Разметка завершена, сохранено в {output_file}")
        log.info(f"Разметка завершена для строки {row}, сохранено в {output_file}")

    def interpolate_selected_row(self):
        """Интерполирует данные выбранной строки."""
        if not self.selected_row_number_valid():
            return
        step, ok = QInputDialog.getDouble(self, "Шаг интерполяции", "Введите шаг:", 0.06, 0.01, 1.0, 2)
        if not ok:
            return
        self.selected_row_data.interpolate_data(step)
        row_dir = self.ensure_row_dir(self.selected_row_number)
        for attr in ["with_substance_path", "without_substance_path", "result_path"]:
            if getattr(self.selected_row_data, attr):
                self.data_files.at[self.selected_row_number, attr.split("_path")[0]] = os.path.basename(
                    getattr(self.selected_row_data, attr))
        self.plot_selected_row()
        self._show_status_message("Данные интерполированы")

    def selected_row_number_valid(self) -> bool:
        """Проверяет, выбрана ли строка."""
        if self.selected_row_number is None or self.selected_row_number >= len(self.data_files):
            self._show_status_message("Выберите строку")
            return False
        return True

    def save_all_labeled_data(self):
        """Сохраняет все размеченные данные."""
        all_data = []
        for row in range(len(self.data_files)):
            if self.data_files.at[row, "labeled"]:
                row_dir = self.ensure_row_dir(row)
                positive = np.load(os.path.join(row_dir, "positive.npy"), allow_pickle=True)
                negative = np.load(os.path.join(row_dir, "negative.npy"), allow_pickle=True)
                for df, label in [(positive, True), (negative, False)]:
                    df = pd.DataFrame(df, columns=[f"gamma_{i}" for i in range(df.shape[1])])
                    df["label"] = label
                    df["row"] = row
                    all_data.append(df)
        if not all_data:
            self._show_status_message("Нет размеченных данных")
            return
        combined_df = pd.concat(all_data, ignore_index=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(PROJECT_DIR, f"all_labeled_data_{timestamp}.csv")
        combined_df.to_csv(output_file, index=False)
        self._show_status_message(f"Результат сохранен в {output_file}")

    def handle_cell_click(self, row: int, column: int):
        """Обрабатывает клики по ячейкам."""
        self.tableWidget.selectRow(row)
        if column == 4 and self.data_files.at[row, "labeled"]:
            self.start_animation(row) if not self.animation_timer.isActive() else self.stop_animation()
        elif column in (1, 2, 3) and self.tableWidget.item(row, column):
            self.remove_file(row, column)

    def start_animation(self, row: int):
        """Запускает анимацию."""
        self.stop_animation()
        self.selected_row_number = row
        row_dir = self.ensure_row_dir(row)
        for fname, attr in [
            ("positive.npy", "input_intervals_positive"),
            ("negative.npy", "input_intervals_negative"),
            ("output_positive.npy", "output_intervals_positive"),
            ("output_negative.npy", "output_intervals_negative")
        ]:
            fpath = os.path.join(row_dir, fname)
            setattr(self.selected_row_data, attr, np.load(fpath, allow_pickle=True) if os.path.exists(fpath) else None)
        if not self.selected_row_data.input_intervals_positive.size:
            self._show_status_message("Нет интервалов для анимации")
            return
        self.current_frame = 0
        self.plotter.plot_widget.clear()
        self.animation_timer.timeout.connect(self.animate_labeled_data)
        self.animation_timer.start(self.animation_delay)
        self._show_status_message("Анимация запущена")

    def stop_animation(self):
        """Останавливает анимацию."""
        if self.animation_timer.isActive():
            self.animation_timer.stop()
            self._show_status_message("Анимация остановлена")
        self.current_frame = 0
        if self.selected_row_number is not None:
            self.plot_selected_row()

    def animate_labeled_data(self):
        """Отрисовывает кадр анимации."""
        total_positive = len(self.selected_row_data.input_intervals_positive)
        total_negative = len(self.selected_row_data.input_intervals_negative)
        total = total_positive + total_negative
        if self.current_frame >= total:
            self.stop_animation()
            return
        if self.current_frame < total_positive:
            interval = self.selected_row_data.input_intervals_positive[self.current_frame]
            line_index = self.selected_row_data.output_intervals_positive[self.current_frame]
            self.plotter.plot_widget.plot_positive_interval(interval, line_index)
            self._show_status_message(f"Позитивный интервал #{self.current_frame + 1}")
        else:
            interval = self.selected_row_data.input_intervals_negative[self.current_frame - total_positive]
            line_index = self.selected_row_data.output_intervals_negative[self.current_frame - total_positive]
            self.plotter.plot_widget.plot_negative(interval, line_index)
            self._show_status_message(f"Негативный интервал #{self.current_frame + 1 - total_positive}")
        self.current_frame += 1

    def save_state(self):
        """Сохраняет состояние."""
        state = {
            "window_width": self.window_width,
            "animation_delay": self.animation_delay,
            "selected_row": self.selected_row_number,
            "table": [
                {col: self.data_files.at[row, col] for col in self.data_files.columns}
                for row in range(len(self.data_files))
            ]
        }
        with open(PATH_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f)
        log.info("Состояние сохранено")

    def load_state(self):
        """Загружает состояние."""
        if not os.path.exists(PATH_STATE_FILE):
            self.reset_table()
            return
        with open(PATH_STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)
        self.window_width = state.get("window_width", self.window_width)
        self.animation_delay = state.get("animation_delay", self.animation_delay)
        self.width_input.setText(str(self.window_width))
        self.delay_input.setText(str(self.animation_delay))
        self.tableWidget.setRowCount(0)
        self.data_files = pd.DataFrame(columns=["with_substance", "without_substance", "result", "labeled"])
        for row_data in state.get("table", []):
            row = self.tableWidget.rowCount()
            self.tableWidget.insertRow(row)
            self.data_files.loc[row] = [None, None, None, None]
            self.setup_row(row)
            row_dir = self.ensure_row_dir(row)
            for col, key in [(1, "with_substance"), (2, "without_substance"), (3, "result")]:
                if row_data.get(key) and os.path.exists(os.path.join(row_dir, row_data[key])):
                    self.data_files.at[row, key] = row_data[key]
                    self._update_table_cell(row, col, row_data[key])
            # Проверяем поле labeled
            labeled_file = row_data.get("labeled")
            if labeled_file and os.path.exists(os.path.join(row_dir, labeled_file)):
                self.data_files.at[row, "labeled"] = labeled_file
                self._update_table_cell(row, 4, "Размечено")
            else:
                self.data_files.at[row, "labeled"] = None
                self._update_table_cell(row, 4, "")
        selected_row = state.get("selected_row", 0)
        if selected_row is not None and selected_row < self.tableWidget.rowCount():
            self.selected_row_number = selected_row
            self.tableWidget.selectRow(selected_row)
            self.plot_selected_row()
        else:
            self.tableWidget.selectRow(0)
            self.plot_selected_row()
        log.info(f"Загружено строк: {self.tableWidget.rowCount()}")

    def _show_status_message(self, message: str):
        """Отображает сообщение в статус-баре."""
        self.statusbar.showMessage(message, 5000)
