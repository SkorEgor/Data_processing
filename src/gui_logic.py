# gui_logic.py
from PySide6.QtWidgets import QMainWindow, QPushButton, QFileDialog, QTableWidgetItem, QVBoxLayout, QLineEdit, QLabel, \
    QHeaderView
from PySide6.QtCore import Qt, QTimer
from gui import Ui_MainWindow
import pyqtgraph as pg
from collections import namedtuple
import pandas as pd
import os

DataRow = namedtuple('DataRow', ['with_substance', 'without_substance', 'result', 'labeled'])


class GuiProgram(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.data_rows = []
        self.window_width = 10
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.next_animation_frame)
        self.current_animation_row = None
        self.current_frame = 0
        self.init_ui()

    def init_ui(self):
        self.tableWidget.setColumnCount(5)
        self.tableWidget.setHorizontalHeaderLabels([
            "Удалить", "С веществом", "Без вещества", "Результат", "Размеченные данные"
        ])
        self.tableWidget.setRowCount(1)
        self.data_rows.append(DataRow(None, None, None, None))
        self.setup_row(0)

        self.tableWidget.itemSelectionChanged.connect(self.plot_selected_row)
        self.tableWidget.cellClicked.connect(self.handle_cell_click)

        self.plot_widget = pg.PlotWidget()
        self.verticalLayout_2.addWidget(self.plot_widget)

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

        self.control_layout.addStretch()

        for i in range(4):
            self.tableWidget.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)
        self.setWindowTitle("Data Analysis Application")

    def setup_row(self, row):
        delete_btn = QPushButton("Удалить")
        delete_btn.clicked.connect(lambda: self.delete_row(row))
        self.tableWidget.setCellWidget(row, 0, delete_btn)

        for col in range(1, 4):
            load_btn = QPushButton("Загрузить")
            load_btn.clicked.connect(lambda ch, r=row, c=col: self.load_file(r, c))
            self.tableWidget.setCellWidget(row, col, load_btn)

        self.tableWidget.setItem(row, 4, QTableWidgetItem(""))

    def parser_all_data(self, string_list):
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

    def parser_result_data(self, string_list):
        data = []
        for line in string_list:
            if "\t" in line and not line.startswith(("FREQ", "*")):
                freq, gam, src = line.strip().split("\t")
                data.append((float(freq), float(gam), src.lower() == "true"))
        if not data:
            return None
        freq, gamma, src_nn = zip(*data)
        return freq, gamma, src_nn

    def load_file(self, row, column):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл", "", "Text Files (*.txt);;CSV Files (*.csv);;All Files (*)"
        )
        if file_name:
            try:
                with open(file_name, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                current_data = self.data_rows[row]
                if column == 1:
                    freq, gamma = self.parser_all_data(lines)
                    new_data = DataRow((freq, gamma), current_data.without_substance,
                                       current_data.result, current_data.labeled)
                elif column == 2:
                    freq, gamma = self.parser_all_data(lines)
                    new_data = DataRow(current_data.with_substance, (freq, gamma),
                                       current_data.result, current_data.labeled)
                elif column == 3:
                    result = self.parser_result_data(lines)
                    if result:
                        new_data = DataRow(current_data.with_substance, current_data.without_substance,
                                           result, current_data.labeled)
                    else:
                        raise ValueError("Нет данных в файле результата")
                self.data_rows[row] = new_data

                file_item = QTableWidgetItem(file_name.split('/')[-1])
                file_item.setFlags(file_item.flags() & ~Qt.ItemIsEditable)
                self.tableWidget.setItem(row, column, file_item)
                self.tableWidget.removeCellWidget(row, column)

                if row == self.tableWidget.rowCount() - 1:
                    self.add_row()
            except Exception as e:
                self.statusbar.showMessage(f"Ошибка загрузки файла: {str(e)}", 5000)

    def add_row(self):
        row_count = self.tableWidget.rowCount()
        self.tableWidget.insertRow(row_count)
        self.data_rows.append(DataRow(None, None, None, None))
        self.setup_row(row_count)

    def delete_row(self, row):
        if self.tableWidget.rowCount() > 1:
            self.tableWidget.removeRow(row)
            del self.data_rows[row]
            self.plot_selected_row()

    def plot_selected_row(self):
        # Останавливаем анимацию без обратного вызова plot_selected_row
        self.animation_timer.stop()
        self.current_animation_row = None

        self.plot_widget.clear()
        selected = self.tableWidget.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        data = self.data_rows[row]

        self.plot_widget.setLabel('left', 'Gamma')
        self.plot_widget.setLabel('bottom', 'Frequency')
        self.plot_widget.addLegend()

        if data.with_substance:
            freq, gamma = data.with_substance
            self.plot_widget.plot(freq, gamma, pen='r', name='С веществом')
        if data.without_substance:
            freq, gamma = data.without_substance
            self.plot_widget.plot(freq, gamma, pen='b', name='Без вещества')
        if data.result:
            freq, gamma, _ = data.result
            self.plot_widget.plot(freq, gamma, pen=None, symbol='o', symbolPen='g',
                                  symbolBrush='g', name='Точки поглощения')

    def update_window_width(self, text):
        try:
            self.window_width = int(text)
        except ValueError:
            self.statusbar.showMessage("Ширина окна должна быть целым числом", 5000)

    def mark_data(self):
        selected = self.tableWidget.selectedItems()
        if not selected:
            self.statusbar.showMessage("Выберите строку для разметки", 5000)
            return
        row = selected[0].row()
        data = self.data_rows[row]
        if not data.with_substance or not data.result:
            self.statusbar.showMessage("Для разметки нужны данные с веществом и результат", 5000)
            return

        freq_with, gamma_with = data.with_substance
        result_freq, _, _ = data.result

        labeled_data = []
        half_window = self.window_width // 2

        for point_freq in result_freq:
            idx = min(range(len(freq_with)), key=lambda i: abs(freq_with[i] - point_freq))
            start = max(0, idx - half_window)
            end = min(len(freq_with), idx + half_window + 1)
            if start == 0:
                prefix = [freq_with[0]] * (half_window - idx)
                freq_segment = prefix + freq_with[:end]
                gamma_segment = [gamma_with[0]] * (half_window - idx) + gamma_with[:end]
            elif end == len(freq_with):
                suffix = [freq_with[-1]] * (half_window - (len(freq_with) - idx - 1))
                freq_segment = freq_with[start:] + suffix
                gamma_segment = gamma_with[start:] + [gamma_with[-1]] * (half_window - (len(freq_with) - idx - 1))
            else:
                freq_segment = freq_with[start:end]
                gamma_segment = gamma_with[start:end]
            labeled_data.append((freq_segment, gamma_segment, True))

        point_indices = [min(range(len(freq_with)), key=lambda i: abs(freq_with[i] - f))
                         for f in result_freq]
        used_indices = set()
        for idx in point_indices:
            used_indices.update(range(max(0, idx - half_window),
                                      min(len(freq_with), idx + half_window + 1)))

        unmarked_count = len(labeled_data)
        i = 0
        while len(labeled_data) < unmarked_count * 2 and i < len(freq_with):
            if i not in used_indices:
                start = max(0, i - half_window)
                end = min(len(freq_with), i + half_window + 1)
                if not any(start <= idx < end for idx in used_indices):
                    if start == 0:
                        prefix = [freq_with[0]] * (half_window - i)
                        freq_segment = prefix + freq_with[:end]
                        gamma_segment = [gamma_with[0]] * (half_window - i) + gamma_with[:end]
                    elif end == len(freq_with):
                        suffix = [freq_with[-1]] * (half_window - (len(freq_with) - i - 1))
                        freq_segment = freq_with[start:] + suffix
                        gamma_segment = gamma_with[start:] + [gamma_with[-1]] * (half_window - (len(freq_with) - i - 1))
                    else:
                        freq_segment = freq_with[start:end]
                        gamma_segment = gamma_with[start:end]
                    labeled_data.append((freq_segment, gamma_segment, False))
                    used_indices.update(range(start, end))
            i += 1

        df = pd.DataFrame({
            'frequency': [f for freq_segment, _, _ in labeled_data for f in freq_segment],
            'gamma': [g for _, gamma_segment, _ in labeled_data for g in gamma_segment],
            'label': [l for _, _, l in labeled_data for _ in range(len(labeled_data[0][0]))]
        })

        output_file = f"labeled_data_row_{row}.csv"
        df.to_csv(output_file, index=False)

        self.data_rows[row] = DataRow(data.with_substance, data.without_substance,
                                      data.result, labeled_data)  # Храним список кортежей вместо DataFrame
        self.tableWidget.setItem(row, 4, QTableWidgetItem(output_file))

        self.statusbar.showMessage(f"Разметка завершена, сохранено в {output_file}", 5000)

    def handle_cell_click(self, row, column):
        if column == 4 and self.data_rows[row].labeled:
            self.stop_animation()
            self.current_animation_row = row
            self.current_frame = 0
            self.start_animation()

    def start_animation(self):
        self.animation_timer.start(800)  # 0.8 секунды

    def stop_animation(self):
        self.animation_timer.stop()
        self.current_animation_row = None  # Восстанавливаем стандартный график

    def next_animation_frame(self):
        if self.current_animation_row is None:
            return

        data = self.data_rows[self.current_animation_row]
        labeled_data = data.labeled

        if not labeled_data or self.current_frame >= len(labeled_data):
            self.stop_animation()
            return

        self.plot_widget.clear()
        self.plot_widget.setLabel('left', 'Gamma')
        self.plot_widget.setLabel('bottom', 'Frequency')

        freq_segment, gamma_segment, is_positive = labeled_data[self.current_frame]
        pen = 'g' if is_positive else 'y'
        self.plot_widget.plot(freq_segment, gamma_segment, pen=pen,
                              name=f"Интервал {'с точкой' if is_positive else 'без точки'}")

        self.current_frame += 1