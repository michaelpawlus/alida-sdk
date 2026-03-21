"""Custom exception hierarchy for Alida SDK."""


class AlidaError(Exception):
    """Base exception for all Alida SDK errors."""


class AuthenticationError(AlidaError):
    """Raised when authentication fails (401, invalid credentials)."""


class NotFoundError(AlidaError):
    """Raised when a resource is not found (404)."""


class RateLimitError(AlidaError):
    """Raised when rate-limited (429)."""


class ServerError(AlidaError):
    """Raised on 5xx responses."""


class ConfigurationError(AlidaError):
    """Raised when required configuration is missing."""
