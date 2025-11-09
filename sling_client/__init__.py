"""Sling API Client - Python client for the Sling scheduling API.

This package provides a framework-agnostic Python client for the Sling API,
along with utility functions for field mapping and data transformation.

Basic usage:

    from sling_client import SlingAPIClient

    client = SlingAPIClient(api_key="your_api_key")
    employees = client.fetch_employees()
    departments = client.fetch_departments()
    roles = client.fetch_roles()

For Django integration, see examples/django_integration/
"""

from .client import SlingAPIClient
from .exceptions import (
    SlingAPIError,
    SlingAuthenticationError,
    SlingConnectionError,
    SlingNotFoundError,
    SlingRateLimitError,
    SlingValidationError,
)
from .utils import (
    detect_field_conflicts,
    map_department_from_sling,
    map_employee_from_sling,
    map_employee_to_sling,
    map_role_from_sling,
    parse_sling_date,
)

__version__ = "0.1.0"
__all__ = [
    "SlingAPIClient",
    # Exceptions
    "SlingAPIError",
    "SlingAuthenticationError",
    "SlingConnectionError",
    "SlingNotFoundError",
    "SlingRateLimitError",
    "SlingValidationError",
    # Utilities
    "map_employee_from_sling",
    "map_employee_to_sling",
    "map_department_from_sling",
    "map_role_from_sling",
    "detect_field_conflicts",
    "parse_sling_date",
]
