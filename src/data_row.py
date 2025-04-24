import os
import numpy as np
import pandas as pd
from scipy.interpolate import interp1d
from logger import log


class DataRow:
    def __init__(
            self,
            with_substance_path: str | None = None,
            without_substance_path: str | None = None,
            result_path: str | None = None,
            input_intervals_positive: np.ndarray | None = None,
            input_intervals_negative: np.ndarray | None = None,
            output_intervals_positive: np.ndarray | None = None,
            output_intervals_negative: np.ndarray | None = None,
    ):
        self.with_substance_path = with_substance_path
        self.without_substance_path = without_substance_path
        self.result_path = result_path
        self.input_intervals_positive = input_intervals_positive
        self.input_intervals_negative = input_intervals_negative
        self.output_intervals_positive = output_intervals_positive
        self.output_intervals_negative = output_intervals_negative

    def get_with_substance(self) -> pd.DataFrame | None:
        return pd.read_csv(self.with_substance_path) if self.with_substance_path and os.path.exists(
            self.with_substance_path) else None

    def get_without_substance(self) -> pd.DataFrame | None:
        return pd.read_csv(self.without_substance_path) if self.without_substance_path and os.path.exists(
            self.without_substance_path) else None

    def get_result(self) -> pd.DataFrame | None:
        return pd.read_csv(self.result_path) if self.result_path and os.path.exists(self.result_path) else None

    def interpolate_data(self, step: float = 0.06):
        """Интерполирует данные с заданным шагом."""
        for path_attr, getter in [
            ('with_substance_path', self.get_with_substance),
            ('without_substance_path', self.get_without_substance)
        ]:
            df = getter()
            if df is not None and not df.empty:
                freq, gamma = interpolate_values(df['frequency'], df['gamma'], step)
                new_df = pd.DataFrame({'frequency': freq, 'gamma': gamma})
                new_path = self._save_interpolated_data(getattr(self, path_attr), new_df)
                setattr(self, path_attr, new_path)

    def _save_interpolated_data(self, original_path: str, df: pd.DataFrame) -> str:
        """Сохраняет интерполированные данные в новый файл."""
        dir_path = os.path.dirname(original_path)
        base_name = os.path.splitext(os.path.basename(original_path))[0]
        new_path = os.path.join(dir_path, f"{base_name}_interpolated.csv")
        df.to_csv(new_path, index=False)
        return new_path

    def mark_data(self, window_width: int) -> bool:
        """Создает размеченные интервалы вокруг точек поглощения и без них."""
        with_substance = self.get_with_substance()
        result = self.get_result()
        if with_substance is None or result is None:
            log.error("Отсутствуют данные with_substance или result")
            return False

        freq_with = with_substance.get('frequency')
        gamma_with = with_substance.get('gamma')
        result_freq = result.get('frequency')
        if freq_with is None or gamma_with is None or result_freq is None or not result_freq.size:
            log.error("Отсутствуют столбцы frequency, gamma или result.frequency пуст")
            return False

        labeled_data = []
        half_window = window_width // 2

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

        if not labeled_data:
            log.error("Не удалось создать интервалы")
            return False

        # Сохраняем размеченные данные как атрибуты
        positive_intervals = [gamma_segment for _, gamma_segment, label in labeled_data if label]
        negative_intervals = [gamma_segment for _, gamma_segment, label in labeled_data if not label]
        self.input_intervals_positive = np.array(positive_intervals, dtype=object) if positive_intervals else None
        self.input_intervals_negative = np.array(negative_intervals, dtype=object) if negative_intervals else None
        self.output_intervals_positive = np.array([np.zeros(len(gamma_segment), dtype=int) for gamma_segment in
                                                   positive_intervals]) if positive_intervals else None
        self.output_intervals_negative = np.array([np.zeros(len(gamma_segment), dtype=int) for gamma_segment in
                                                   negative_intervals]) if negative_intervals else None
        log.info(f"Создано {len(positive_intervals)} позитивных и {len(negative_intervals)} негативных интервалов")
        return True


def interpolate_values(frequency, values, step=0.06):
    frequency = np.asarray(frequency)
    values = np.asarray(values)
    if len(frequency) == 0 or len(values) == 0:
        raise ValueError("Частоты и значения не могут быть пустыми.")
    min_freq, max_freq = frequency.min(), frequency.max()
    new_frequencies = np.arange(min_freq, max_freq + step, step)
    interpolator = interp1d(frequency, values, kind="linear", fill_value="extrapolate")
    return new_frequencies, interpolator(new_frequencies)
