"""Microsoft Graph API error hierarchy and exception handling."""


class GraphError(Exception):
    """Base exception for Graph API errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class ThrottlingError(GraphError):
    """Raised when Graph API returns 429 (Too Many Requests)."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        retry_after_seconds: int | None = None,
    ) -> None:
        super().__init__(message, status_code)
        self.retry_after_seconds = retry_after_seconds


class NotFoundError(GraphError):
    """Raised when resource is not found (404)."""

    pass


class AuthError(GraphError):
    """Raised when authentication fails (401, 403)."""

    pass


class GraphValidationError(GraphError):
    """Raised when input validation fails."""

    pass


class ServiceUnavailableError(GraphError):
    """Raised when service is unavailable (5xx errors)."""

    pass
