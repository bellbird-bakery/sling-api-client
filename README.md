# Sling API Client

A Python client for the [Sling](https://getsling.com) scheduling and workforce management API. This is a framework-agnostic package that can be used standalone or integrated with Django, Flask, FastAPI, or any other Python web framework.

## Features

- ✅ **Framework Agnostic** - Use with Django, Flask, FastAPI, or standalone scripts
- ✅ **Automatic Retries** - Built-in exponential backoff for failed requests
- ✅ **Rate Limiting** - Handles API rate limits (429 responses) gracefully
- ✅ **Comprehensive Error Handling** - Custom exceptions for different error types
- ✅ **Type Hints** - Full typing support for better IDE integration
- ✅ **Logging** - Detailed logging for debugging and monitoring
- ✅ **Field Mapping Utilities** - Helper functions for data transformation
- ✅ **Django Integration Examples** - Complete reference implementation included

## Installation

### From Private Git Repository

```bash
# Install directly from git
pip install git+https://github.com/your-org/sling-api-client.git

# Or add to requirements.txt
git+https://github.com/your-org/sling-api-client.git@v0.1.0
```

### Dependencies

- Python >= 3.8
- requests >= 2.28.0
- Django >= 4.0 (optional, for Django integration)

## Quick Start

### Basic Usage

```python
from sling_client import SlingAPIClient

# Initialize client
client = SlingAPIClient(
    api_url="https://api.getsling.com/v1",
    api_key="your_api_key_here",
    timeout=30
)

# Or use environment variables (SLING_API_URL, SLING_API_KEY, SLING_API_TIMEOUT)
client = SlingAPIClient()

# Fetch all employees
employees = client.fetch_employees()
for emp in employees:
    print(f"{emp['name']} - {emp['email']}")

# Fetch departments and roles
departments = client.fetch_departments()
roles = client.fetch_roles()

# Get a specific employee
employee = client.fetch_employee(sling_id="123456")

# Update an employee
updated = client.update_employee(
    sling_id="123456",
    employee_data={"name": "John", "lastname": "Doe"}
)
```

### Field Mapping Utilities

```python
from sling_client import map_employee_from_sling, detect_field_conflicts

# Map Sling API response to standard format
sling_data = {"id": 123, "name": "John", "lastname": "Doe", "email": "john@example.com"}
mapped = map_employee_from_sling(sling_data)
# Returns: {"sling_id": "123", "first_name": "John", "last_name": "Doe", ...}

# Detect conflicts between local and Sling data
local_data = {"first_name": "Jonathan", "last_name": "Doe", "email": "john@example.com"}
conflicts = detect_field_conflicts(local_data, sling_data)
# Returns: [{"field_name": "first_name", "local_value": "Jonathan", "sling_value": "John"}]
```

## Configuration

### Environment Variables

```bash
export SLING_API_URL="https://api.getsling.com/v1"
export SLING_API_KEY="your_api_key_here"
export SLING_API_TIMEOUT="30"
```

### Django Settings

```python
# settings.py
SLING_API_URL = "https://api.getsling.com/v1"
SLING_API_KEY = env("SLING_API_KEY")  # Use environment variable
SLING_API_TIMEOUT = 30
```

The client will automatically detect Django settings if available, falling back to environment variables.

## Django Integration

Complete Django integration examples are provided in `examples/django_integration/`. This includes:

- **Models** - Department, Role, SlingConflict, and model mixins
- **Admin** - Enhanced admin interface with conflict resolution
- **Celery Tasks** - Automated daily sync with email notifications
- **Management Commands** - CLI tools for manual sync and testing
- **Views & URLs** - Optional web UI for conflict resolution

See [`examples/django_integration/README.md`](examples/django_integration/README.md) for detailed integration guide.

## API Methods

### Employee/User Methods

```python
# Fetch all employees (optionally filtered)
employees = client.fetch_employees(updated_since="2024-01-01", limit=100)

# Get single employee
employee = client.fetch_employee(sling_id="123456")

# Create employee (Note: May be blocked by API)
new_employee = client.create_employee({
    "name": "John",
    "lastname": "Doe",
    "email": "john@example.com",
    "active": True
})

# Update employee
updated = client.update_employee(sling_id="123456", employee_data={...})
```

### Department Methods (Location Groups)

```python
# Fetch all departments
departments = client.fetch_departments()

# Departments are Sling "location" type groups
for dept in departments:
    print(f"{dept['name']} - {dept['id']}")
```

### Role Methods (Position Groups)

```python
# Fetch all roles/positions
roles = client.fetch_roles()

# Roles are Sling "position" type groups
for role in roles:
    print(f"{role['name']} - {role['id']}")
```

### Group Methods

```python
# Fetch all groups (locations, positions, teams)
groups = client.fetch_groups(include_archived=False)

# Get specific group with members
group_detail = client.fetch_group(group_id="123456")
members = group_detail.get("members", [])
```

### Team Methods

```python
# Fetch teams (group-type groups)
teams = client.fetch_teams()
```

## Error Handling

The client raises specific exceptions for different error conditions:

```python
from sling_client import (
    SlingAPIError,              # Base exception
    SlingAuthenticationError,   # 401 errors
    SlingNotFoundError,         # 404 errors
    SlingValidationError,       # 400 errors
    SlingRateLimitError,        # 429 errors
    SlingConnectionError,       # Network errors
)

try:
    employees = client.fetch_employees()
except SlingAuthenticationError:
    print("Invalid API key")
except SlingRateLimitError:
    print("Rate limit exceeded, try again later")
except SlingConnectionError as e:
    print(f"Network error: {e}")
except SlingAPIError as e:
    print(f"API error: {e}")
```

## Logging

The client uses Python's standard logging module:

```python
import logging

# Enable debug logging to see all API requests
logging.basicConfig(level=logging.DEBUG)

# Or configure specific logger
logger = logging.getLogger("sling_client")
logger.setLevel(logging.INFO)
```

## Testing

```bash
# Install dev dependencies
pip install pytest responses

# Run tests
pytest tests/

# Run with coverage
pytest --cov=sling_client tests/
```

## Examples

### Sync Employees Script

```python
"""Simple script to sync employees from Sling."""
import logging
from sling_client import SlingAPIClient, map_employee_from_sling

logging.basicConfig(level=logging.INFO)

def sync_employees():
    client = SlingAPIClient()

    # Fetch all employees
    sling_employees = client.fetch_employees()

    for sling_emp in sling_employees:
        # Map to standard format
        mapped = map_employee_from_sling(sling_emp)

        # TODO: Save to your database
        print(f"Employee: {mapped['first_name']} {mapped['last_name']}")
        print(f"  Sling ID: {mapped['sling_id']}")
        print(f"  Email: {mapped['email']}")
        print(f"  Active: {mapped['is_active']}")
        print()

if __name__ == "__main__":
    sync_employees()
```

### Detect Data Conflicts

```python
"""Check for data conflicts between local DB and Sling."""
from sling_client import SlingAPIClient, detect_field_conflicts

client = SlingAPIClient()

# Your local employee data
local_employee = {
    "first_name": "Jonathan",
    "last_name": "Doe",
    "email": "j.doe@company.com"
}

# Fetch from Sling
sling_employee = client.fetch_employee(sling_id="123456")

# Detect conflicts
conflicts = detect_field_conflicts(local_employee, sling_employee)

if conflicts:
    print("Conflicts detected:")
    for conflict in conflicts:
        print(f"  {conflict['field_name']}:")
        print(f"    Local:  {conflict['local_value']}")
        print(f"    Sling:  {conflict['sling_value']}")
else:
    print("No conflicts - data is in sync!")
```

## Known Limitations

- **Creating Users**: Sling API may return "400 - Temporarily unavailable" when creating users via API. This appears to be a limitation on Sling's side. Workaround: Create users in Sling web interface first, then sync.

- **Limited Personal Data**: Sling API does not provide all employee fields (e.g., hire date, address, phone). You'll need to manage these fields separately in your system.

- **No Compensation Data**: Pay rates and salaries are not available via the Sling API for privacy reasons.

## Contributing

This is an internal package for [Your Organization]. For issues or feature requests, contact the platform team.

## License

Proprietary - Internal use only

## Support

- **Documentation**: See `examples/` directory for integration guides
- **Issues**: [GitHub Issues](https://github.com/your-org/sling-api-client/issues)
- **Contact**: platform-team@yourcompany.com

## Version History

### v0.1.0 (2025-01-09)

- Initial release
- Core API client with full Sling API coverage
- Field mapping utilities
- Django integration examples
- Comprehensive documentation
