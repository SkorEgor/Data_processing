import sys
import logging
import pyqtgraph as pg
from pandas import DataFrame
from numpy.random import randn
from numpy import ndarray, linspace, sin
from PySide6.QtGui import QColor, QPixmap, Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget, QApplication

from src.data import DataRow


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
    absorption_line_text_true = "Точки поглощения (от нейронной сети)"
    absorption_line_color_true = "#36F62D"  # Зеленый
    absorption_line_text_false = "Точки поглощения (проставленные вручную)"
    absorption_line_color_false = "#0000FF"  # Синий
    labeled_positive_text = "Размеченные интервалы (с точкой)"
    labeled_positive_color = "#36F62D"  # Зеленый
    labeled_negative_text = "Размеченные интервалы (без точки)"
    labeled_negative_color = "#FFA500"  # Желтый

    def __init__(self, parent=None):
        pg.setConfigOptions(background="w", foreground="k")
        super().__init__(parent=parent)
        self.showGrid(x=True, y=True)
        self.setLabel("left", self.vertical_axis_name_data)
        self.setLabel("bottom", self.horizontal_axis_name_data)
        self.setTitle(self.title_data)
        self.setMinimumSize(400, 300)
        self.enableAutoRange(x=True, y=True)

    def plot_row(self, data_row: DataRow):
        """Отрисовывает данные из DataRow и возвращает данные для легенды."""
        self.clear()
        legend_data = []
        logging.info(f"Отрисовка данных для строки")

        has_data = any([
            isinstance(data_row.with_substance, DataFrame) and not data_row.with_substance.empty,
            isinstance(data_row.without_substance, DataFrame) and not data_row.without_substance.empty,
            isinstance(data_row.result, DataFrame) and not data_row.result.empty,
            data_row.intervals_positive is not None,
            data_row.intervals_negative is not None
        ])
        # Нет данных
        if not has_data:
            logging.info("Нет данных для отрисовки")
            return legend_data
        # Отрисовка данных без вещества
        if (
                isinstance(data_row.without_substance, DataFrame)
                and not data_row.without_substance.empty
                and not data_row.without_substance[["frequency", "gamma"]].dropna().empty
        ):
            self.plot(
                data_row.without_substance["frequency"],
                data_row.without_substance["gamma"],
                pen=pg.mkPen(color=self.color_without_gas, width=2),
                name=self.name_without_gas,
            )
            legend_data.append((self.color_without_gas, self.name_without_gas))
        # Отрисовка данных с веществом
        if (
                isinstance(data_row.with_substance, DataFrame)
                and not data_row.with_substance.empty
                and not data_row.with_substance[["frequency", "gamma"]].dropna().empty
        ):
            self.plot(
                data_row.with_substance["frequency"],
                data_row.with_substance["gamma"],
                pen=pg.mkPen(color=self.color_with_gas, width=2),
                name=self.name_with_gas,
            )
            legend_data.append((self.color_with_gas, self.name_with_gas))

        if (
                isinstance(data_row.result, DataFrame)
                and not data_row.result.empty
                and not data_row.result[["frequency", "gamma"]].dropna().empty
        ):
            if "src" in data_row.result.columns:
                df_true = data_row.result[data_row.result["src"] == True]
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

                df_false = data_row.result[data_row.result["src"] == False]
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
                    logging.info(f"Отрисованы точки: {len(df_false)} точек")
            else:
                logging.warning(f"Колонка 'src' отсутствует в data_row.result")
                scatter = pg.ScatterPlotItem(
                    x=data_row.result["frequency"],
                    y=data_row.result["gamma"],
                    symbol="o",
                    pen=pg.mkPen("k"),
                    brush=self.absorption_line_color_true,
                    size=8,
                )
                self.addItem(scatter)
                legend_data.append((self.absorption_line_color_true, self.absorption_line_text_true))
                logging.info(f"Отрисованы точки поглощения")

        return legend_data

    def plot_positive_interval(self, gamma_segment: ndarray):
        """Отрисовывает положительный интервал (с линией поглощения)."""
        self.clear()
        legend_data = []
        logging.info(f"Отрисовка линии поглощения")

        self.plot(
            y=gamma_segment,
            pen=pg.mkPen(color=self.labeled_positive_color, width=2),
            name=self.labeled_positive_text,
        )
        legend_data.append((self.labeled_positive_color, self.labeled_positive_text))
        self.enableAutoRange(x=True, y=True)
        logging.info(f"Успешно отрисована линия поглощения")

    def plot_negative(self, gamma_segment: ndarray):
        """Отрисовывает отрицательный интервал (без линии поглощения)."""
        self.clear()
        legend_data = []
        logging.info(f"Отрисовка без линии поглощения")

        self.plot(
            y=gamma_segment,
            pen=pg.mkPen(color=self.labeled_negative_color, width=2),
            name=self.labeled_negative_text,
        )
        legend_data.append((self.labeled_negative_color, self.labeled_negative_text))
        self.enableAutoRange(x=True, y=True)
        logging.info(f"Успешно отрисован интервал без поглощения")


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

        self.setLayout(layout)

    def plot_data(self, data_row: DataRow) -> None:
        """Отрисовывает данные и обновляет легенду."""
        # Очищаем легенду перед новой отрисовкой
        self.legend_widget.update_legend([])
        # Отрисовываем данные
        legend_data = self.plot_widget.plot_row(data_row)
        # Обновляем легенду
        self.legend_widget.update_legend(legend_data)


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
    # Пример данных для intervals_positive
    positive_intervals = sin(freq / 10) + 0.2 * randn(100)

    data_row = DataRow(
        with_substance=DataFrame({"frequency": freq, "gamma": gamma_with}),
        without_substance=DataFrame({"frequency": freq, "gamma": gamma_without}),
        result=result_data,
        intervals_positive=positive_intervals,
        intervals_negative=None
    )

    # Окно с отрисовкой данных
    app = QApplication(sys.argv)

    # Первый график для основных данных
    plotter1 = Plotter()
    plotter1.plot_data(data_row)
    plotter1.setWindowTitle("Данные с веществом и без вещества")
    plotter1.show()

    # Второй график для intervals_positive
    plotter2 = Plotter()
    plotter2.plot_widget.plot_positive_interval(data_row.intervals_positive)
    plotter2.legend_widget.update_legend(
        [(plotter2.plot_widget.labeled_positive_color, plotter2.plot_widget.labeled_positive_text)])
    plotter2.setWindowTitle("Размеченные интервалы (с точкой)")
    plotter2.show()

    sys.exit(app.exec())