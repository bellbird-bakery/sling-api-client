"""Unit tests for SlingAPIClient."""
import pytest
import responses
from sling_client import SlingAPIClient
from sling_client.exceptions import (
    SlingAuthenticationError,
    SlingConnectionError,
    SlingNotFoundError,
    SlingRateLimitError,
    SlingValidationError,
)


@pytest.fixture
def client():
    """Create a test client."""
    return SlingAPIClient(
        api_url="https://api.test.com/v1",
        api_key="test_api_key",
        timeout=10
    )


class TestClientInitialization:
    """Test client initialization."""

    def test_init_with_params(self):
        """Test initialization with parameters."""
        client = SlingAPIClient(
            api_url="https://api.test.com",
            api_key="test_key",
            timeout=20
        )
        assert client.api_url == "https://api.test.com"
        assert client.api_key == "test_key"
        assert client.timeout == 20

    def test_init_with_env_vars(self, monkeypatch):
        """Test initialization with environment variables."""
        monkeypatch.setenv("SLING_API_URL", "https://env.test.com")
        monkeypatch.setenv("SLING_API_KEY", "env_key")
        monkeypatch.setenv("SLING_API_TIMEOUT", "30")

        client = SlingAPIClient()
        assert client.api_url == "https://env.test.com"
        assert client.api_key == "env_key"
        assert client.timeout == 30


class TestEmployeeMethods:
    """Test employee-related methods."""

    @responses.activate
    def test_fetch_employees(self, client):
        """Test fetching employees."""
        responses.add(
            responses.GET,
            "https://api.test.com/v1/users",
            json=[
                {"id": 1, "name": "John", "email": "john@test.com"},
                {"id": 2, "name": "Jane", "email": "jane@test.com"},
            ],
            status=200
        )

        employees = client.fetch_employees()
        assert len(employees) == 2
        assert employees[0]["name"] == "John"
        assert employees[1]["email"] == "jane@test.com"

    @responses.activate
    def test_fetch_employee(self, client):
        """Test fetching single employee."""
        responses.add(
            responses.GET,
            "https://api.test.com/v1/users/123",
            json={"id": 123, "name": "John", "email": "john@test.com"},
            status=200
        )

        employee = client.fetch_employee("123")
        assert employee["id"] == 123
        assert employee["name"] == "John"

    @responses.activate
    def test_create_employee(self, client):
        """Test creating employee."""
        responses.add(
            responses.POST,
            "https://api.test.com/v1/users",
            json={"id": 456, "name": "New", "email": "new@test.com"},
            status=200
        )

        result = client.create_employee({
            "name": "New",
            "email": "new@test.com"
        })
        assert result["id"] == 456

    @responses.activate
    def test_update_employee(self, client):
        """Test updating employee."""
        responses.add(
            responses.PUT,
            "https://api.test.com/v1/users/123",
            json={"id": 123, "name": "Updated"},
            status=200
        )

        result = client.update_employee("123", {"name": "Updated"})
        assert result["name"] == "Updated"


class TestGroupMethods:
    """Test group-related methods."""

    @responses.activate
    def test_fetch_groups(self, client):
        """Test fetching groups."""
        responses.add(
            responses.GET,
            "https://api.test.com/v1/groups",
            json=[
                {"id": 1, "name": "Group 1", "type": "location"},
                {"id": 2, "name": "Group 2", "type": "position"},
            ],
            status=200
        )

        groups = client.fetch_groups()
        assert len(groups) == 2

    @responses.activate
    def test_fetch_departments(self, client):
        """Test fetching departments (location groups)."""
        responses.add(
            responses.GET,
            "https://api.test.com/v1/groups",
            json=[
                {"id": 1, "name": "Dept 1", "type": "location"},
                {"id": 2, "name": "Role 1", "type": "position"},
            ],
            status=200
        )

        departments = client.fetch_departments()
        assert len(departments) == 1
        assert departments[0]["type"] == "location"

    @responses.activate
    def test_fetch_roles(self, client):
        """Test fetching roles (position groups)."""
        responses.add(
            responses.GET,
            "https://api.test.com/v1/groups",
            json=[
                {"id": 1, "name": "Dept 1", "type": "location"},
                {"id": 2, "name": "Role 1", "type": "position"},
            ],
            status=200
        )

        roles = client.fetch_roles()
        assert len(roles) == 1
        assert roles[0]["type"] == "position"


class TestErrorHandling:
    """Test error handling."""

    @responses.activate
    def test_authentication_error(self, client):
        """Test authentication error handling."""
        responses.add(
            responses.GET,
            "https://api.test.com/v1/users",
            json={"error": "Unauthorized"},
            status=401
        )

        with pytest.raises(SlingAuthenticationError):
            client.fetch_employees()

    @responses.activate
    def test_not_found_error(self, client):
        """Test not found error handling."""
        responses.add(
            responses.GET,
            "https://api.test.com/v1/users/999",
            json={"error": "Not found"},
            status=404
        )

        with pytest.raises(SlingNotFoundError):
            client.fetch_employee("999")

    @responses.activate
    def test_validation_error(self, client):
        """Test validation error handling."""
        responses.add(
            responses.POST,
            "https://api.test.com/v1/users",
            json={"message": "Email is required"},
            status=400
        )

        with pytest.raises(SlingValidationError):
            client.create_employee({"name": "Test"})

    @responses.activate
    def test_rate_limit_error(self, client):
        """Test rate limit error handling (no retry)."""
        # Add 3 responses - client will retry 3 times
        for _ in range(3):
            responses.add(
                responses.GET,
                "https://api.test.com/v1/users",
                json={"error": "Rate limit exceeded"},
                status=429,
                headers={"Retry-After": "1"}
            )

        with pytest.raises(SlingRateLimitError):
            client.fetch_employees()

    @responses.activate
    def test_connection_error_with_retry(self, client):
        """Test connection error with retry logic."""
        # First two calls fail, third succeeds
        responses.add(
            responses.GET,
            "https://api.test.com/v1/users",
            body=Exception("Connection failed")
        )
        responses.add(
            responses.GET,
            "https://api.test.com/v1/users",
            body=Exception("Connection failed")
        )
        responses.add(
            responses.GET,
            "https://api.test.com/v1/users",
            json=[{"id": 1, "name": "John"}],
            status=200
        )

        employees = client.fetch_employees()
        assert len(employees) == 1
