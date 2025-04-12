class AppException(Exception):
    """Исключение для отображения предупреждающего окна с описанием ошибки"""

    def __init__(self, title: str, message: str):
        self.title = title
        self.message = message
        super().__init__(f"{title}: {message}")

    def __str__(self):
        return f"[{self.title}] {self.message}"
