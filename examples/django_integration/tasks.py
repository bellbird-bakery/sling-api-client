"""
Celery Tasks for Sling Integration

This file provides example Celery tasks for automated Sling synchronization.
These are reference implementations - adapt to your needs.

PREREQUISITES:
1. Celery installed and configured in your Django project
2. Redis or another message broker
3. django-celery-beat for scheduled tasks (optional)

SETUP:
1. Copy this file to your Django app
2. Customize the sync logic for your Employee model
3. Configure Celery Beat schedule in settings.py:

    # settings.py
    from celery.schedules import crontab

    CELERY_BEAT_SCHEDULE = {
        "sync-sling-employees-daily": {
            "task": "yourapp.tasks.sync_employees_from_sling",
            "schedule": crontab(hour=2, minute=0),  # 2:00 AM daily
        },
    }

CUSTOMIZATION:
- Update import paths to match your project structure
- Modify field mappings for your Employee model
- Customize email templates and recipients
- Adjust sync logic for your workflow

USAGE:
    # Run manually
    from yourapp.tasks import sync_employees_from_sling
    sync_employees_from_sling()

    # Via Celery
    sync_employees_from_sling.delay()
"""

import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

# ⚠️ CUSTOMIZE: Import your Celery app
# from config.celery_app import app  # Adjust to your project structure
from celery import shared_task

# ⚠️ CUSTOMIZE: Import your models
# from yourapp.models import Employee, Department, Role, SlingConflict
# For this example, using placeholder imports:
# from .models import Department, Role, SlingConflict

from sling_client import SlingAPIClient

User = get_user_model()
logger = logging.getLogger(__name__)


# Use @shared_task if you don't have a specific Celery app instance
# Or use @app.task() if you have a Celery app instance
@shared_task
def sync_employees_from_sling(update_window_hours=48, sync_reference_data=True):
    """
    Daily sync task to update employees from Sling.

    This task:
    1. Optionally syncs departments and roles
    2. Fetches employees from Sling (optionally filtered by update date)
    3. Updates employees with matching sling_id
    4. Creates SlingConflict records for discrepancies
    5. Sends summary email to HR managers

    Args:
        update_window_hours: Only fetch employees updated in last N hours (0 = all)
        sync_reference_data: Whether to sync departments/roles first

    Returns:
        dict: Summary statistics

    CUSTOMIZATION:
    - Update Department, Role, Employee imports
    - Modify field mappings in update logic
    - Customize conflict detection logic
    - Adjust email recipients (currently HR_MANAGER and ADMIN roles)
    """
    logger.info("Starting Sling employee sync task")

    # Initialize stats
    stats = {
        "started_at": timezone.now(),
        "employees_synced": 0,
        "employees_updated": 0,
        "employees_skipped": 0,
        "conflicts_created": 0,
        "departments_synced": 0,
        "roles_synced": 0,
        "errors": [],
    }

    try:
        # Initialize Sling API client
        client = SlingAPIClient()

        # Step 1: Sync reference data (departments and roles)
        if sync_reference_data:
            logger.info("Syncing departments and roles from Sling")
            try:
                # ⚠️ IMPLEMENT: Your department/role sync logic
                # dept_created, dept_updated = sync_departments_from_sling(client)
                # role_created, role_updated = sync_roles_from_sling(client)
                # stats["departments_synced"] = dept_created + dept_updated
                # stats["roles_synced"] = role_created + role_updated
                pass

            except Exception as e:
                error_msg = f"Error syncing reference data: {e}"
                logger.error(error_msg, exc_info=True)
                stats["errors"].append(error_msg)

        # Step 2: Fetch employees from Sling
        logger.info("Fetching employees from Sling")
        try:
            # Calculate updated_since timestamp if window specified
            updated_since = None
            if update_window_hours > 0:
                updated_since = timezone.now() - timedelta(hours=update_window_hours)
                # Convert to ISO format string if your API expects it
                # updated_since = updated_since.isoformat()

            sling_employees = client.fetch_employees()
            logger.info(f"Fetched {len(sling_employees)} employees from Sling")

            # Step 3: Update employees
            # ⚠️ IMPLEMENT: Your employee update logic
            # for sling_employee in sling_employees:
            #     try:
            #         sling_id = str(sling_employee.get("id"))
            #         # Only update employees that already have sling_id
            #         existing_employee = Employee.objects.filter(sling_id=sling_id).first()
            #
            #         if existing_employee:
            #             # Update employee data and detect conflicts
            #             conflicts = update_employee_from_sling(existing_employee, sling_employee)
            #             if conflicts:
            #                 stats["conflicts_created"] += len(conflicts)
            #             else:
            #                 stats["employees_updated"] += 1
            #         else:
            #             stats["employees_skipped"] += 1
            #     except Exception as e:
            #         error_msg = f"Error processing employee: {e}"
            #         logger.error(error_msg)
            #         stats["errors"].append(error_msg)

        except Exception as e:
            error_msg = f"Error fetching employees from Sling: {e}"
            logger.error(error_msg, exc_info=True)
            stats["errors"].append(error_msg)

        # Step 4: Send summary email to HR managers
        stats["completed_at"] = timezone.now()
        stats["duration"] = (stats["completed_at"] - stats["started_at"]).total_seconds()

        send_sync_summary_email(stats)

        logger.info(
            f"Sync task completed. Updated {stats['employees_updated']} employees, "
            f"{stats['conflicts_created']} conflicts, {len(stats['errors'])} errors"
        )

        return stats

    except Exception as e:
        error_msg = f"Critical error in sync task: {e}"
        logger.error(error_msg, exc_info=True)
        stats["errors"].append(error_msg)
        stats["completed_at"] = timezone.now()

        # Send error notification
        send_sync_summary_email(stats)

        raise


