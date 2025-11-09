```markdown
# Django Integration Guide for Sling API Client

This guide shows you how to integrate the `sling-api-client` package into your Django project for employee synchronization with Sling.

## Overview

This integration provides:

- ✅ **Models** for storing Sling data (Department, Role, Conflicts)
- ✅ **Admin Interface** for managing conflicts
- ✅ **Celery Tasks** for automated daily syncing
- ✅ **Management Commands** for manual operations
- ✅ **Conflict Detection** and resolution workflow
- ✅ **Automated Email Notifications** for sync summaries

## Prerequisites

- Django >= 4.0
- PostgreSQL or MySQL (recommended for production)
- Celery + Redis (optional, for automated syncing)
- sling-api-client package installed

## Installation Steps

### 1. Install the Package

```bash
pip install git+https://github.com/your-org/sling-api-client.git
```

### 2. Configure Django Settings

Add to your `settings.py`:

```python
# Sling API Configuration
SLING_API_URL = env("SLING_API_URL", default="https://api.getsling.com/v1")
SLING_API_KEY = env("SLING_API_KEY")  # Required - get from Sling dashboard
SLING_API_TIMEOUT = env.int("SLING_API_TIMEOUT", default=30)
```

Set environment variables:

```bash
# .env or .envs/.local/.django
SLING_API_KEY=your_sling_api_key_here
SLING_API_URL=https://api.getsling.com/v1
SLING_API_TIMEOUT=30
```

### 3. Create Django App for Integration

```bash
python manage.py startapp integrations
```

Add to `INSTALLED_APPS` in `settings.py`:

```python
INSTALLED_APPS = [
    # ... other apps
    "your_project.integrations",
]
```

### 4. Add Models

Copy `models.py` from this directory to your `integrations/models.py`.

**Important**: Update the `SlingConflict` model's employee ForeignKey to point to your Employee model:

```python
# integrations/models.py
class SlingConflict(models.Model):
    employee = models.ForeignKey(
        "employees.Employee",  # ⚠️ Change to YOUR app.Model
        on_delete=models.CASCADE,
        related_name="sling_conflicts",
    )
    # ... rest of model
```

### 5. Add Sling Fields to Your Employee Model

Add the `SlingIntegratedModelMixin` to your Employee model:

```python
# employees/models.py
from your_project.integrations.models import SlingIntegratedModelMixin

class Employee(SlingIntegratedModelMixin, models.Model):
    # Your existing fields
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()

    # Sling relationships (optional but recommended)
    sling_department = models.ForeignKey(
        'integrations.Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='employees'
    )
    sling_positions = models.ManyToManyField(
        'integrations.Role',
        blank=True,
        related_name='employees'
    )

    # ... rest of your model
```

### 6. Create and Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Register Admin Interface

Copy `admin.py` from this directory to your `integrations/admin.py`.

Update search fields to match your Employee model:

```python
# integrations/admin.py
@admin.register(SlingConflict)
class SlingConflictAdmin(admin.ModelAdmin):
    search_fields = [
        "employee__first_name",  # ⚠️ Adjust to match your Employee fields
        "employee__last_name",
        "employee__email",
        "field_name"
    ]
    # ... rest of admin
```

### 8. Add Management Commands (Optional)

Create management command structure:

```bash
mkdir -p integrations/management/commands
touch integrations/management/__init__.py
touch integrations/management/commands/__init__.py
```

Copy `management/commands/test_sling_connection.py` to your commands directory.

Test the connection:

```bash
python manage.py test_sling_connection
```

### 9. Configure Celery for Automated Sync (Optional)

If you want automated daily syncing, set up Celery:

#### Install Dependencies

```bash
pip install celery redis django-celery-beat
```

#### Configure Celery

```python
# config/celery_app.py (or your Celery config file)
from celery import Celery
from celery.schedules import crontab

app = Celery('your_project')
app.config_from_object('django.conf:settings', namespace='CELERY')

