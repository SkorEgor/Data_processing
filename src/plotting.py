import pyqtgraph as pg
import pandas as pd
import logging
from PySide6.QtCore import QTimer, Qt
import os


class Plotter:
    def __init__(self, parent_widget, parent):
        """Инициализирует объект для построения графиков и анимации."""
        self.parent = parent
        self.plot_widget: pg.PlotWidget = pg.PlotWidget()
        parent_widget.layout().addWidget(self.plot_widget)
        self.animation_timer: QTimer = QTimer()
        self.current_animation_row: int = None
        self.current_frame: int = 0
        self.animation_timer.timeout.connect(self.animate_labeled_data)

    def plot_row_data(self):
        """Строит график данных из выбранной строки таблицы."""
        self.stop_animation()
        self.plot_widget.clear()
        selected = self.parent.tableWidget.selectedItems()
        if not selected:
            return
        row = selected[0].row()
        data = self.parent.data_rows[row]

        self.plot_widget.setLabel('left', 'Gamma')
        self.plot_widget.setLabel('bottom', 'Frequency')
        self.plot_widget.addLegend()

        self.parent.statusbar.showMessage("Чтение данных...", 5000)

        try:
            if data.with_substance_file and os.path.exists(data.with_substance_file):
                try:
                    df = pd.read_csv(data.with_substance_file)
                    self.plot_widget.plot(df['frequency'], df['gamma'], pen='r', name='С веществом')
                except Exception as e:
                    logging.error(f"Ошибка чтения {data.with_substance_file}: {str(e)}")
                    self.parent.statusbar.showMessage(f"Ошибка чтения данных с веществом: {str(e)}", 5000)
                    self.parent.remove_file(row, 1)

            if data.without_substance_file and os.path.exists(data.without_substance_file):
                try:
                    df = pd.read_csv(data.without_substance_file)
                    self.plot_widget.plot(df['frequency'], df['gamma'], pen='b', name='Без вещества')
                except Exception as e:
                    logging.error(f"Ошибка чтения {data.without_substance_file}: {str(e)}")
                    self.parent.statusbar.showMessage(f"Ошибка чтения данных без вещества: {str(e)}", 5000)
                    self.parent.remove_file(row, 2)

            if data.result_file and os.path.exists(data.result_file):
                try:
                    df = pd.read_csv(data.result_file)
                    self.plot_widget.plot(df['frequency'], df['gamma'], pen=None, symbol='o',
                                          symbolPen='g', symbolBrush='g', name='Точки поглощения')
                except Exception as e:
                    logging.error(f"Ошибка чтения {data.result_file}: {str(e)}")
                    self.parent.statusbar.showMessage(f"Ошибка чтения результата: {str(e)}", 5000)
                    self.parent.remove_file(row, 3)
            self.parent.statusbar.showMessage("График обновлен", 5000)
        except Exception as e:
            logging.error(f"Ошибка построения графика: {str(e)}")
            self.parent.statusbar.showMessage(f"Ошибка построения графика: {str(e)}", 5000)

    def animate_labeled_data(self):
        """Отображает следующий кадр анимации размеченных данных."""
        if self.current_animation_row is None:
            self.stop_animation()
            return
        data = self.parent.data_rows[self.current_animation_row]
        if not data.labeled_file or not os.path.exists(data.labeled_file):
            logging.error(f"Файл размеченных данных не найден: {data.labeled_file}")
            self.parent.statusbar.showMessage("Файл размеченных данных не найден", 5000)
            self.stop_animation()
            return

        try:
            df = pd.read_csv(data.labeled_file)
            window_size = len(df) // (len(df['label'].unique()) * 2)
            segments = [df[i:i + window_size] for i in range(0, len(df), window_size)]
            if not segments or self.current_frame >= len(segments):
                self.stop_animation()
                self.parent.statusbar.showMessage("Анимация завершена", 5000)
                return

            self.plot_widget.clear()
            self.plot_widget.setLabel('left', 'Gamma')
            self.plot_widget.setLabel('bottom', 'Frequency')

            segment = segments[self.current_frame]
            is_positive = segment['label'].iloc[0]
            pen = 'g' if is_positive else 'y'
            self.plot_widget.plot(segment['frequency'], segment['gamma'], pen=pen,
                                  name=f"Интервал {'с точкой' if is_positive else 'без точки'}")

            self.current_frame += 1
            logging.info(f"Отображен кадр анимации {self.current_frame} для строки {self.current_animation_row}")
        except Exception as e:
            logging.error(f"Ошибка анимации данных {data.labeled_file}: {str(e)}")
            self.parent.statusbar.showMessage(f"Ошибка анимации: {str(e)}", 5000)
            self.parent.remove_file(self.current_animation_row, 4)
            self.stop_animation()

    def start_animation(self, row: int):
        """
        Запускает анимацию для указанной строки.

        Parameters
        ----------
        row : int
            Индекс строки таблицы.
        """
        self.current_animation_row = row
        self.current_frame = 0
        self.animation_timer.start(800)
        logging.info(f"Запущена анимация для строки {row}")

    def stop_animation(self):
        """Останавливает анимацию."""
        self.animation_timer.stop()
        self.current_animation_row = None
        logging.info("Анимация остановлена")