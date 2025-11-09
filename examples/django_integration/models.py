"""
Django Models for Sling Integration

This file provides example models for Sling integration. Copy and adapt to your project.

CUSTOMIZATION POINTS:
1. Adjust field names/types to match your database schema
2. Add/remove fields as needed for your use case
3. Change the ForeignKey target for SlingConflict.employee
4. Modify __str__ methods and Meta options

REQUIRED DEPENDENCIES:
- Django >= 4.0

USAGE:
1. Copy these models to your Django app's models.py
2. Customize field names and relationships
3. Run makemigrations and migrate
4. Use these models with the sling_client package
"""

from django.conf import settings
from django.db import models


class Department(models.Model):
    """
    Department synced from Sling.

    Sling uses "location" type groups for departments.
    This model stores department data from Sling's /groups endpoint.

    CUSTOMIZATION:
    - Add custom fields (e.g., cost_center, manager_id)
    - Change field sizes if needed
    - Add custom methods (e.g., get_employee_count())
    """

    name = models.CharField(max_length=200)
    sling_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Sling group ID"
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Department"
        verbose_name_plural = "Departments"

    def __str__(self):
        return self.name


class Role(models.Model):
    """
    Role/Position synced from Sling.

    Sling uses "position" type groups for roles.
    This model stores role/position data from Sling's /groups endpoint.

    CUSTOMIZATION:
    - Rename to Position or JobTitle if preferred
    - Add fields like pay_grade, responsibilities
    - Add relationships (e.g., department, reports_to)
    """

    title = models.CharField(max_length=200)
    sling_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Sling group ID"
    )
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]
        verbose_name = "Role"
        verbose_name_plural = "Roles"

    def __str__(self):
        return self.title


class SlingConflict(models.Model):
    """
    Track data conflicts between local system and Sling.

    When syncing data from Sling, conflicts may occur if local data
    differs from Sling data. This model stores those conflicts for
    manual review and resolution.

    CUSTOMIZATION:
    - Change employee ForeignKey to match your Employee/Person model
    - Add custom resolution types if needed
    - Add metadata fields (e.g., auto_resolve, priority)

    WORKFLOW:
    1. Sync detects conflict → creates SlingConflict record
    2. HR reviews conflict in admin or UI
    3. HR chooses resolution: Keep Local / Use Sling / Manual
    4. Conflict marked as resolved

    IMPORTANT: Update the employee ForeignKey to point to YOUR employee model!
    Example:
        employee = models.ForeignKey(
            "myapp.Employee",  # Change to your app.Model
            on_delete=models.CASCADE,
            related_name="sling_conflicts",
        )
    """

    RESOLUTION_CHOICES = [
        ("KEEP_LOCAL", "Keep Local Value"),
        ("USE_SLING", "Use Sling Value"),
        ("MANUAL", "Merged Manually"),
    ]

    # ⚠️ CUSTOMIZE THIS: Point to your Employee/Person model
    employee = models.ForeignKey(
        "employees.Employee",  # Change to your model (e.g., "yourapp.Employee")
        on_delete=models.CASCADE,
        related_name="sling_conflicts",
    )

    field_name = models.CharField(
        max_length=100,
        help_text="Field that has conflicting data"
    )
    local_value = models.TextField(help_text="Current value in local database")
    sling_value = models.TextField(help_text="Value from Sling API")

    # Resolution tracking
    resolved = models.BooleanField(default=False)
    resolution = models.CharField(
        max_length=20,
        choices=RESOLUTION_CHOICES,
        blank=True,
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_sling_conflicts",  # Avoid conflicts with other models
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Sling Conflict"
        verbose_name_plural = "Sling Conflicts"
        indexes = [
            models.Index(fields=["resolved", "created_at"]),
            models.Index(fields=["field_name"]),
        ]

    def __str__(self):
        # Customize this based on your Employee model's __str__ or name field
        return f"Conflict: {self.employee} - {self.field_name}"


# OPTIONAL: Mixin for your Employee/Person model
# Add this mixin to your existing Employee model to track Sling sync status

class SlingIntegratedModelMixin(models.Model):
    """
    Abstract model mixin for models that sync with Sling.

    Add this mixin to your Employee/Person model to track sync status.

    Example usage:
        class Employee(SlingIntegratedModelMixin, models.Model):
            # Your existing fields...
            first_name = models.CharField(max_length=100)
            last_name = models.CharField(max_length=100)
            email = models.EmailField()

            # Optionally add relationships to Department and Role
            sling_department = models.ForeignKey(
                'Department',
                on_delete=models.SET_NULL,
                null=True,
                blank=True
            )
            sling_positions = models.ManyToManyField('Role', blank=True)
    """

    SYNC_STATUS_CHOICES = [
        ("NOT_SYNCED", "Not Synced"),
        ("SYNCED", "Synced"),
        ("CONFLICT", "Has Conflicts"),
        ("FAILED", "Sync Failed"),
    ]

    sling_id = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Sling user ID"
    )
    sling_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last successful sync from Sling"
    )
    sling_sync_status = models.CharField(
        max_length=20,
        choices=SYNC_STATUS_CHOICES,
        default="NOT_SYNCED",
    )

    class Meta:
        abstract = True

    def is_synced_with_sling(self):
        """Check if this record is synced with Sling."""
        return bool(self.sling_id) and self.sling_sync_status == "SYNCED"

    def has_sling_conflicts(self):
        """Check if this record has unresolved Sling conflicts."""
        # This assumes the related_name is 'sling_conflicts'
        return hasattr(self, 'sling_conflicts') and \
               self.sling_conflicts.filter(resolved=False).exists()
