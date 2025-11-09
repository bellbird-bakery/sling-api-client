"""Custom exceptions for Sling API integration."""


class SlingAPIError(Exception):
    """Base exception for Sling API errors."""

    pass


class SlingAuthenticationError(SlingAPIError):
    """Raised when authentication fails."""

    pass


class SlingRateLimitError(SlingAPIError):
    """Raised when API rate limit is exceeded."""

    pass


class SlingNotFoundError(SlingAPIError):
    """Raised when a resource is not found (404)."""

    pass


class SlingValidationError(SlingAPIError):
    """Raised when API returns validation errors."""

    pass


class SlingConnectionError(SlingAPIError):
    """Raised when connection to Sling API fails."""

    pass
