# Sling API Messaging & Communication Features

## Overview

The Sling API includes comprehensive messaging and communication capabilities that enable full integration with Sling's team communication platform. This document details these features and how to use them with the Python client.

## Research Summary

### API Specification Discovery

Successfully accessed the complete OpenAPI specification at `https://api.getsling.com/v1/spec.json`, which revealed **extensive messaging endpoints** that were previously undocumented in the client.

### Key Findings

1. ✅ **Messaging IS Available** - Full conversation and messaging system with 30+ endpoints
2. ✅ **Channels/Newsfeed IS Available** - Complete channel system for announcements and articles
3. ❌ **Compensation Data NOT Available** - Confirmed no wage/salary endpoints exist (privacy restriction)

## Features Added to Client

### Total Additions
- **34 new messaging methods** added to `SlingAPIClient`
- Client expanded from **22 methods → 56 methods**
- Full support for Sling's communication platform

## Available Features

### 1. Conversations (Direct Messaging)

Conversations are private or group chats between employees.

#### Core Operations
```python
# List all conversations
conversations = client.fetch_conversations()

# Get specific conversation
conversation = client.fetch_conversation(conversation_id="123456")

# Create new conversation (1-on-1 or group)
new_conv = client.create_conversation(
    user_ids=["111", "222", "333"],
    message="Initial message (optional)",
    group_name="Group Name (optional for groups)"
)

# Update conversation (e.g., rename group)
client.update_conversation(
    conversation_id="123456",
    conversation_data={"name": "New Group Name"}
)

# Delete/archive conversation
client.delete_conversation(conversation_id="123456")

# Leave group conversation
client.delete(f"/conversations/{conversation_id}/me")

# Unarchive conversation
client.post(f"/conversations/{conversation_id}/unarchive")
```

#### Notification Management
```python
# Silence notifications
client.silence_conversation(conversation_id="123456")

# Re-enable notifications
client.unsilence_conversation(conversation_id="123456")
```

### 2. Messages

Messages are sent within conversations.

#### Sending Messages
```python
# Send a message
message = client.send_message(
    conversation_id="123456",
    text="Hello team!",
    attachments=[
        {"type": "image", "url": "https://..."},
        {"type": "file", "url": "https://..."}
    ]
)

# Send bulk message (BCC-style to multiple recipients)
client.send_bulk_message(
    conversation_id="123456",
    recipients=["111", "222", "333"],
    text="Broadcast message"
)
```

#### Fetching Messages
```python
# Get message history
messages = client.fetch_messages(
    conversation_id="123456",
    limit=50,  # Optional: max messages to fetch
    before="2024-01-01T00:00:00Z"  # Optional: pagination
)

# Mark messages as read
client.put(
    f"/conversations/{conversation_id}/messages",
    data={"unread": 0}
)
```

#### Managing Messages
```python
# Update a message
client.update_message(
    conversation_id="123456",
    message_id="789",
    message_data={"text": "Updated text"}
)

# Delete a message
client.delete_message(
    conversation_id="123456",
    message_id="789"
)
```

#### Message Reactions (Emojis)
```python
# Add emoji reaction
client.add_message_reaction(
    conversation_id="123456",
    message_id="789",
    emoji="👍"
)

# Remove emoji reaction
client.remove_message_reaction(
    conversation_id="123456",
    message_id="789",
    emoji="👍"
)

# Update reaction (change emoji)
client.put(
    f"/conversations/{conversation_id}/reactions/{message_id}",
    data={"emoji": "❤️"}
)
```

### 3. Search

Search across all conversations and messages.

```python
# Search for text in conversations
results = client.search_conversations(query="schedule")
# Returns: List of matching conversations/messages

# Export conversation history
export_data = client.post(
    f"/conversations/{conversation_id}/export",
    data={
        "start_date": "2024-01-01",
        "end_date": "2024-01-31"
    }
)
```

### 4. Channels (Newsfeed/Announcements)

Channels are broadcast communication systems (like a company newsfeed).

