# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **framework-agnostic Python client library** for the Sling scheduling and workforce management API. The package can be used standalone or integrated with Django, Flask, FastAPI, or any other Python web framework.

**Key Design Principles:**
- Zero dependencies on web frameworks (only requires `requests`)
- Configuration via environment variables, Django settings, or direct parameters
- Automatic retries with exponential backoff
- Built-in rate limit handling (429 responses)
- Comprehensive exception hierarchy for different error types

## Development Commands

### Testing
```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=sling_client tests/

# Run specific test file
pytest tests/test_client.py
pytest tests/test_utils.py
```

### Code Quality
```bash
# Format code
black sling_client/ tests/ examples/

# Lint code
ruff check sling_client/ tests/ examples/

# Type checking (if mypy configured)
mypy sling_client/
```

### Package Installation
```bash
# Install in development mode
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"

# Install with Django support
pip install -e ".[django]"
```

## Architecture

### Core Modules

**`sling_client/client.py` - Main API Client**
- `SlingAPIClient`: Core client class with HTTP request handling
- Configuration resolution order: Constructor args → Django settings → Environment variables
- `_make_request()`: Centralized request handler with retry logic and error handling
- HTTP methods: `get()`, `post()`, `put()`, `delete()`
- High-level API methods grouped by resource type (employees, departments, roles, groups, teams)

**`sling_client/exceptions.py` - Exception Hierarchy**
All exceptions inherit from `SlingAPIError`:
- `SlingAuthenticationError` - 401 errors, invalid/expired tokens
- `SlingNotFoundError` - 404 errors
- `SlingValidationError` - 400 errors
- `SlingRateLimitError` - 429 errors (rate limiting)
- `SlingConnectionError` - Network/timeout errors

**`sling_client/utils.py` - Data Transformation Utilities**
- `map_employee_from_sling()` - Sling API format → standard format
- `map_employee_to_sling()` - Standard format → Sling API format
- `map_department_from_sling()` - Maps location-type groups
- `map_role_from_sling()` - Maps position-type groups
- `detect_field_conflicts()` - Compares local vs Sling data
- `parse_sling_date()` - ISO date string parser

### Sling API Concepts

**Groups as Multi-Purpose Entities:**
Sling uses a single "groups" endpoint for multiple organizational concepts:
- `type: "location"` → Departments (physical locations)
- `type: "position"` → Roles/Positions (job titles)
- `type: "group"` → Teams (custom groupings)

The client provides convenience methods (`fetch_departments()`, `fetch_roles()`, `fetch_teams()`) that filter the groups endpoint by type.

**Field Naming:**
Sling API uses unconventional field names:
- `name` = first name
- `legalName` = legal first name
- `preferredName` = preferred first name (optional)
- `lastname` = last name (single word, lowercase)

The utils module handles this mapping to/from standard `first_name` and `last_name` conventions.

### Django Integration Pattern

The `examples/django_integration/` directory provides a **reference implementation**, not a reusable Django app. It demonstrates:

**Models (`models.py`):**
- `Department` - Stores Sling location groups
- `Role` - Stores Sling position groups
- `SlingConflict` - Tracks data discrepancies requiring manual resolution
- `SlingIntegratedModelMixin` - Mixin for Employee models (adds `sling_id`, `sling_synced_at`, `sling_sync_status`)

**Conflict Resolution Workflow:**
1. Sync runs → detects differences between local and Sling data
2. `SlingConflict` records created for each field difference
3. HR reviews via Django admin or custom UI
4. Batch actions: "Keep Local", "Use Sling", or "Dismiss"
5. Conflicts marked as resolved after action

**Celery Tasks (`tasks.py`):**
- Automated daily sync at 2 AM
- Email notifications to HR with sync summary
- Configurable sync window (only fetch recently updated employees)

## Messaging & Communication Features

The Sling API includes comprehensive messaging and communication capabilities that were added to the client. These features enable full integration with Sling's team communication tools.

### Conversations & Messages
- **Conversations**: Private 1-on-1 or group conversations between employees
  - `fetch_conversations()` - List all conversations for current user
  - `fetch_conversation(conversation_id)` - Get conversation details
  - `create_conversation(user_ids, message, group_name)` - Start new conversation
  - `send_message(conversation_id, text, attachments)` - Send message
  - `fetch_messages(conversation_id, limit, before)` - Get message history
  - `update_message()` / `delete_message()` - Edit or remove messages
  - `send_bulk_message()` - Send BCC-style message to multiple users
  - `silence_conversation()` / `unsilence_conversation()` - Notification controls

### Message Reactions
- `add_message_reaction(conversation_id, message_id, emoji)` - React with emoji
- `remove_message_reaction()` - Remove emoji reaction
- `search_conversations(query)` - Search all conversations for text

