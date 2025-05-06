import sys
import logging
from random import randint

import numpy as np
import pyqtgraph as pg
from pandas import DataFrame
from numpy.random import randn
from numpy import ndarray, linspace, sin, where
from PySide6.QtGui import QColor, QPixmap, Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget, QApplication
from pyqtgraph.Qt.QtCore import Signal

from src.row_data import RowData


def clearer_layout(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget:
            widget.deleteLater()
        elif item.layout():
            clearer_layout(item.layout())


class SpectrometerPlotWidget(pg.PlotWidget):
    title_data = "Данные с веществом и без вещества"
    horizontal_axis_name_data = "Частота [МГц]"
    vertical_axis_name_data = "Гамма [усл.ед.]"
    name_without_gas = "Без вещества"
    color_without_gas = "#515151"
    name_with_gas = "С веществом"
    color_with_gas = "#DC7C02"
    absorption_line_center_text = "Центры линий поглощения"
    absorption_line_center_color = "#FF0000"
    absorption_line_text_true = "Точки поглощения (от нейронной сети)"
    absorption_line_color_true = "#36F62D"  # Зеленый
    absorption_line_text_false = "Точки поглощения (проставленные вручную)"
    absorption_line_color_false = "#0000FF"  # Синий
    labeled_positive_text = "Размеченные интервалы (с точкой)"
    labeled_positive_color = "#36F62D"  # Зеленый
    labeled_negative_text = "Размеченные интервалы (без точки)"
    labeled_negative_color = "#FFA500"  # Желтый
    # Объявляем сигнал обновления легенды (для кастомной легенды)
    dataUpdated = Signal(list)

    def __init__(self, parent=None):
        pg.setConfigOptions(background="w", foreground="k")
        super().__init__(parent=parent)
        self.showGrid(x=True, y=True)
        self.setLabel("left", self.vertical_axis_name_data)
        self.setLabel("bottom", self.horizontal_axis_name_data)
        self.setTitle(self.title_data)
        self.setMinimumSize(400, 300)
        self.enableAutoRange(x=True, y=True)

    def plot_row(self, data_row: RowData):
        _, _, data_row = data_row
        """Отрисовывает данные из RowData и возвращает данные для легенды."""
        # Очищаем предыдущие данные
        self.clear()
        legend_data = []
        logging.info("Отрисовка данных для строки")

        # Получаем данные через методы
        with_substance = data_row.with_substance
        without_substance = data_row.without_substance
        result = data_row.absorption_lines

        has_data = any([
            isinstance(with_substance, DataFrame) and not with_substance.empty,
            isinstance(without_substance, DataFrame) and not without_substance.empty,
            isinstance(result, DataFrame) and not result.empty
        ])

        # Нет данных
        if not has_data:
            logging.info("Нет данных для отрисовки")
            return legend_data

        # Отрисовка данных без вещества
        if (
                isinstance(without_substance, DataFrame)
                and not without_substance.empty
                and not without_substance[["frequency", "gamma"]].dropna().empty
        ):
            self.plot(
                without_substance["frequency"],
                without_substance["gamma"],
                pen=pg.mkPen(color=self.color_without_gas, width=2),
                name=self.name_without_gas,
            )
            legend_data.append((self.color_without_gas, self.name_without_gas))

        # Отрисовка данных с веществом
        if (
                isinstance(with_substance, DataFrame)
                and not with_substance.empty
                and not with_substance[["frequency", "gamma"]].dropna().empty
        ):
            self.plot(
                with_substance["frequency"],
                with_substance["gamma"],
                pen=pg.mkPen(color=self.color_with_gas, width=2),
                name=self.name_with_gas,
            )
            legend_data.append((self.color_with_gas, self.name_with_gas))

        # Отрисовка результатов
        if (
                isinstance(result, DataFrame)
                and not result.empty
                and not result[["frequency", "gamma"]].dropna().empty
        ):
            if "src" in result.columns:
                df_true = result[result["src"] == True]
                if not df_true.empty:
                    scatter_true = pg.ScatterPlotItem(
                        x=df_true["frequency"],
                        y=df_true["gamma"],
                        symbol="o",
                        pen=pg.mkPen("k"),
                        brush=self.absorption_line_color_true,
                        size=8,
                    )
                    self.addItem(scatter_true)
                    legend_data.append((self.absorption_line_color_true, self.absorption_line_text_true))
                    logging.info(f"Отрисованы точки src=True: {len(df_true)} точек")

                df_false = result[result["src"] == False]
                if not df_false.empty:
                    scatter_false = pg.ScatterPlotItem(
                        x=df_false["frequency"],
                        y=df_false["gamma"],
                        symbol="o",
                        pen=pg.mkPen("k"),
                        brush=self.absorption_line_color_false,
                        size=8,
                    )
                    self.addItem(scatter_false)
                    legend_data.append((self.absorption_line_color_false, self.absorption_line_text_false))
                    logging.info(f"Отрисованы точки src=False: {len(df_false)} точек")
            else:
                logging.warning("Колонка 'src' отсутствует в result")
                scatter = pg.ScatterPlotItem(
                    x=result["frequency"],
                    y=result["gamma"],
                    symbol="o",
                    pen=pg.mkPen("k"),
                    brush=self.absorption_line_color_true,
                    size=8,
                )
                self.addItem(scatter)
                legend_data.append((self.absorption_line_color_true, self.absorption_line_text_true))
                logging.info("Отрисованы точки поглощения")

        # Испускаем сигнал с обновленными данными для легенды
        self.dataUpdated.emit(legend_data)
        return legend_data

    def plot_positive_interval(self, gamma_segment: ndarray, line_index: ndarray | None = None):
        """Отрисовывает положительный интервал (с линией поглощения)."""
        # Очищаем предыдущие данные
        self.clear()
        legend_data = []
        logging.info(f"Отрисовка линии поглощения")
        # Отрисовка интервала
        self.plot(
            y=gamma_segment,
            pen=pg.mkPen(color=self.labeled_positive_color, width=2),
            name=self.labeled_positive_text,
        )
        # Отрисовка вертикальных линий - центров линий поглощения
        if line_index is not None:
            for idx in where(line_index == 1)[0]:
                vline = pg.InfiniteLine(
                    pos=idx, angle=90, pen=pg.mkPen(color=self.absorption_line_center_color, width=3)
                )
                self.addItem(vline)
            legend_data.append((self.absorption_line_center_color, self.absorption_line_center_text))
        legend_data.append((self.labeled_positive_color, self.labeled_positive_text))
        self.enableAutoRange(x=True, y=True)
        logging.info(f"Успешно отрисована линия поглощения")
        # Испускаем сигнал с обновленными данными для легенды
        self.dataUpdated.emit(legend_data)

    def plot_negative(self, gamma_segment: np.ndarray, line_index: np.ndarray | None = None):
        """Отрисовывает отрицательный интервал (без линии поглощения)."""
        # Очищаем предыдущие данные
        self.clear()
        legend_data = []
        logging.info(f"Отрисовка без линии поглощения")
        # Отрисовка интервала
        self.plot(
            y=gamma_segment,
            pen=pg.mkPen(color=self.labeled_negative_color, width=2),
            name=self.labeled_negative_text,
        )
        # Отрисовка вертикальных линий - центров линий поглощения
        if line_index is not None:
            for idx in np.where(line_index == 1)[0]:
                vline = pg.InfiniteLine(
                    pos=idx, angle=90, pen=pg.mkPen(color=self.absorption_line_center_color, width=3)
                )
                self.addItem(vline)
            legend_data.append((self.absorption_line_center_color, self.absorption_line_center_text))
        legend_data.append((self.labeled_negative_color, self.labeled_negative_text))
        self.enableAutoRange(x=True, y=True)
        logging.info(f"Успешно отрисован интервал без поглощения")
        # Испускаем сигнал с обновленными данными для легенды
        self.dataUpdated.emit(legend_data)


class LegendWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)

    def update_legend(self, legend_items):
        clearer_layout(self.layout)
        for color, label in legend_items:
            item_layout = QHBoxLayout()
            item_layout.setSpacing(2)
            item_layout.setContentsMargins(0, 0, 0, 0)
            # QPixmap для цвета
            color_label = QLabel()
            pixmap = QPixmap(20, 20)
            pixmap.fill(QColor(color))
            color_label.setPixmap(pixmap)
            color_label.setFixedSize(20, 20)
            item_layout.addWidget(color_label)
            # Текстовая метка, выровненная по левому краю
            text_label = QLabel(label)
            text_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            item_layout.addWidget(text_label)
            # Растяжение, чтобы сохранить общее распределение
            item_layout.addStretch()
            self.layout.addLayout(item_layout)