# Celery Beat Schedule
app.conf.beat_schedule = {
    'sync-sling-employees-daily': {
        'task': 'your_project.integrations.tasks.sync_employees_from_sling',
        'schedule': crontab(hour=2, minute=0),  # 2:00 AM daily
    },
}
```

#### Create Tasks File

Copy `tasks.py` from this directory and customize:

1. Update import paths
2. Implement sync logic for your Employee model
3. Customize email recipients

### 10. Implement Sync Logic

Create `integrations/sync_helpers.py`:

```python
"""Helper functions for syncing employees from Sling."""
import logging
from django.utils import timezone
from sling_client import map_employee_from_sling, detect_field_conflicts
from .models import Department, Role, SlingConflict
from employees.models import Employee  # Your Employee model

logger = logging.getLogger(__name__)


def update_employee_from_sling(employee, sling_data):
    """
    Update employee from Sling data and detect conflicts.

    Args:
        employee: Employee model instance
        sling_data: Dictionary from Sling API

    Returns:
        List of conflict field names (empty if no conflicts)
    """
    # Map Sling data to standard format
    mapped_data = map_employee_from_sling(sling_data)

    # Prepare local data for conflict detection
    local_data = {
        "first_name": employee.first_name,
        "last_name": employee.last_name,
        "email": employee.email,
    }

    # Detect conflicts
    conflicts = detect_field_conflicts(local_data, sling_data)

    if conflicts:
        # Create SlingConflict records
        for conflict in conflicts:
            SlingConflict.objects.get_or_create(
                employee=employee,
                field_name=conflict["field_name"],
                resolved=False,
                defaults={
                    "local_value": conflict["local_value"],
                    "sling_value": conflict["sling_value"],
                }
            )
        logger.warning(
            f"Conflicts detected for {employee.first_name} {employee.last_name}: "
            f"{', '.join(c['field_name'] for c in conflicts)}"
        )
        employee.sling_sync_status = "CONFLICT"
        employee.save(update_fields=["sling_sync_status"])
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


def sync_departments_from_sling(client):
    """Sync departments from Sling."""
    from sling_client import map_department_from_sling

    departments = client.fetch_departments()
    created = updated = 0

    for sling_dept in departments:
        mapped = map_department_from_sling(sling_dept)
        dept, was_created = Department.objects.update_or_create(
            sling_id=mapped["sling_id"],
            defaults={"name": mapped["name"]}
        )
        if was_created:
            created += 1
        else:
            updated += 1

    return created, updated


def sync_roles_from_sling(client):
    """Sync roles from Sling."""
    from sling_client import map_role_from_sling

    roles = client.fetch_roles()
    created = updated = 0

    for sling_role in roles:
        mapped = map_role_from_sling(sling_role)
        role, was_created = Role.objects.update_or_create(
            sling_id=mapped["sling_id"],
            defaults={"title": mapped["title"]}
        )
        if was_created:
            created += 1
        else:
            updated += 1

    return created, updated
