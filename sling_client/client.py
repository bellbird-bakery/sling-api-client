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

    # Conversation methods
    def fetch_conversations(self) -> List[Dict[str, Any]]:
        """
        Fetch all conversations for the current user.

        Returns:
            List of conversation dictionaries
        """
        logger.info("Fetching conversations from Sling")
        response = self.get("/conversations")
        conversations = response if isinstance(response, list) else response.get("conversations", [])
        logger.info(f"Fetched {len(conversations)} conversations")
        return conversations

    def fetch_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """
        Fetch a single conversation by ID.

        Args:
            conversation_id: Sling conversation ID

        Returns:
            Conversation dictionary with details
        """
        logger.info(f"Fetching conversation {conversation_id} from Sling")
        return self.get(f"/conversations/{conversation_id}")

    def create_conversation(
        self,
        user_ids: List[str],
        message: Optional[str] = None,
        group_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new conversation.

        Args:
            user_ids: List of user IDs to include in conversation
            message: Optional initial message
            group_name: Optional name for group conversations

        Returns:
            Created conversation data
        """
        data = {"users": user_ids}
        if message:
            data["message"] = message
        if group_name:
            data["name"] = group_name

        logger.info(f"Creating conversation with {len(user_ids)} users")
        return self.post("/conversations", data=data)

    def delete_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """
        Archive or delete a conversation.

        Args:
            conversation_id: Sling conversation ID

        Returns:
            Response data
        """
        logger.info(f"Deleting conversation {conversation_id}")
        return self.delete(f"/conversations/{conversation_id}")

    def update_conversation(
        self,
        conversation_id: str,
        conversation_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update group conversation details (e.g., name).

        Args:
            conversation_id: Sling conversation ID
            conversation_data: Updated conversation data

        Returns:
            Updated conversation data
        """
        logger.info(f"Updating conversation {conversation_id}")
        return self.put(f"/conversations/{conversation_id}", data=conversation_data)

    def silence_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """
        Stop notifications from a conversation.

        Args:
            conversation_id: Sling conversation ID

        Returns:
            Response data
        """
        logger.info(f"Silencing conversation {conversation_id}")
        return self.post(f"/conversations/{conversation_id}/silence")

    def unsilence_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """
        Enable notifications for a conversation.

        Args:
            conversation_id: Sling conversation ID

        Returns:
            Response data
        """
        logger.info(f"Unsilencing conversation {conversation_id}")
        return self.delete(f"/conversations/{conversation_id}/silence")

    # Message methods
    def fetch_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
        before: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch messages from a conversation.

        Args:
            conversation_id: Sling conversation ID
            limit: Maximum number of messages to fetch
            before: Fetch messages before this timestamp

        Returns:
            List of message dictionaries
        """
        params = {}
        if limit:
            params["limit"] = limit
        if before:
            params["before"] = before

        logger.info(f"Fetching messages from conversation {conversation_id}")
        response = self.get(f"/conversations/{conversation_id}/messages", params=params)
        messages = response if isinstance(response, list) else response.get("messages", [])
        logger.info(f"Fetched {len(messages)} messages")
        return messages

    def send_message(
        self,
        conversation_id: str,
        text: str,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Send a message to a conversation.

        Args:
            conversation_id: Sling conversation ID
            text: Message text content
            attachments: Optional list of attachment objects

        Returns:
            Created message data
        """
        data = {"text": text}
        if attachments:
            data["attachments"] = attachments

        logger.info(f"Sending message to conversation {conversation_id}")
        return self.post(f"/conversations/{conversation_id}/messages", data=data)

    def update_message(
        self,
        conversation_id: str,
        message_id: str,
        message_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update a message in a conversation.

        Args:
            conversation_id: Sling conversation ID
            message_id: Message ID to update
            message_data: Updated message data

        Returns:
            Updated message data
        """
        logger.info(f"Updating message {message_id} in conversation {conversation_id}")
        return self.put(
            f"/conversations/{conversation_id}/messages/{message_id}",
            data=message_data
        )

    def delete_message(self, conversation_id: str, message_id: str) -> Dict[str, Any]:
        """
        Delete a message from a conversation.

        Args:
            conversation_id: Sling conversation ID
            message_id: Message ID to delete

        Returns:
            Response data
        """
        logger.info(f"Deleting message {message_id} from conversation {conversation_id}")
        return self.delete(f"/conversations/{conversation_id}/messages/{message_id}")

    def send_bulk_message(
        self,
        conversation_id: str,
        recipients: List[str],
        text: str,
    ) -> Dict[str, Any]:
        """
        Send BCC-like message to multiple recipients.

        Args:
            conversation_id: Sling conversation ID
            recipients: List of user IDs
            text: Message text content

        Returns:
            Response data
        """
        data = {"recipients": recipients, "text": text}
        logger.info(f"Sending bulk message to {len(recipients)} recipients")
        return self.post(f"/conversations/{conversation_id}/bulk/messages", data=data)

    def add_message_reaction(
        self,
        conversation_id: str,
        message_id: str,
        emoji: str,
    ) -> Dict[str, Any]:
        """
        Add emoji reaction to a message.

        Args:
            conversation_id: Sling conversation ID
            message_id: Message ID
            emoji: Emoji character or code

        Returns:
            Response data
        """
        data = {"emoji": emoji}
        logger.info(f"Adding reaction to message {message_id}")
        return self.put(
            f"/conversations/{conversation_id}/emojis/{message_id}",
            data=data
        )

    def remove_message_reaction(
        self,
        conversation_id: str,
        message_id: str,
        emoji: str,
    ) -> Dict[str, Any]:
        """
        Remove emoji reaction from a message.

        Args:
            conversation_id: Sling conversation ID
            message_id: Message ID
            emoji: Emoji character or code to remove

        Returns:
            Response data
        """
        data = {"emoji": emoji}
        logger.info(f"Removing reaction from message {message_id}")
        return self.post(
            f"/conversations/{conversation_id}/emojis/{message_id}/delete",
            data=data
        )

    def search_conversations(self, query: str) -> List[Dict[str, Any]]:
        """
        Search conversations for text.

        Args:
            query: Search query string

        Returns:
            List of matching conversations/messages
        """
        data = {"query": query}
        logger.info(f"Searching conversations for: {query}")
        response = self.post("/search", data=data)
        return response if isinstance(response, list) else response.get("results", [])

    # Channel methods (Newsfeed/Announcements)
    def fetch_channels(self, all_channels: bool = False) -> List[Dict[str, Any]]:
        """
        Fetch channels (newsfeed/announcements) for the user.

        Args:
            all_channels: If True, fetch all org channels (admin only)

        Returns:
            List of channel dictionaries
        """
        endpoint = "/channels/all" if all_channels else "/channels"
        logger.info("Fetching channels from Sling")
        response = self.get(endpoint)
        channels = response if isinstance(response, list) else response.get("channels", [])
        logger.info(f"Fetched {len(channels)} channels")
        return channels

    def fetch_channel(self, channel_id: str) -> Dict[str, Any]:
        """
        Fetch a single channel with its articles.

        Args:
            channel_id: Sling channel ID

        Returns:
            Channel dictionary with articles
        """
        logger.info(f"Fetching channel {channel_id} from Sling")
        return self.get(f"/channels/{channel_id}")

    def create_channel(self, channel_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new channel (admin only).

        Args:
            channel_data: Channel data including name, description, etc.

        Returns:
            Created channel data
        """
        logger.info(f"Creating channel: {channel_data.get('name')}")
        return self.post("/channels", data=channel_data)

    def subscribe_to_channel(self, channel_id: str) -> Dict[str, Any]:
        """
        Subscribe current user to a channel.

        Args:
            channel_id: Sling channel ID

        Returns:
            Response data
        """
        logger.info(f"Subscribing to channel {channel_id}")
        return self.post(f"/channels/{channel_id}/subscribers")

    def unsubscribe_from_channel(self, channel_id: str) -> Dict[str, Any]:
        """
        Unsubscribe current user from a channel.

        Args:
            channel_id: Sling channel ID

        Returns:
            Response data
        """
        logger.info(f"Unsubscribing from channel {channel_id}")
        return self.delete(f"/channels/{channel_id}/subscribers")

    def pin_channel(self, channel_id: str) -> Dict[str, Any]:
        """
        Pin a channel for quick access.

        Args:
            channel_id: Sling channel ID

        Returns:
            Response data
        """
        logger.info(f"Pinning channel {channel_id}")
        return self.post(f"/channels/{channel_id}/pin")

    def unpin_channel(self, channel_id: str) -> Dict[str, Any]:
        """
        Unpin a channel.

        Args:
            channel_id: Sling channel ID

        Returns:
            Response data
        """
        logger.info(f"Unpinning channel {channel_id}")
        return self.delete(f"/channels/{channel_id}/pin")

    # Article methods (Posts in channels)
    def fetch_articles(self, channel_id: str) -> List[Dict[str, Any]]:
        """
        Fetch articles from a channel.

        Args:
            channel_id: Sling channel ID

        Returns:
            List of article dictionaries
        """
        logger.info(f"Fetching articles from channel {channel_id}")
        response = self.get(f"/channels/{channel_id}/articles")
        articles = response if isinstance(response, list) else response.get("articles", [])
        logger.info(f"Fetched {len(articles)} articles")
        return articles

    def fetch_article(self, channel_id: str, article_id: str) -> Dict[str, Any]:
        """
        Fetch a single article with details.

        Args:
            channel_id: Sling channel ID
            article_id: Article ID

        Returns:
            Article dictionary
        """
        logger.info(f"Fetching article {article_id} from channel {channel_id}")
        return self.get(f"/channels/{channel_id}/articles/{article_id}")

    def create_article(
        self,
        channel_id: str,
        article_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create a new article (post) in a channel.

        Args:
            channel_id: Sling channel ID
            article_data: Article data (title, body, attachments, etc.)

        Returns:
            Created article data
        """
        logger.info(f"Creating article in channel {channel_id}")
        return self.post(f"/channels/{channel_id}/articles", data=article_data)

    def update_article(
        self,
        channel_id: str,
        article_id: str,
        article_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update an article.

        Args:
            channel_id: Sling channel ID
            article_id: Article ID
            article_data: Updated article data

        Returns:
            Updated article data
        """
        logger.info(f"Updating article {article_id} in channel {channel_id}")
        return self.put(
            f"/channels/{channel_id}/articles/{article_id}",
            data=article_data
        )

    def delete_article(self, channel_id: str, article_id: str) -> Dict[str, Any]:
        """
        Delete an article from a channel.

        Args:
            channel_id: Sling channel ID
            article_id: Article ID

        Returns:
            Response data
        """
        logger.info(f"Deleting article {article_id} from channel {channel_id}")
        return self.delete(f"/channels/{channel_id}/articles/{article_id}")

    def like_article(self, channel_id: str, article_id: str) -> Dict[str, Any]:
        """
        Like an article.

        Args:
            channel_id: Sling channel ID
            article_id: Article ID

        Returns:
            Response data
        """
        logger.info(f"Liking article {article_id}")
        return self.post(f"/channels/{channel_id}/articles/{article_id}/likes")

    def unlike_article(self, channel_id: str, article_id: str) -> Dict[str, Any]:
        """
        Remove like from an article.

        Args:
            channel_id: Sling channel ID
            article_id: Article ID

        Returns:
            Response data
        """
        logger.info(f"Unliking article {article_id}")
        return self.delete(f"/channels/{channel_id}/articles/{article_id}/likes")

    def mark_article_read(self, channel_id: str, article_id: str) -> Dict[str, Any]:
        """
        Mark an article as read.

        Args:
            channel_id: Sling channel ID
            article_id: Article ID

        Returns:
            Response data
        """
        logger.info(f"Marking article {article_id} as read")
        return self.put(f"/channels/{channel_id}/articles/{article_id}/seen")

    # Article comments
    def fetch_article_comments(
        self,
        channel_id: str,
        article_id: str,
    ) -> List[Dict[str, Any]]:
        """
        Fetch comments on an article.

        Args:
            channel_id: Sling channel ID
            article_id: Article ID

        Returns:
            List of comment dictionaries
        """
        logger.info(f"Fetching comments for article {article_id}")
        response = self.get(f"/channels/{channel_id}/articles/{article_id}/comments")
        comments = response if isinstance(response, list) else response.get("comments", [])
        return comments

    def add_article_comment(
        self,
        channel_id: str,
        article_id: str,
        text: str,
    ) -> Dict[str, Any]:
        """
        Add a comment to an article.

        Args:
            channel_id: Sling channel ID
            article_id: Article ID
            text: Comment text

        Returns:
            Created comment data
        """
        data = {"text": text}
        logger.info(f"Adding comment to article {article_id}")
        return self.post(
            f"/channels/{channel_id}/articles/{article_id}/comments",
            data=data
        )

    def update_article_comment(
        self,
        channel_id: str,
        article_id: str,
        comment_id: str,
        text: str,
    ) -> Dict[str, Any]:
        """
        Update an article comment.

        Args:
            channel_id: Sling channel ID
            article_id: Article ID
            comment_id: Comment ID
            text: Updated comment text

        Returns:
            Updated comment data
        """
        data = {"text": text}
        logger.info(f"Updating comment {comment_id} on article {article_id}")
        return self.put(
            f"/channels/{channel_id}/articles/{article_id}/comments/{comment_id}",
            data=data
        )

    def delete_article_comment(
        self,
        channel_id: str,
        article_id: str,
        comment_id: str,
    ) -> Dict[str, Any]:
        """
        Delete an article comment.

        Args:
            channel_id: Sling channel ID
            article_id: Article ID
            comment_id: Comment ID

        Returns:
            Response data
        """
        logger.info(f"Deleting comment {comment_id} from article {article_id}")
        return self.delete(
            f"/channels/{channel_id}/articles/{article_id}/comments/{comment_id}"
        )

    # Shift methods (additional endpoints not in original client)
    def fetch_shifts(
        self,
        start_date: str,
        end_date: str,
        user_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch shifts within a date range.

        Args:
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            user_ids: Optional list of user IDs to filter by

        Returns:
            List of shift dictionaries
        """
        params = {"dates": f"{start_date}/{end_date}"}
        if user_ids:
            params["users"] = ",".join(user_ids)

        logger.info(f"Fetching shifts from {start_date} to {end_date}")
        response = self.get("/shifts", params=params)
        shifts = response if isinstance(response, list) else response.get("shifts", [])
        logger.info(f"Fetched {len(shifts)} shifts")
        return shifts

    def fetch_shift(self, shift_id: str) -> Dict[str, Any]:
        """
        Fetch a single shift by ID.

        Args:
            shift_id: Sling shift/event ID

        Returns:
            Shift dictionary
        """
        logger.info(f"Fetching shift {shift_id} from Sling")
        return self.get(f"/shifts/{shift_id}")

    def create_shift(self, shift_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new shift.

        Args:
            shift_data: Shift data (user, start, end, position, location, etc.)

        Returns:
            Created shift data
        """
        logger.info("Creating shift in Sling")
        return self.post("/shifts", data=shift_data)

    def update_shift(
        self,
        shift_id: str,
        shift_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update an existing shift.

        Args:
            shift_id: Sling shift/event ID
            shift_data: Updated shift data

        Returns:
            Updated shift data
        """
        logger.info(f"Updating shift {shift_id}")
        return self.put(f"/shifts/{shift_id}", data=shift_data)

    def delete_shift(self, shift_id: str) -> Dict[str, Any]:
        """
        Delete a shift.

        Args:
            shift_id: Sling shift/event ID

        Returns:
            Response data
        """
        logger.info(f"Deleting shift {shift_id}")
        return self.post("/shifts/delete", data={"ids": [shift_id]})

    def publish_shift(self, shift_id: str) -> Dict[str, Any]:
        """
        Publish a shift to make it visible to employees.

        Args:
            shift_id: Sling shift/event ID

        Returns:
            Response data
        """
        logger.info(f"Publishing shift {shift_id}")
        return self.post(f"/shifts/{shift_id}/sync")

    def unpublish_shift(self, shift_id: str) -> Dict[str, Any]:
        """
        Unpublish a shift.

        Args:
            shift_id: Sling shift/event ID

        Returns:
            Response data
        """
        logger.info(f"Unpublishing shift {shift_id}")
        return self.post(f"/shifts/{shift_id}/unpublish")

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
