"""Sling API client for employee data synchronization.

This is a framework-agnostic Python client for the Sling API.
It can be used standalone or integrated with Django, Flask, FastAPI, etc.

Example usage:

    from sling_client import SlingAPIClient

    # Option 1: Pass credentials directly
    client = SlingAPIClient(
        api_url="https://api.getsling.com/v1",
        api_key="your_api_key_here",
        timeout=30
    )

    # Option 2: Use environment variables (SLING_API_URL, SLING_API_KEY, SLING_API_TIMEOUT)
    client = SlingAPIClient()

    # Fetch employees
    employees = client.fetch_employees()

    # Fetch departments and roles
    departments = client.fetch_departments()
    roles = client.fetch_roles()
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional

import requests

from .exceptions import (
    SlingAPIError,
    SlingAuthenticationError,
    SlingConnectionError,
    SlingNotFoundError,
    SlingRateLimitError,
    SlingValidationError,
)

logger = logging.getLogger(__name__)


class SlingAPIClient:
    """Client for interacting with the Sling API.

    This client handles authentication, rate limiting, retries, and provides
    convenient methods for common operations.

    Configuration:
        - Pass arguments to __init__
        - Set environment variables: SLING_API_URL, SLING_API_KEY, SLING_API_TIMEOUT
        - Django users: Set in settings.py as SLING_API_URL, SLING_API_KEY, SLING_API_TIMEOUT
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30,
    ):
        """
        Initialize the Sling API client.

        Args:
            api_url: Base URL for Sling API (defaults to env SLING_API_URL or https://api.getsling.com/v1)
            api_key: API authentication token (defaults to env SLING_API_KEY)
            timeout: Request timeout in seconds (defaults to env SLING_API_TIMEOUT or 30)
        """
        # Try Django settings first (if available), then environment variables, then defaults
        self.api_url = api_url or self._get_config(
            "SLING_API_URL", "https://api.getsling.com/v1"
        )
        self.api_key = api_key or self._get_config("SLING_API_KEY", "")
        self.timeout = timeout or int(self._get_config("SLING_API_TIMEOUT", "30"))
        self.session = requests.Session()

        if self.api_key:
            self.session.headers.update({"Authorization": self.api_key})

    def _get_config(self, key: str, default: str = "") -> str:
        """Get configuration from Django settings or environment variables.

        Args:
            key: Configuration key (e.g., 'SLING_API_URL')
            default: Default value if not found

        Returns:
            Configuration value
        """
        # Try Django settings first
        try:
            from django.conf import settings

            return getattr(settings, key, None) or os.environ.get(key, default)
        except ImportError:
            # Django not available, use environment variables
            return os.environ.get(key, default)

    def authenticate(self, email: str, password: str) -> str:
        """
        Authenticate with Sling API using email and password.

        Args:
            email: User email
            password: User password

        Returns:
            Authentication token

        Raises:
            SlingAuthenticationError: If authentication fails
        """
        url = f"{self.api_url}/account/login"
        data = {"email": email, "password": password}

        try:
            response = requests.post(url, json=data, timeout=self.timeout)

            if response.status_code == 401:
                raise SlingAuthenticationError("Invalid email or password")

            response.raise_for_status()

            # Token is returned in Authorization header
            token = response.headers.get("Authorization")
            if not token:
                # Some APIs return it in the response body
                token = response.json().get("token") or response.json().get(
                    "access_token"
                )

            if not token:
                raise SlingAuthenticationError("No token returned from login")

            # Update session with new token
            self.api_key = token
            self.session.headers.update({"Authorization": token})

            logger.info(f"Successfully authenticated user: {email}")
            return token

        except requests.exceptions.RequestException as e:
            logger.error(f"Authentication failed: {e}")
            raise SlingConnectionError(f"Failed to connect to Sling API: {e}") from e

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        retry_count: int = 3,
    ) -> Dict[str, Any]:
        """
        Make an HTTP request to the Sling API with retry logic.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., '/users')
            data: Request body data
            params: URL query parameters
            retry_count: Number of retries on failure

        Returns:
            JSON response data

        Raises:
            SlingAPIError: On API errors
        """
        if not self.api_key:
            raise SlingAuthenticationError(
                "No API key set. Please authenticate first."
            )

        url = f"{self.api_url}{endpoint}"
        attempt = 0

        while attempt < retry_count:
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    timeout=self.timeout,
                )

                # Handle rate limiting with exponential backoff
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(
                        f"Rate limit exceeded. Retrying after {retry_after}s"
                    )

                    if attempt < retry_count - 1:
                        time.sleep(retry_after)
                        attempt += 1
                        continue
                    else:
                        raise SlingRateLimitError("API rate limit exceeded")

                # Handle authentication errors
                if response.status_code == 401:
                    raise SlingAuthenticationError("Invalid or expired token")

                # Handle not found errors
                if response.status_code == 404:
                    raise SlingNotFoundError(f"Resource not found: {endpoint}")

                # Handle validation errors
                if response.status_code == 400:
                    error_msg = response.json().get("message", "Validation error")
                    raise SlingValidationError(error_msg)

                # Raise for other HTTP errors
                response.raise_for_status()

                # Return JSON response if available
                if response.content:
                    return response.json()
                return {}

            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout (attempt {attempt + 1}/{retry_count})")
                if attempt < retry_count - 1:
                    time.sleep(2**attempt)  # Exponential backoff
                    attempt += 1
                    continue
                raise SlingConnectionError("Request timed out after retries")

            except requests.exceptions.RequestException as e:
                logger.error(f"API request failed: {e}")
                if attempt < retry_count - 1:
                    time.sleep(2**attempt)
                    attempt += 1
                    continue
                raise SlingConnectionError(
                    f"Failed to connect to Sling API: {e}"
                ) from e

            except (
                SlingAuthenticationError,
                SlingNotFoundError,
                SlingValidationError,
                SlingRateLimitError,
            ):
                # Don't retry these errors
                raise

    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make a GET request to the Sling API."""
        return self._make_request("GET", endpoint, params=params)

    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make a POST request to the Sling API."""
        return self._make_request("POST", endpoint, data=data)

    def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Make a PUT request to the Sling API."""
        return self._make_request("PUT", endpoint, data=data)

    def delete(self, endpoint: str) -> Dict[str, Any]:
        """Make a DELETE request to the Sling API."""
        return self._make_request("DELETE", endpoint)

    # Employee/User methods
    def fetch_employees(
        self,
        updated_since: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch all employees from Sling.

        Args:
            updated_since: ISO date string to filter by last update
            limit: Maximum number of employees to fetch

        Returns:
            List of employee dictionaries
        """
        params = {}
        if updated_since:
            params["updated_since"] = updated_since
        if limit:
            params["limit"] = limit

        logger.info("Fetching employees from Sling")
        response = self.get("/users", params=params)

        # Response might be a list or a dict with 'users' key
        employees = response if isinstance(response, list) else response.get("users", [])
        logger.info(f"Fetched {len(employees)} employees")
        return employees

    def fetch_employee(self, sling_id: str) -> Dict[str, Any]:
        """
        Fetch a single employee by Sling ID.

        Args:
            sling_id: Sling user ID

        Returns:
            Employee dictionary
        """
        logger.info(f"Fetching employee {sling_id} from Sling")
        return self.get(f"/users/{sling_id}")

    def create_employee(self, employee_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new employee in Sling.

        Args:
            employee_data: Dictionary with employee information

        Returns:
            Created employee data with Sling ID
        """
        logger.info(f"Creating employee in Sling: {employee_data.get('email')}")
        response = self.post("/users", data=employee_data)
        logger.info(f"Created employee with Sling ID: {response.get('id')}")
        return response

    def update_employee(
        self,
        sling_id: str,
        employee_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update an existing employee in Sling.

        Args:
            sling_id: Sling user ID
            employee_data: Dictionary with updated employee information

        Returns:
            Updated employee data
        """
        logger.info(f"Updating employee {sling_id} in Sling")
        response = self.put(f"/users/{sling_id}", data=employee_data)
        logger.info(f"Updated employee {sling_id}")
        return response

    # Groups methods (Sling uses groups for departments, positions, locations)
    def fetch_groups(self, include_archived: bool = False) -> List[Dict[str, Any]]:
        """
        Fetch all groups from Sling.

        Groups include positions, locations, teams, and 'everyone'.

        Args:
            include_archived: Whether to include archived groups

        Returns:
            List of group dictionaries
        """
        logger.info("Fetching groups from Sling")
        response = self.get("/groups")
        groups = response if isinstance(response, list) else response.get("groups", [])

        if not include_archived:
            groups = [g for g in groups if not g.get("archivedAt")]

        logger.info(f"Fetched {len(groups)} groups")
        return groups

    def fetch_group(self, group_id: str) -> Dict[str, Any]:
        """
        Fetch a single group with its members.

        Args:
            group_id: Sling group ID

        Returns:
            Group dictionary with members array
        """
        logger.info(f"Fetching group {group_id} from Sling")
        return self.get(f"/groups/{group_id}")

    # Department methods (using location-type groups)
    def fetch_departments(self) -> List[Dict[str, Any]]:
        """
        Fetch all departments from Sling (location-type groups).

        Returns:
            List of department/location dictionaries
        """
        logger.info("Fetching departments (locations) from Sling")
        groups = self.fetch_groups(include_archived=False)
        departments = [g for g in groups if g.get("type") == "location"]
        logger.info(f"Fetched {len(departments)} departments")
        return departments

    # Role methods (using position-type groups)
    def fetch_roles(self) -> List[Dict[str, Any]]:
        """
        Fetch all roles/positions from Sling (position-type groups).

        Returns:
            List of role/position dictionaries
        """
        logger.info("Fetching roles (positions) from Sling")
        groups = self.fetch_groups(include_archived=False)
        roles = [g for g in groups if g.get("type") == "position"]
        logger.info(f"Fetched {len(roles)} roles")
        return roles

    # Team methods (using group-type groups)
    def fetch_teams(self) -> List[Dict[str, Any]]:
        """
        Fetch all teams from Sling (group-type groups).

        Returns:
            List of team dictionaries
        """
        logger.info("Fetching teams from Sling")
        groups = self.fetch_groups(include_archived=False)
        teams = [g for g in groups if g.get("type") == "group"]
        logger.info(f"Fetched {len(teams)} teams")
        return teams

    def test_connection(self) -> bool:
        """
        Test the connection to Sling API.

        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Try to fetch current user info or a simple endpoint
            self.get("/account")
            logger.info("Sling API connection test successful")
            return True
        except Exception as e:
            logger.error(f"Sling API connection test failed: {e}")
            return False
