import pandas as pd
from dataclasses import dataclass


@dataclass
class RowName:
    with_substance: str | None = None
    without_substance: str | None = None
    absorption_lines: str | None = None
    labeled_data: str | None = None


def _data_changed(func):
    def wrapper(self, *args, **kwargs):
        result = func(self, *args, **kwargs)
        if self.data_change_call_function is not None:
            self.data_change_call_function()
        return result

    return wrapper


@dataclass
class RowData:
    with_substance: pd.DataFrame | None = None
    without_substance: pd.DataFrame | None = None
    absorption_lines: pd.DataFrame | None = None
    labeled_data: pd.DataFrame | None = None

    @_data_changed
    def reset_data(self) -> None:
        self.with_substance = None
        self.without_substance = None
        self.absorption_lines = None
        self.labeled_data = None

    def has_with_substance(self) -> bool:
        return self.with_substance is not None and not self.with_substance.empty

    def has_without_substance(self) -> bool:
        return self.without_substance is not None and not self.without_substance.empty

    def has_absorption_lines(self) -> bool:
        return self.absorption_lines is not None and not self.absorption_lines.empty

    def has_labeled_data(self) -> bool:
        return self.labeled_data is not None and not self.labeled_data.empty

    def has_data(self):
        """Есть какие-то данные"""
        return (
                self.has_with_substance()
                or self.has_without_substance()
                or self.has_absorption_lines()
                or self.has_labeled_data()
        )

    @_data_changed
    def set_data(
            self,
            with_substance: pd.DataFrame | None = None,
            without_substance: pd.DataFrame | None = None,
            absorption_lines: pd.DataFrame | None = None,
            labeled_data: pd.DataFrame | None = None
    ):
        self.with_substance = self.with_substance if with_substance is None else with_substance
        self.without_substance = self.without_substance if without_substance is None else without_substance
        self.absorption_lines = self.absorption_lines if absorption_lines is None else absorption_lines
        self.labeled_data = self.labeled_data if labeled_data is None else labeled_data
