from pyqtgraph import PlotWidget, ScatterPlotItem, mkPen, setConfigOptions
from PySide6.QtCore import Signal, QTimer
from PySide6.QtWidgets import QWidget, QVBoxLayout
from collections import namedtuple

DataRow = namedtuple('DataRow', ['with_substance', 'without_substance', 'result', 'labeled'])

class DataPlotWidget(PlotWidget):
    """Виджет для отрисовки данных и анимации."""
    dataUpdated = Signal()

    def __init__(self, parent=None):
        setConfigOptions(background='w', foreground='k')
        super().__init__(parent)
        self.showGrid(x=True, y=True)
        self.setLabel('left', 'Gamma')
        self.setLabel('bottom', 'Frequency')
        self.addLegend()
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.next_animation_frame)
        self.current_animation_row = None
        self.current_frame = 0
        self.data_rows = []

    def plot_row(self, data: DataRow):
        """Отрисовка данных выбранной строки."""
        self.clear()
        self.current_animation_row = None
        self.animation_timer.stop()

        if not data:
            return

        if data.with_substance:
            freq, gamma = data.with_substance
            self.plot(freq, gamma, pen='r', name='С веществом')
        if data.without_substance:
            freq, gamma = data.without_substance
            self.plot(freq, gamma, pen='b', name='Без вещества')
        if data.result:
            freq, gamma, _ = data.result
            self.plot(freq, gamma, pen=None, symbol='o', symbolPen='g',
                      symbolBrush='g', name='Точки поглощения')
        self.dataUpdated.emit()

    def start_animation(self, row: int, data_rows: list):
        """Запуск анимации для размеченных данных строки."""
        self.data_rows = data_rows
        self.current_animation_row = row
        self.current_frame = 0
        self.animation_timer.start(800)

    def stop_animation(self):
        """Остановка анимации."""
        self.animation_timer.stop()
        self.current_animation_row = None

    def next_animation_frame(self):
        """Отрисовка следующего кадра анимации."""
        if self.current_animation_row is None:
            return
        data = self.data_rows[self.current_animation_row]
        labeled_data = data.labeled
        if not labeled_data or self.current_frame >= len(labeled_data):
            self.stop_animation()
            return

        self.clear()
        self.setLabel('left', 'Gamma')
        self.setLabel('bottom', 'Frequency')

        freq_segment, gamma_segment, is_positive = labeled_data[self.current_frame]
        pen = 'g' if is_positive else 'y'
        self.plot(freq_segment, gamma_segment, pen=pen,
                  name=f"Интервал {'с точкой' if is_positive else 'без точки'}")

        self.current_frame += 1
        self.dataUpdated.emit()