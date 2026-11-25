class ApiError(Exception):
    """Erro de API com status HTTP e código estável `{code, message}`."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status, self.code, self.message = status, code, message
