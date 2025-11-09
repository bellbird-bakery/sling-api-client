"""Unit tests for utility functions."""
import pytest
from datetime import datetime, date
from sling_client.utils import (
    map_employee_from_sling,
    map_department_from_sling,
    map_role_from_sling,
    map_employee_to_sling,
    detect_field_conflicts,
    parse_sling_date,
)


class TestEmployeeMapping:
    """Test employee field mapping."""

    def test_map_employee_basic(self):
        """Test basic employee mapping."""
        sling_data = {
            "id": 123,
            "name": "John",
            "lastname": "Doe",
            "email": "john@test.com",
            "active": True,
        }

        result = map_employee_from_sling(sling_data)

        assert result["sling_id"] == "123"
        assert result["first_name"] == "John"
        assert result["last_name"] == "Doe"
        assert result["email"] == "john@test.com"
        assert result["is_active"] is True

    def test_map_employee_with_preferred_name(self):
        """Test mapping with preferred name."""
        sling_data = {
            "id": 123,
            "name": "Jonathan",
            "preferredName": "John",
            "lastname": "Doe",
            "email": "john@test.com",
            "active": True,
        }

        result = map_employee_from_sling(sling_data)
        assert result["first_name"] == "John"  # Should use preferred name

    def test_map_employee_with_legal_name(self):
        """Test mapping with legal name."""
        sling_data = {
            "id": 123,
            "name": "J",
            "legalName": "Jonathan",
            "lastname": "Doe",
            "email": "john@test.com",
            "active": True,
        }

        result = map_employee_from_sling(sling_data)
        assert result["first_name"] == "Jonathan"  # Should use legal name

    def test_map_employee_inactive_with_deactivation_date(self):
        """Test mapping inactive employee with deactivation date."""
        sling_data = {
            "id": 123,
            "name": "John",
            "lastname": "Doe",
            "email": "john@test.com",
            "active": False,
            "deactivatedAt": "2024-01-15T10:30:00",
        }

        result = map_employee_from_sling(sling_data)
        assert result["is_active"] is False
        assert "termination_date" in result
        assert isinstance(result["termination_date"], date)

    def test_map_employee_missing_fields(self):
        """Test mapping with missing fields."""
        sling_data = {
            "id": 123,
        }

        result = map_employee_from_sling(sling_data)
        assert result["first_name"] == "Unknown"
        assert result["last_name"] == "Unknown"
        assert result["email"] == ""


class TestDepartmentMapping:
    """Test department field mapping."""

    def test_map_department(self):
        """Test basic department mapping."""
        sling_group = {
            "id": 456,
            "type": "location",
            "name": "Engineering",
            "memberCount": 25,
        }

        result = map_department_from_sling(sling_group)
        assert result["sling_id"] == "456"
        assert result["name"] == "Engineering"
        assert result["member_count"] == 25
        assert result["is_archived"] is False


class TestRoleMapping:
    """Test role field mapping."""

    def test_map_role(self):
        """Test basic role mapping."""
        sling_group = {
            "id": 789,
            "type": "position",
            "name": "Software Engineer",
            "memberCount": 15,
        }

        result = map_role_from_sling(sling_group)
        assert result["sling_id"] == "789"
        assert result["title"] == "Software Engineer"
        assert result["member_count"] == 15
        assert result["is_archived"] is False


class TestEmployeeToSling:
    """Test mapping employee data to Sling format."""

    def test_map_employee_to_sling(self):
        """Test mapping employee to Sling format."""
        employee_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@test.com",
            "is_active": True,
            "timezone": "America/New_York",
        }

        result = map_employee_to_sling(employee_data)
        assert result["name"] == "John"
        assert result["lastname"] == "Doe"
        assert result["email"] == "john@test.com"
        assert result["active"] is True
        assert result["timezone"] == "America/New_York"

    def test_map_employee_to_sling_default_timezone(self):
        """Test default timezone."""
        employee_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@test.com",
            "is_active": True,
        }

        result = map_employee_to_sling(employee_data)
        assert result["timezone"] == "Pacific/Auckland"  # Default