### Channels (Newsfeed/Announcements)
Channels are Sling's broadcast communication feature (like a company newsfeed):
- **Channel Management**:
  - `fetch_channels(all_channels=False)` - List channels (admin can fetch all)
  - `fetch_channel(channel_id)` - Get channel with articles
  - `create_channel(channel_data)` - Create new channel (admin)
  - `subscribe_to_channel()` / `unsubscribe_from_channel()` - Manage subscriptions
  - `pin_channel()` / `unpin_channel()` - Pin for quick access

### Articles (Posts in Channels)
Articles are posts within channels (newsfeed posts or announcements):
- **Article Operations**:
  - `fetch_articles(channel_id)` - Get all posts in channel
  - `fetch_article(channel_id, article_id)` - Get article details
  - `create_article(channel_id, article_data)` - Create post
  - `update_article()` / `delete_article()` - Edit or remove posts
  - `like_article()` / `unlike_article()` - Like/unlike posts
  - `mark_article_read()` - Mark as seen

- **Comments on Articles**:
  - `fetch_article_comments(channel_id, article_id)` - Get all comments
  - `add_article_comment(channel_id, article_id, text)` - Comment on post
  - `update_article_comment()` / `delete_article_comment()` - Edit/remove comments

### Use Cases
- **Team Announcements**: Create channels for company-wide or department announcements
- **Direct Messaging**: Enable employees to communicate privately or in groups
- **Interactive Posts**: Allow likes and comments on announcements for engagement
- **Shift Communication**: Send messages about shift changes or coverage needs
- **Document Sharing**: Attach files, photos, and videos to messages and articles

### Important Notes
- **Permissions**: Many messaging operations respect user roles (admin vs employee)
- **Bulk Operations**: Use `send_bulk_message()` for mass communications
- **Search**: The `search_conversations()` endpoint searches across all accessible conversations
- **Channel vs Conversation**: Channels are broadcast/announcement systems; conversations are chat

## Known API Limitations

### Creating Users
The Sling API frequently returns "400 - Temporarily unavailable" when creating users via API. This appears to be a Sling-side limitation. **Workaround**: Create users in Sling web interface first, then sync via API.

### Limited Personal Data
Sling API does not provide:
- Hire date
- Home address
- Phone number (in some cases)
- Manager/reporting relationships
- **Pay rates or salary information** - Confirmed via OpenAPI spec analysis. No compensation endpoints exist for privacy/security reasons.

These fields must be managed separately in your system.

### Rate Limiting
Sling enforces rate limits (returns 429 responses). The client handles this automatically with exponential backoff, but be aware when doing bulk operations.

## Testing Strategy

Tests use the `responses` library to mock HTTP requests. When adding new API methods:

1. Add corresponding test in `tests/test_client.py`
2. Mock the expected Sling API response format
3. Test both success and error cases
4. Test retry logic for transient failures

Example test structure:
```python
@responses.activate
def test_fetch_employees_success():
    responses.add(
        responses.GET,
        "https://api.getsling.com/v1/users",
        json=[{"id": 123, "name": "John", "lastname": "Doe"}],
        status=200
    )
    client = SlingAPIClient(api_key="test-key")
    employees = client.fetch_employees()
    assert len(employees) == 1
```

## Configuration Management

The client supports three configuration sources (in priority order):

1. **Constructor arguments** - Explicit values passed to `SlingAPIClient()`
2. **Django settings** - `SLING_API_URL`, `SLING_API_KEY`, `SLING_API_TIMEOUT` in `settings.py`
3. **Environment variables** - Same names as Django settings

This allows flexibility across different deployment scenarios (standalone scripts, Django projects, etc.).

## Error Handling Best Practices

Always catch specific exceptions rather than the base `SlingAPIError`:

```python
try:
    employees = client.fetch_employees()
except SlingAuthenticationError:
    # Handle invalid API key
except SlingRateLimitError:
    # Handle rate limiting (maybe retry later)
except SlingConnectionError:
    # Handle network issues
except SlingAPIError as e:
    # Catch-all for other API errors
```

Don't retry `SlingAuthenticationError`, `SlingNotFoundError`, or `SlingValidationError` - these indicate problems that won't be resolved by retrying.

## Adding New API Endpoints

When adding support for a new Sling API endpoint:

1. Add method to `SlingAPIClient` class in `client.py`
2. Use `self.get()`, `self.post()`, etc. (not `self._make_request()` directly)
3. Add corresponding mapping function in `utils.py` if needed
4. Write tests in `tests/test_client.py`
5. Update docstrings with example API response format
6. Consider whether the endpoint needs a convenience filter (like departments/roles do with groups)

## Version Management

- Version is defined in `pyproject.toml`, `setup.py`, and `sling_client/__init__.py`
- Keep all three in sync when bumping versions
- Follow semantic versioning (MAJOR.MINOR.PATCH)
