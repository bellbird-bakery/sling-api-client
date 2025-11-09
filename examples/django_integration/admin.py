"""
Django Admin Interface for Sling Integration

This file provides example admin configurations for Sling integration models.
Copy and adapt to your project.

CUSTOMIZATION POINTS:
1. Adjust search_fields to match your Employee model fields
2. Modify field_mapping in mark_as_resolved_use_sling to match your fields
3. Add custom filters or actions as needed
4. Customize the value comparison HTML styling

USAGE:
1. Copy to your Django app's admin.py
2. Customize search fields and employee model references
3. Register with Django admin
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import Department, Role, SlingConflict


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    """Admin interface for Department model."""

    list_display = ["name", "sling_id", "created_at", "updated_at"]
    search_fields = ["name", "sling_id"]
    readonly_fields = ["created_at", "updated_at"]
    list_per_page = 50


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Admin interface for Role model."""

    list_display = ["title", "sling_id", "created_at", "updated_at"]
    search_fields = ["title", "sling_id"]
    readonly_fields = ["created_at", "updated_at"]
    list_per_page = 50


@admin.register(SlingConflict)
class SlingConflictAdmin(admin.ModelAdmin):
    """
    Admin interface for SlingConflict model.

    Provides:
    - Side-by-side value comparison
    - Batch resolution actions
    - Filtering by status, field, date
    - Search by employee details

    CUSTOMIZATION:
    - Update search_fields to match your Employee model
    - Modify field_mapping in actions to match your Employee fields
    - Add custom actions for your workflow
    """

    list_display = [
        "employee",
        "field_name",
        "value_comparison",
        "resolved_status",
        "created_at",
        "resolved_at",
        "resolved_by",
    ]
    list_filter = ["resolved", "field_name", "resolution", "created_at"]

    # ⚠️ CUSTOMIZE: Update to match your Employee model fields
    search_fields = [
        "employee__first_name",
        "employee__last_name",
        "employee__email",
        "field_name"
    ]

    readonly_fields = ["created_at", "value_comparison_detail"]
    date_hierarchy = "created_at"
    list_per_page = 25

    fieldsets = (
        ("Conflict Information", {
            "fields": ("employee", "field_name", "created_at", "value_comparison_detail")
        }),
        ("Values", {
            "fields": ("local_value", "sling_value"),
            "classes": ("wide",),
        }),
        ("Resolution", {
            "fields": ("resolved", "resolution", "resolved_at", "resolved_by"),
        }),
    )

    def value_comparison(self, obj):
        """Show abbreviated value comparison in list view."""
        local = obj.local_value[:30] + "..." if len(obj.local_value) > 30 else obj.local_value
        sling = obj.sling_value[:30] + "..." if len(obj.sling_value) > 30 else obj.sling_value
        return format_html(
            '<div style="font-size: 0.9em;">'
            '<div><strong>Local:</strong> <code>{}</code></div>'
            '<div><strong>Sling:</strong> <code style="background: #fff9e6;">{}</code></div>'
            '</div>',
            local,
            sling
        )
    value_comparison.short_description = "Values"

    def value_comparison_detail(self, obj):
        """Show full value comparison in detail view with side-by-side layout."""
        return format_html(
            '<table style="width: 100%; border-collapse: collapse;">'
            '<tr style="background: #f9f9f9;">'
            '<th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Local Value (Current)</th>'
            '<th style="padding: 10px; border: 1px solid #ddd; text-align: left;">Sling Value (Source)</th>'
            '</tr>'
            '<tr>'
            '<td style="padding: 10px; border: 1px solid #ddd;"><code>{}</code></td>'
            '<td style="padding: 10px; border: 1px solid #ddd; background: #fff9e6;"><code>{}</code></td>'
            '</tr>'
            '</table>',
            obj.local_value,
            obj.sling_value
        )
    value_comparison_detail.short_description = "Value Comparison"

    def resolved_status(self, obj):
        """Display conflict resolution status with color coding."""
        if obj.resolved:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Resolved</span><br>'
                '<small style="color: #666;">{}</small>',
                obj.get_resolution_display() if obj.resolution else ""
            )
        return format_html(
            '<span style="color: red; font-weight: bold;">⚠ Unresolved</span>'
        )
    resolved_status.short_description = "Status"

    # Batch Actions
    actions = [
        "mark_as_resolved_keep_local",
        "mark_as_resolved_use_sling",
        "mark_as_dismissed"
    ]

    def mark_as_resolved_keep_local(self, request, queryset):
        """Mark conflicts as resolved, keeping local values (no changes to employee data)."""
        from django.utils import timezone

        updated = queryset.filter(resolved=False).update(
            resolved=True,
            resolution="KEEP_LOCAL",
            resolved_at=timezone.now(),
            resolved_by=request.user,
        )
        self.message_user(
            request,
            f"{updated} conflict(s) resolved (kept local values)."
        )
    mark_as_resolved_keep_local.short_description = "Resolve: Keep Local Values"

    def mark_as_resolved_use_sling(self, request, queryset):
        """
        Mark conflicts as resolved and update employees with Sling values.

        ⚠️ IMPORTANT: Update field_mapping to match YOUR Employee model fields!
        """
        from django.utils import timezone

        updated_count = 0

        # ⚠️ CUSTOMIZE THIS: Map conflict field_name to your Employee model field names
        field_mapping = {
            "first_name": "first_name",
            "last_name": "last_name",
            "email": "email",
            "phone": "phone",
            # Add more fields as needed for your model
        }

        for conflict in queryset.filter(resolved=False):
            if conflict.field_name in field_mapping:
                employee = conflict.employee
                employee_field = field_mapping[conflict.field_name]

                # Update the employee field with Sling value
                setattr(employee, employee_field, conflict.sling_value)
                employee.save()

                # Mark conflict as resolved
                conflict.resolved = True
                conflict.resolution = "USE_SLING"
                conflict.resolved_at = timezone.now()
                conflict.resolved_by = request.user
                conflict.save()
                updated_count += 1

        self.message_user(
            request,
            f"{updated_count} conflict(s) resolved (updated to Sling values)."
        )
    mark_as_resolved_use_sling.short_description = "Resolve: Use Sling Values (updates employees)"

    def mark_as_dismissed(self, request, queryset):
        """Mark conflicts as dismissed without making any changes."""
        from django.utils import timezone

        updated = queryset.filter(resolved=False).update(
            resolved=True,
            resolution="MANUAL",
            resolved_at=timezone.now(),
            resolved_by=request.user,
        )
        self.message_user(
            request,
            f"{updated} conflict(s) dismissed."
        )
    mark_as_dismissed.short_description = "Dismiss (no changes)"
