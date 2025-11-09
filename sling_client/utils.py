"""Utility functions for field mapping and data transformation.

These utilities help map data between Sling API format and your application's models.
They are framework-agnostic and can be used with Django, SQLAlchemy, or any other ORM.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def map_employee_from_sling(sling_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map Sling user data to standard employee fields.

    This function extracts common fields from Sling API response and normalizes them.
    You can use this as a base and extend/modify for your specific needs.

    Args:
        sling_data: Dictionary from Sling API /users endpoint

    Returns:
        Dictionary with normalized employee fields

    Example Sling data:
        {
          "id": 6880218,
          "name": "Jeremy",
          "legalName": "Jeremy",
          "preferredName": null,
          "lastname": "MacCormack",
          "email": "jeremy@example.com",
          "timezone": "Pacific/Auckland",
          "hoursCap": 0,
          "active": true,
          "deactivatedAt": null,
          "timeclockEnabled": false,
          "avatar": "https://...",
          "type": "user"
        }
    """
    # Determine first name and last name
    first_name = sling_data.get("name", "")
    last_name = sling_data.get("lastname", "")

    # Use preferred name if available, otherwise use legal name
    preferred_name = sling_data.get("preferredName")
    if preferred_name and preferred_name.strip():
        first_name = preferred_name.strip()
    elif sling_data.get("legalName"):
        first_name = sling_data.get("legalName", first_name)

    # Map to standard fields
    mapped_data = {
        # Sling-specific fields
        "sling_id": str(sling_data.get("id")),
        # Personal information
        "first_name": first_name.strip() if first_name else "Unknown",
        "last_name": last_name.strip() if last_name else "Unknown",
        "email": sling_data.get("email", "").strip(),
        # Status
        "is_active": sling_data.get("active", True),
        "timezone": sling_data.get("timezone", ""),
        "avatar_url": sling_data.get("avatar", ""),
    }

    # Handle termination date
    if not sling_data.get("active") and sling_data.get("deactivatedAt"):
        try:
            deactivated_str = sling_data.get("deactivatedAt")
            # Parse ISO date string
            deactivated_date = datetime.fromisoformat(
                deactivated_str.replace("+00:00", "").replace("Z", "")
            ).date()
            mapped_data["termination_date"] = deactivated_date
        except (ValueError, AttributeError) as e:
            logger.warning(f"Could not parse deactivatedAt date: {e}")

    return mapped_data


def map_department_from_sling(sling_group: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map Sling location group to standard department fields.

    Args:
        sling_group: Dictionary from Sling API /groups endpoint (type: location)

    Returns:
        Dictionary with department fields

    Example:
        {
          "id": 6880223,
          "type": "location",
          "name": "Bellbird Bakery",
          "externalId": null,
          "archivedAt": null,
          "memberCount": 32
        }
    """
    return {
        "sling_id": str(sling_group.get("id")),
        "name": sling_group.get("name", "Unknown").strip(),
        "member_count": sling_group.get("memberCount", 0),
        "is_archived": bool(sling_group.get("archivedAt")),
    }


def map_role_from_sling(sling_group: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map Sling position group to standard role fields.

    Args:
        sling_group: Dictionary from Sling API /groups endpoint (type: position)

    Returns:
        Dictionary with role fields

    Example:
        {
          "id": 6880243,
          "type": "position",
          "name": "Holmwood Baker",
          "externalId": null,
          "archivedAt": null,
          "memberCount": 11
        }
    """
    return {
        "sling_id": str(sling_group.get("id")),
        "title": sling_group.get("name", "Unknown").strip(),
        "member_count": sling_group.get("memberCount", 0),
        "is_archived": bool(sling_group.get("archivedAt")),
    }


def map_employee_to_sling(employee_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map standard employee data to Sling API format for creating/updating users.

    Args:
        employee_data: Dictionary with employee data

    Returns:
        Dictionary formatted for Sling API POST /users or PUT /users/{id}

    Example input:
        {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "is_active": True,
            "timezone": "Pacific/Auckland"
        }
    """
    sling_data = {
        "email": employee_data.get("email"),
        "name": employee_data.get("first_name", ""),
        "lastname": employee_data.get("last_name", ""),
        "legalName": employee_data.get("first_name", ""),
        "active": employee_data.get("is_active", True),
    }

    # Add timezone if available
    if employee_data.get("timezone"):
        sling_data["timezone"] = employee_data["timezone"]
    else:
        sling_data["timezone"] = "Pacific/Auckland"  # Default

    return sling_data


def detect_field_conflicts(
    local_data: Dict[str, Any],
    sling_data: Dict[str, Any],
    fields_to_check: Optional[Dict[str, str]] = None,
) -> list:
    """
    Detect conflicts between local data and Sling data.

    This is useful for identifying data discrepancies that need manual resolution.

    Args:
        local_data: Dictionary with local employee data
        sling_data: Dictionary from Sling API (unmapped)
        fields_to_check: Optional dict mapping local field names to Sling field names
                         Default: {"first_name": "name", "last_name": "lastname", "email": "email"}

    Returns:
        List of conflict dictionaries with field_name, local_value, sling_value

    Example:
        conflicts = detect_field_conflicts(
            local_data={"first_name": "John", "last_name": "Doe"},
            sling_data={"name": "Johnny", "lastname": "Doe"}
        )
        # Returns: [{"field_name": "first_name", "local_value": "John", "sling_value": "Johnny"}]
    """
    conflicts = []

    # Map Sling data to standard format
    sling_mapped = map_employee_from_sling(sling_data)

    # Default fields to check
    if fields_to_check is None:
        fields_to_check = {
            "first_name": "first_name",
            "last_name": "last_name",
            "email": "email",
        }

    for local_field, sling_field in fields_to_check.items():
        local_value = local_data.get(local_field, "")
        sling_value = sling_mapped.get(sling_field, "")

        # Normalize for comparison (strip whitespace, lowercase)
        local_normalized = str(local_value).strip().lower()
        sling_normalized = str(sling_value).strip().lower()

        if local_normalized != sling_normalized:
            conflicts.append(
                {
                    "field_name": local_field,
                    "local_value": str(local_value),
                    "sling_value": str(sling_value),
                }
            )

    return conflicts


def parse_sling_date(date_string: Optional[str]) -> Optional[datetime]:
    """
    Parse a Sling API date string to a datetime object.

    Sling typically returns dates in ISO format with timezone info.

    Args:
        date_string: ISO date string (e.g., "2024-01-15T10:30:00+00:00")

    Returns:
        datetime object or None if parsing fails
    """
    if not date_string:
        return None

    try:
        # Remove timezone info for simpler parsing
        cleaned = date_string.replace("+00:00", "").replace("Z", "")
        return datetime.fromisoformat(cleaned)
    except (ValueError, AttributeError) as e:
        logger.warning(f"Could not parse Sling date '{date_string}': {e}")
        return None
