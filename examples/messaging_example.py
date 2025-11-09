"""Example script demonstrating Sling messaging and communication features.

This example shows how to:
1. Create and manage conversations
2. Send messages and add reactions
3. Work with channels (newsfeed/announcements)
4. Create and interact with articles (posts)
5. Search conversations
"""

import logging
from sling_client import SlingAPIClient

# Set up logging
logging.basicConfig(level=logging.INFO)


def messaging_demo():
    """Demonstrate messaging capabilities."""
    # Initialize client
    client = SlingAPIClient()

    # Example 1: List and create conversations
    print("\n=== Conversations ===")
    conversations = client.fetch_conversations()
    print(f"Found {len(conversations)} conversations")

    # Create a new group conversation
    new_conversation = client.create_conversation(
        user_ids=["123456", "789012"],
        message="Hey team, let's coordinate on tomorrow's shifts",
        group_name="Shift Coordination"
    )
    conversation_id = new_conversation.get("id")
    print(f"Created conversation: {conversation_id}")

    # Example 2: Send messages
    print("\n=== Messages ===")
    message = client.send_message(
        conversation_id=conversation_id,
        text="Can someone cover the morning shift tomorrow?"
    )
    message_id = message.get("id")
    print(f"Sent message: {message_id}")

    # Add reaction to message
    client.add_message_reaction(
        conversation_id=conversation_id,
        message_id=message_id,
        emoji="👍"
    )
    print("Added reaction to message")

    # Fetch message history
    messages = client.fetch_messages(
        conversation_id=conversation_id,
        limit=20
    )
    print(f"Fetched {len(messages)} messages from conversation")

    # Example 3: Search conversations
    print("\n=== Search ===")
    results = client.search_conversations(query="shift")
    print(f"Found {len(results)} results for 'shift'")

    # Example 4: Work with channels (newsfeed)
    print("\n=== Channels (Newsfeed) ===")
    channels = client.fetch_channels()
    print(f"Found {len(channels)} channels")

    if channels:
        channel_id = channels[0].get("id")
        channel_name = channels[0].get("name")
        print(f"Working with channel: {channel_name} ({channel_id})")

        # Subscribe to channel
        client.subscribe_to_channel(channel_id=channel_id)
        print("Subscribed to channel")

        # Pin for quick access
        client.pin_channel(channel_id=channel_id)
        print("Pinned channel")

    # Example 5: Create and interact with articles (posts)
    print("\n=== Articles (Posts) ===")
    if channels:
        # Create a new article/post
        article = client.create_article(
            channel_id=channel_id,
            article_data={
                "title": "Important: New Schedule Policy",
                "body": "Starting next month, all shift swaps must be approved 24 hours in advance.",
                "attachments": []
            }
        )
        article_id = article.get("id")
        print(f"Created article: {article_id}")

        # Like the article
        client.like_article(channel_id=channel_id, article_id=article_id)
        print("Liked article")

        # Add a comment
        comment = client.add_article_comment(
            channel_id=channel_id,
            article_id=article_id,
            text="Thanks for the heads up!"
        )
        print(f"Added comment: {comment.get('id')}")

        # Mark as read
        client.mark_article_read(channel_id=channel_id, article_id=article_id)
        print("Marked article as read")

        # Fetch all comments
        comments = client.fetch_article_comments(
            channel_id=channel_id,
            article_id=article_id
        )
        print(f"Article has {len(comments)} comments")

    # Example 6: Bulk messaging
    print("\n=== Bulk Messaging ===")
    client.send_bulk_message(
        conversation_id=conversation_id,
        recipients=["123456", "789012", "345678"],
        text="Reminder: Team meeting at 3pm today"
    )
    print("Sent bulk message to 3 recipients")

    # Example 7: Conversation management
    print("\n=== Conversation Management ===")
    # Silence notifications
    client.silence_conversation(conversation_id=conversation_id)
    print("Silenced conversation")

    # Re-enable notifications
    client.unsilence_conversation(conversation_id=conversation_id)
    print("Unsilenced conversation")

    print("\n=== Demo Complete ===")


def broadcast_announcement():
    """Example: Broadcast an announcement to all employees."""
    client = SlingAPIClient()

    # Create a new channel for announcements (admin only)
    channel = client.create_channel({
        "name": "Company Announcements",
        "description": "Important updates from management",
        "type": "announcement"
    })
    channel_id = channel.get("id")

    # Post an announcement
    article = client.create_article(
        channel_id=channel_id,
        article_data={
            "title": "Holiday Schedule Update",
            "body": """
            Hi everyone,

            Please note the following holiday schedule changes:
            - Dec 24: Close at 3pm
            - Dec 25: Closed
            - Dec 26: Regular hours

            Thanks!
            Management
            """,
            "attachments": []
        }
    )

    print(f"Broadcast announcement posted: {article.get('id')}")


def shift_coordination_workflow():
    """Example: Coordinate shift coverage via messaging."""
    client = SlingAPIClient()

    # 1. Check for available shifts
    shifts = client.fetch_shifts(
        start_date="2024-01-15",
        end_date="2024-01-15"
    )

    unassigned = [s for s in shifts if not s.get("user")]
    print(f"Found {len(unassigned)} unassigned shifts")

    if unassigned:
        shift = unassigned[0]
        shift_id = shift.get("id")

        # 2. Get employees who work this position
        position_id = shift.get("position")
        group = client.fetch_group(group_id=position_id)
        eligible_employees = [m.get("id") for m in group.get("members", [])]

        # 3. Create conversation with eligible employees
        conversation = client.create_conversation(
            user_ids=eligible_employees,
            message=f"Need coverage for {shift.get('dtstart')} - {shift.get('dtend')}. Who's available?",
            group_name="Shift Coverage Request"
        )

        print(f"Created conversation with {len(eligible_employees)} employees")

        # 4. When someone volunteers, assign the shift
        # (In real implementation, this would be triggered by a response)
        # client.update_shift(shift_id=shift_id, shift_data={"user": volunteer_id})


if __name__ == "__main__":
    try:
        # Run the main demo
        messaging_demo()

        # Uncomment to run other examples:
        # broadcast_announcement()
        # shift_coordination_workflow()

    except Exception as e:
        print(f"Error: {e}")
        logging.exception("Demo failed")
