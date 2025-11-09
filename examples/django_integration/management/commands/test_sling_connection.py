"""
Management Command: Test Sling API Connection

This command tests your Sling API connection and displays sample data.

USAGE:
    python manage.py test_sling_connection
    python manage.py test_sling_connection --api-key YOUR_KEY
    python manage.py test_sling_connection --api-url https://api.getsling.com/v1

SETUP:
1. Copy this file to: yourapp/management/commands/test_sling_connection.py
2. Ensure management/commands/ directories exist
3. Add __init__.py files to management/ and management/commands/
4. Run: python manage.py test_sling_connection
"""

from django.core.management.base import BaseCommand
from django.conf import settings

from sling_client import SlingAPIClient


class Command(BaseCommand):
    """Test connection to Sling API and display basic information."""

    help = "Test connection to Sling API and display basic information"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--api-key",
            type=str,
            help="Override API key from settings",
        )
        parser.add_argument(
            "--api-url",
            type=str,
            help="Override API URL from settings",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        # Get API credentials
        api_key = options.get("api_key") or getattr(settings, "SLING_API_KEY", None)
        api_url = options.get("api_url") or getattr(
            settings, "SLING_API_URL", "https://api.getsling.com/v1"
        )

        if not api_key:
            self.stdout.write(
                self.style.ERROR(
                    "No API key found. Please set SLING_API_KEY in your settings "
                    "or provide --api-key argument."
                )
            )
            return

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Testing Sling API Connection"))
        self.stdout.write("=" * 60 + "\n")

        # Display configuration
        self.stdout.write(f"API URL: {api_url}")
        self.stdout.write(f"API Key: {'*' * (len(api_key) - 4)}{api_key[-4:]}")
        self.stdout.write("")

        # Initialize client
        try:
            client = SlingAPIClient(api_url=api_url, api_key=api_key)
            self.stdout.write(self.style.SUCCESS("✓ Client initialized"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Failed to initialize client: {e}"))
            return

        # Test connection
        self.stdout.write("\nTesting connection...")
        if client.test_connection():
            self.stdout.write(self.style.SUCCESS("✓ Connection successful"))
        else:
            self.stdout.write(self.style.ERROR("✗ Connection failed"))
            self.stdout.write(
                self.style.WARNING(
                    "\nNote: This might be expected if the /account endpoint "
                    "doesn't exist. The API might still work for other endpoints."
                )
            )

        # Try to fetch employees
        self.stdout.write("\nAttempting to fetch employees...")
        try:
            employees = client.fetch_employees(limit=5)
            self.stdout.write(
                self.style.SUCCESS(f"✓ Successfully fetched {len(employees)} employees")
            )

            if employees:
                self.stdout.write("\nSample employee data:")
                for i, emp in enumerate(employees[:3], 1):
                    self.stdout.write(f"\n  Employee {i}:")
                    self.stdout.write(f"    ID: {emp.get('id', 'N/A')}")
                    self.stdout.write(f"    Name: {emp.get('name', 'N/A')}")
                    self.stdout.write(f"    Email: {emp.get('email', 'N/A')}")
            else:
                self.stdout.write(self.style.WARNING("  No employees returned"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Failed to fetch employees: {e}"))

        # Try to fetch departments
        self.stdout.write("\nAttempting to fetch departments...")
        try:
            departments = client.fetch_departments()
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Successfully fetched {len(departments)} departments"
                )
            )

            if departments:
                self.stdout.write("\nDepartments:")
                for dept in departments[:5]:
                    self.stdout.write(
                        f"  - {dept.get('name', dept.get('id', 'N/A'))}"
                    )
            else:
                self.stdout.write(self.style.WARNING("  No departments returned"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Failed to fetch departments: {e}"))

        # Try to fetch roles
        self.stdout.write("\nAttempting to fetch roles...")
        try:
            roles = client.fetch_roles()
            self.stdout.write(
                self.style.SUCCESS(f"✓ Successfully fetched {len(roles)} roles")
            )

            if roles:
                self.stdout.write("\nRoles:")
                for role in roles[:5]:
                    self.stdout.write(
                        f"  - {role.get('title', role.get('name', 'N/A'))}"
                    )
            else:
                self.stdout.write(self.style.WARNING("  No roles returned"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Failed to fetch roles: {e}"))

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("Connection test complete"))
        self.stdout.write("=" * 60 + "\n")
