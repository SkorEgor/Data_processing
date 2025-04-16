from numpy import ndarray
from pandas import DataFrame
import numpy as np
import random


class DataRow:
    def __init__(
            self,
            with_substance: DataFrame | None = None,
            without_substance: DataFrame | None = None,
            result: DataFrame | None = None,
            intervals_positive: ndarray | None = None,
            intervals_negative: ndarray | None = None,
    ):
        self.with_substance: DataFrame | None = with_substance
        self.without_substance: DataFrame | None = without_substance
        self.result: DataFrame | None = result
        self.intervals_positive: ndarray | None = intervals_positive
        self.intervals_negative: ndarray | None = intervals_negative

    def mark_data(self, window_width: int) -> bool:
        """Создает размеченные интервалы на основе with_substance и result."""
        if self.with_substance is None or self.result is None:
            return False

        freq_with = self.with_substance.get('frequency')
        gamma_with = self.with_substance.get('gamma')
        result_freq = self.result.get('frequency')

        if freq_with is None or gamma_with is None or result_freq is None or not result_freq.size:
            return False

        positive_intervals = []
        negative_intervals = []
        used_indices = set()
        half_window = window_width // 2

        # Позитивные интервалы (вокруг точек поглощения)
        for point_freq in result_freq:
            idx = min(range(len(freq_with)), key=lambda i: abs(freq_with[i] - point_freq))
            start = idx - half_window
            end = idx + half_window
            if start < 0 or end > len(freq_with) or (end - start) != window_width:
                continue
            gamma_segment = gamma_with[start:end].tolist()
            positive_intervals.append(gamma_segment)
            used_indices.update(range(start, end))

        # Негативные интервалы (случайные, не пересекающиеся с позитивными)
        n_positive = len(positive_intervals)
        available_indices = [
            i for i in range(half_window, len(freq_with) - half_window)
            if not any(i - half_window <= idx < i + half_window for idx in used_indices)
        ]
        random.shuffle(available_indices)

        for i in available_indices[:n_positive]:
            start = i - half_window
            end = i + half_window
            gamma_segment = gamma_with[start:end].tolist()
            negative_intervals.append(gamma_segment)

        if not positive_intervals or not negative_intervals:
            return False

        self.intervals_positive = np.array(positive_intervals)
        self.intervals_negative = np.array(negative_intervals)
        return True