def send_sync_summary_email(stats):
    """
    Send sync summary email to HR managers.

    Args:
        stats: Dictionary of sync statistics

    CUSTOMIZATION:
    - Update User.objects.filter() to match your user role system
    - Create your own email template
    - Customize subject line and from_email
    """
    # ⚠️ CUSTOMIZE: Filter for your HR users
    # This example assumes a User model with a 'role' field
    hr_users = []
    # Example:
    # hr_users = User.objects.filter(
    #     role__in=["ADMIN", "HR_MANAGER"]
    # ).values_list("email", flat=True)

    if not hr_users:
        logger.warning("No HR managers found to send sync summary")
        return

    # ⚠️ CUSTOMIZE: Get conflicts from your SlingConflict model
    # unresolved_conflicts = SlingConflict.objects.filter(
    #     resolved=False
    # ).select_related("employee")[:10]

    # Prepare email context
    context = {
        "stats": stats,
        # "unresolved_conflicts": unresolved_conflicts,
        # "total_unresolved": SlingConflict.objects.filter(resolved=False).count(),
        "admin_url": getattr(settings, "ADMIN_URL", "/admin/"),
    }

    # Determine subject based on errors/conflicts
    if stats.get("errors"):
        subject_prefix = "[ERROR]"
    elif stats.get("conflicts_created", 0) > 0:
        subject_prefix = "[CONFLICTS]"
    else:
        subject_prefix = "[SUCCESS]"

    subject = f"{subject_prefix} Daily Sling Sync Summary"

    # ⚠️ CUSTOMIZE: Create your own email template
    # html_message = render_to_string(
    #     "yourapp/emails/sling_sync_summary.html",
    #     context
    # )

    # For now, use a simple plain text message
    plain_message = f"""
    Sling Sync Summary
    ==================

    Duration: {stats.get('duration', 0):.1f} seconds
    Employees Updated: {stats.get('employees_updated', 0)}
    Conflicts Created: {stats.get('conflicts_created', 0)}
    Errors: {len(stats.get('errors', []))}

    {'Errors: ' + ', '.join(stats['errors']) if stats.get('errors') else 'No errors'}
    """

    try:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=list(hr_users),
            # html_message=html_message,  # Uncomment when you have HTML template
            fail_silently=False,
        )
        logger.info(f"Sync summary email sent to {len(hr_users)} recipients")
    except Exception as e:
        logger.error(f"Failed to send sync summary email: {e}", exc_info=True)


# Example helper functions (implement these for your project)

def update_employee_from_sling(employee, sling_data):
    """
    Update employee from Sling data and detect conflicts.

    Args:
        employee: Your Employee model instance
        sling_data: Dictionary from Sling API

    Returns:
        List of conflict field names (empty if no conflicts)

    IMPLEMENTATION EXAMPLE:
        from sling_client import map_employee_from_sling, detect_field_conflicts

        # Map Sling data
        mapped_data = map_employee_from_sling(sling_data)

        # Detect conflicts
        local_data = {
            "first_name": employee.first_name,
            "last_name": employee.last_name,
            "email": employee.email,
        }
        conflicts = detect_field_conflicts(local_data, sling_data)

        if conflicts:
            # Create SlingConflict records
            for conflict in conflicts:
                SlingConflict.objects.create(
                    employee=employee,
                    field_name=conflict["field_name"],
                    local_value=conflict["local_value"],
                    sling_value=conflict["sling_value"],
                )
            return [c["field_name"] for c in conflicts]
        else:
            # No conflicts, update employee
            employee.first_name = mapped_data["first_name"]
            employee.last_name = mapped_data["last_name"]
            employee.email = mapped_data["email"]
            employee.sling_synced_at = timezone.now()
            employee.sling_sync_status = "SYNCED"
            employee.save()
            return []
    """
    pass  # Implement this for your project