#### Channel Management
```python
# List channels
channels = client.fetch_channels()  # User's channels
all_channels = client.fetch_channels(all_channels=True)  # All org channels (admin)

# Get channel details with articles
channel = client.fetch_channel(channel_id="456")

# Create channel (admin only)
new_channel = client.create_channel({
    "name": "Company Announcements",
    "description": "Important updates",
    "type": "announcement"  # or "news", "social", etc.
})
```

#### Subscriptions
```python
# Subscribe to channel
client.subscribe_to_channel(channel_id="456")

# Unsubscribe from channel
client.unsubscribe_from_channel(channel_id="456")

# Get channel subscribers
subscribers = client.get(f"/channels/{channel_id}/subscribers")
```

#### Channel Organization
```python
# Pin channel for quick access
client.pin_channel(channel_id="456")

# Unpin channel
client.unpin_channel(channel_id="456")

# Mark all articles as read
client.put(f"/channels/{channel_id}/read")
```

#### Notifications
```python
# Get article notifications
notifications = client.get("/channels/notifications")

# Mark all notifications as read
client.put("/channels/notifications")

# Mark specific notification as read
client.put(f"/channels/notifications/{notification_id}")
```

### 5. Articles (Posts in Channels)

Articles are posts within channels (like newsfeed posts).

#### Creating & Managing Articles
```python
# Create article/post
article = client.create_article(
    channel_id="456",
    article_data={
        "title": "Important Update",
        "body": "Full article content here...",
        "attachments": [
            {"type": "image", "url": "https://..."},
            {"type": "file", "url": "https://...", "name": "document.pdf"}
        ]
    }
)

# Update article
client.update_article(
    channel_id="456",
    article_id="789",
    article_data={"title": "Updated Title"}
)

# Delete article
client.delete_article(channel_id="456", article_id="789")
```

#### Fetching Articles
```python
# Get all articles in channel
articles = client.fetch_articles(channel_id="456")

# Get specific article
article = client.fetch_article(channel_id="456", article_id="789")
```

#### Article Interactions
```python
# Like article
client.like_article(channel_id="456", article_id="789")

# Unlike article
client.unlike_article(channel_id="456", article_id="789")

# Get all likes
likes = client.get(f"/channels/{channel_id}/articles/{article_id}/likes")

# Mark article as read
client.mark_article_read(channel_id="456", article_id="789")

# Get users who read article
readers = client.get(
    f"/channels/{channel_id}/articles/{article_id}/seen"
)
```

### 6. Article Comments

Comments on articles enable discussions.

```python
# Get all comments
comments = client.fetch_article_comments(
    channel_id="456",
    article_id="789"
)

# Add comment
comment = client.add_article_comment(
    channel_id="456",
    article_id="789",
    text="Great update, thanks!"
)

# Update comment
client.update_article_comment(
    channel_id="456",
    article_id="789",
    comment_id="111",
    text="Updated comment text"
)

# Delete comment
client.delete_article_comment(
    channel_id="456",
    article_id="789",
    comment_id="111"
)
```

## Use Cases

### 1. Team Announcements
```python
# Create announcement channel
channel = client.create_channel({
    "name": "HR Announcements",
    "description": "Policy updates and company news"
})

# Post announcement
article = client.create_article(
    channel_id=channel["id"],
    article_data={
        "title": "New Benefits Package",
        "body": "We're excited to announce..."
    }
)
```

### 2. Shift Coordination
```python
# Create conversation with shift workers
conv = client.create_conversation(
    user_ids=get_shift_workers(),
    message="Need coverage for tomorrow's morning shift. Who's available?"
)

# Send follow-up
client.send_message(
    conversation_id=conv["id"],
    text="Thanks John for volunteering!"
)
```

### 3. Employee Engagement
```python
# Fetch company newsfeed
channels = client.fetch_channels()
for channel in channels:
    articles = client.fetch_articles(channel["id"])
    for article in articles:
        # Display article
        # Allow likes and comments
        pass
```