class Plotter(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.plot_widget = SpectrometerPlotWidget()
        layout.addWidget(self.plot_widget, stretch=1)

        self.legend_widget = LegendWidget()
        layout.addWidget(self.legend_widget, stretch=0)

        # Подключаем сигнал dataUpdated к методу update_legend
        self.plot_widget.dataUpdated.connect(self.legend_widget.update_legend)

        self.setLayout(layout)


# Пример использования
if __name__ == "__main__":
    freq = linspace(100, 200, 100)
    gamma_with = sin(freq / 10) + 0.1 * randn(100)
    gamma_without = sin(freq / 10) + 0.05 * randn(100)
    result_data = DataFrame({
        "frequency": [freq[10], freq[30], freq[50], freq[80]],
        "gamma": [gamma_with[10], gamma_with[30], gamma_with[50], gamma_with[80]],
        "src": [True, False, True, False]
    })
    # Пример данных для input_intervals_positive
    positive_intervals = sin(freq / 10) + 0.2 * randn(100)
    output_intervals_positive = np.array([0] * len(positive_intervals))
    output_intervals_positive[randint(a=0, b=len(positive_intervals))] = 1
    data_row = RowData(
        with_substance=DataFrame({"frequency": freq, "gamma": gamma_with}),
        without_substance=DataFrame({"frequency": freq, "gamma": gamma_without}),
        result=result_data,
        input_intervals_positive=positive_intervals,
        output_intervals_positive=output_intervals_positive
    )
    # Окно с отрисовкой данных
    app = QApplication(sys.argv)
    # - Первый график для основных данных
    plotter1 = Plotter()
    plotter1.plot_widget.plot_row(data_row)
    plotter1.setWindowTitle("Данные с веществом и без вещества")
    plotter1.show()
    # - Второй график для input_intervals_positive
    plotter2 = Plotter()
    plotter2.plot_widget.plot_positive_interval(
        gamma_segment=data_row.input_intervals_positive,
        line_index=data_row.output_intervals_positive
    )
    plotter2.setWindowTitle("Размеченные интервалы (с точкой)")
    plotter2.show()
    # - Запуск окон
    sys.exit(app.exec())