class TestConflictDetection:
    """Test conflict detection."""

    def test_detect_no_conflicts(self):
        """Test when there are no conflicts."""
        local_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@test.com",
        }
        sling_data = {
            "id": 123,
            "name": "John",
            "lastname": "Doe",
            "email": "john@test.com",
        }

        conflicts = detect_field_conflicts(local_data, sling_data)
        assert len(conflicts) == 0

    def test_detect_name_conflict(self):
        """Test detecting name conflict."""
        local_data = {
            "first_name": "Jonathan",
            "last_name": "Doe",
            "email": "john@test.com",
        }
        sling_data = {
            "id": 123,
            "name": "John",
            "lastname": "Doe",
            "email": "john@test.com",
        }

        conflicts = detect_field_conflicts(local_data, sling_data)
        assert len(conflicts) == 1
        assert conflicts[0]["field_name"] == "first_name"
        assert conflicts[0]["local_value"] == "Jonathan"
        assert conflicts[0]["sling_value"] == "John"

    def test_detect_multiple_conflicts(self):
        """Test detecting multiple conflicts."""
        local_data = {
            "first_name": "Jonathan",
            "last_name": "Smith",
            "email": "john@test.com",
        }
        sling_data = {
            "id": 123,
            "name": "John",
            "lastname": "Doe",
            "email": "john@test.com",
        }

        conflicts = detect_field_conflicts(local_data, sling_data)
        assert len(conflicts) == 2
        field_names = [c["field_name"] for c in conflicts]
        assert "first_name" in field_names
        assert "last_name" in field_names

    def test_detect_conflicts_case_insensitive(self):
        """Test that conflicts are case-insensitive."""
        local_data = {
            "first_name": "JOHN",
            "last_name": "DOE",
            "email": "JOHN@TEST.COM",
        }
        sling_data = {
            "id": 123,
            "name": "john",
            "lastname": "doe",
            "email": "john@test.com",
        }

        conflicts = detect_field_conflicts(local_data, sling_data)
        assert len(conflicts) == 0  # Should be no conflicts (case-insensitive)

    def test_detect_conflicts_custom_fields(self):
        """Test custom field mapping."""
        local_data = {
            "given_name": "John",
            "family_name": "Doe",
        }
        sling_data = {
            "id": 123,
            "name": "Jonathan",
            "lastname": "Doe",
        }

        fields_to_check = {
            "given_name": "first_name",  # Local field → Sling field mapping
            "family_name": "last_name",
        }

        conflicts = detect_field_conflicts(
            local_data,
            sling_data,
            fields_to_check=fields_to_check
        )

        assert len(conflicts) == 1
        assert conflicts[0]["field_name"] == "given_name"


class TestDateParsing:
    """Test date parsing utilities."""

    def test_parse_sling_date_iso_format(self):
        """Test parsing ISO format date."""
        date_string = "2024-01-15T10:30:00"
        result = parse_sling_date(date_string)

        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 15

    def test_parse_sling_date_with_timezone(self):
        """Test parsing date with timezone."""
        date_string = "2024-01-15T10:30:00+00:00"
        result = parse_sling_date(date_string)

        assert isinstance(result, datetime)
        assert result.year == 2024

    def test_parse_sling_date_with_z(self):
        """Test parsing date with Z timezone."""
        date_string = "2024-01-15T10:30:00Z"
        result = parse_sling_date(date_string)

        assert isinstance(result, datetime)
        assert result.year == 2024

    def test_parse_sling_date_none(self):
        """Test parsing None."""
        result = parse_sling_date(None)
        assert result is None

    def test_parse_sling_date_invalid(self):
        """Test parsing invalid date string."""
        result = parse_sling_date("invalid")
        assert result is None  # Should return None instead of raising exception