### 4. Emergency Notifications
```python
# Send urgent message to all managers
managers = get_manager_ids()
conv = client.create_conversation(
    user_ids=managers,
    message="⚠️ URGENT: Store closing early due to weather",
    group_name="Emergency Alert"
)
```

## Permissions & Access Control

### User Roles
- **Admin**: Full access to all features
- **Manager**: Can create channels, moderate conversations
- **Employee**: Can participate in conversations and channels they're subscribed to

### Important Notes
1. **Channel Creation**: Typically requires admin role
2. **All Channels**: Only admins can fetch all org channels
3. **Channel Subscribers**: Admins can manage who sees what channels
4. **Message Visibility**: Users only see conversations they're part of

## Data Structures

### Conversation Object
```json
{
  "id": "123456",
  "name": "Group Name",
  "type": "group",
  "members": [
    {"id": "111", "name": "John"},
    {"id": "222", "name": "Jane"}
  ],
  "lastMessage": {
    "text": "Last message...",
    "createdAt": "2024-01-15T10:30:00Z"
  },
  "unreadCount": 3,
  "silenced": false
}
```

### Message Object
```json
{
  "id": "789",
  "conversationId": "123456",
  "userId": "111",
  "text": "Message text",
  "attachments": [],
  "reactions": [
    {"emoji": "👍", "userId": "222"}
  ],
  "createdAt": "2024-01-15T10:30:00Z",
  "updatedAt": "2024-01-15T10:31:00Z"
}
```

### Channel Object
```json
{
  "id": "456",
  "name": "Announcements",
  "description": "Company news",
  "type": "announcement",
  "subscribed": true,
  "pinned": false,
  "unreadCount": 2
}
```

### Article Object
```json
{
  "id": "789",
  "channelId": "456",
  "title": "Article Title",
  "body": "Article content...",
  "attachments": [],
  "author": {
    "id": "111",
    "name": "John Doe"
  },
  "likes": 5,
  "comments": 3,
  "createdAt": "2024-01-15T09:00:00Z"
}
```

## Compensation Data Research

### Confirmed: NO Compensation Endpoints

Analyzed the complete OpenAPI specification at `https://api.getsling.com/v1/spec.json` and confirmed:

- ❌ No `/wages` endpoints
- ❌ No `/salary` endpoints
- ❌ No `/compensation` endpoints
- ❌ No `/pay` or `/payroll` endpoints
- ❌ No wage/salary fields in user objects

### Sling's Position
While Sling's web interface supports setting salaries and wages for labor cost calculations, **this data is intentionally excluded from the API** for privacy and security reasons. This is a common practice in HRIS/workforce management APIs.

### Workaround
Manage compensation data in your own system and use Sling only for:
- Scheduling
- Time tracking
- Team communication
- Shift management

## Testing the New Features

### Basic Test
```python
from sling_client import SlingAPIClient

client = SlingAPIClient()

# Test connection
assert client.test_connection()

# Test conversations
conversations = client.fetch_conversations()
print(f"Found {len(conversations)} conversations")

# Test channels
channels = client.fetch_channels()
print(f"Found {len(channels)} channels")
```

### Verify All Methods Available
```bash
python3 -c "from sling_client import SlingAPIClient; \
    methods = [m for m in dir(SlingAPIClient) if not m.startswith('_')]; \
    print(f'Total public methods: {len(methods)}')"
```

## Next Steps

1. **Add Tests**: Create unit tests for messaging methods in `tests/test_messaging.py`
2. **Add Mapping Utilities**: Create helper functions in `utils.py` for message/channel data transformation
3. **Update Version**: Bump version to `0.2.0` to reflect new features
4. **Django Integration**: Add messaging models and views to Django example

## See Also

- [README.md](README.md) - Main documentation
- [CLAUDE.md](CLAUDE.md) - Developer guide
- [examples/messaging_example.py](examples/messaging_example.py) - Working code examples
- [Sling API Spec](https://api.getsling.com/v1/spec.json) - Full OpenAPI specification