```

## Usage

### Manual Sync

Test the connection:

```bash
python manage.py test_sling_connection
```

Create a management command for manual sync:

```bash
python manage.py sync_sling --window-hours 48
```

### Automated Daily Sync

Once Celery is configured, the sync will run automatically at 2:00 AM daily.

Monitor with Celery Flower:

```bash
celery -A config.celery_app flower
# Open http://localhost:5555
```

### Conflict Resolution

#### Via Django Admin

1. Go to `/admin/integrations/slingconflict/`
2. Filter by "Unresolved"
3. Review conflicts
4. Use batch actions:
   - "Keep Local Values" - Keep your current data
   - "Use Sling Values" - Update to Sling data
   - "Dismiss" - Mark as resolved without changes

#### Via Custom UI (Optional)

If you want a custom conflict resolution UI:

1. Copy `views.py` and customize
2. Copy `urls.py` and include in your project
3. Create templates (see hr_guru project for examples)

## Field Mapping Customization

By default, these fields are synced from Sling:

- `first_name` ← Sling `name` or `preferredName` or `legalName`
- `last_name` ← Sling `lastname`
- `email` ← Sling `email`
- `is_active` ← Sling `active`
- `termination_date` ← Sling `deactivatedAt` (if inactive)

**Fields NOT synced from Sling** (you must manage manually):

- Hire date
- Address
- Phone number
- Pay rate/salary (Sling doesn't provide compensation data)
- Manager relationships (Sling doesn't provide org chart data)

To customize field mappings, create your own mapping functions based on `sling_client.utils`.

## Email Notifications

The sync task sends email summaries to HR managers. Configure recipients in `tasks.py`:

```python
# tasks.py - send_sync_summary_email()
hr_users = User.objects.filter(
    role__in=["ADMIN", "HR_MANAGER"]  # Adjust to your role system
).values_list("email", flat=True)
```

Create email template at `integrations/templates/integrations/emails/sling_sync_summary.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Sling Sync Summary</title>
</head>
<body>
    <h1>Sling Sync Summary</h1>

    <h2>Statistics</h2>
    <ul>
        <li>Duration: {{ stats.duration|floatformat:1 }} seconds</li>
        <li>Employees Updated: {{ stats.employees_updated }}</li>
        <li>Conflicts Created: {{ stats.conflicts_created }}</li>
        <li>Errors: {{ stats.errors|length }}</li>
    </ul>

    {% if stats.conflicts_created > 0 %}
    <h2>⚠️ Conflicts Detected</h2>
    <p>Please review conflicts in the admin:</p>
    <p><a href="{{ request.scheme }}://{{ request.get_host }}{{ admin_url }}integrations/slingconflict/?resolved__exact=0">
        View Unresolved Conflicts
    </a></p>
    {% endif %}

    {% if stats.errors %}
    <h2>❌ Errors</h2>
    <ul>
        {% for error in stats.errors %}
        <li>{{ error }}</li>
        {% endfor %}
    </ul>
    {% endif %}
</body>
</html>
```

## Troubleshooting

### "No API key found"

Set `SLING_API_KEY` in your environment or settings.

### "Temporarily unavailable" when creating employees

This is a known Sling API limitation. Create employees in Sling web interface first, then sync.

### Conflicts not appearing in admin

Check:
1. `SlingConflict.employee` ForeignKey points to your Employee model
2. Search fields in admin match your Employee model fields
3. Conflicts are being created (check database directly)

### Sync task not running

Check:
1. Celery worker is running: `celery -A config.celery_app worker -l info`
2. Celery beat is running: `celery -A config.celery_app beat -l info`
3. Task is in beat schedule: Check Celery logs

### Employee fields not updating

Check:
1. Field mapping in `update_employee_from_sling()`
2. Conflict detection is not blocking updates
3. Employee model has the fields you're trying to update

## Best Practices

### 1. Initial Import

For the first import of all employees:

```python
from sling_client import SlingAPIClient
from integrations.sync_helpers import sync_departments_from_sling, sync_roles_from_sling

client = SlingAPIClient()

# 1. Sync departments and roles first
sync_departments_from_sling(client)
sync_roles_from_sling(client)

# 2. Import all employees
sling_employees = client.fetch_employees()
for sling_emp in sling_employees:
    # Create Employee records with sling_id
    # Map department and position relationships
    pass
```

### 2. Conflict Resolution Workflow

1. **Daily**: Automated sync runs, creates conflict records
2. **Morning**: HR checks dashboard for conflict alert
3. **Review**: HR reviews each conflict in admin
4. **Decide**: Keep local OR use Sling OR merge manually
5. **Resolve**: Mark conflict as resolved

### 3. Data Ownership

- **Sling is Source of Truth for**: Names, email, active status, department, position
- **Your System is Source of Truth for**: Pay rate, hire date, manager, address, phone

### 4. Performance

- Use `select_related()` and `prefetch_related()` when querying conflicts
- Index `sling_id` field on Employee model
- Run sync during off-hours (2 AM)
- Limit sync window (`--window-hours 48`) to reduce API calls

## Support

For issues specific to this integration:
1. Check this README
2. Review example code in this directory
3. Contact platform team

For Sling API issues:
- [Sling API Documentation](https://support.getsling.com)
- [API Support](mailto:support@getsling.com)
```
