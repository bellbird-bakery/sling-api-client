"""
URL Patterns for Sling Integration (OPTIONAL)

This file provides example URL patterns for Sling integration views.
These are completely optional - you may not need web views at all.

If you want a UI for conflict resolution, copy and adapt these patterns.

USAGE:
1. Copy to your Django app's urls.py
2. Include in your project's main urls.py:

    # project/urls.py
    urlpatterns = [
        path("integrations/", include("yourapp.urls", namespace="integrations")),
    ]

3. Create corresponding views (see views.py example)
"""

from django.urls import path

# ⚠️ CUSTOMIZE: Import your views
# from . import views

app_name = "integrations"

urlpatterns = [
    # Conflict management URLs (optional)
    # path(
    #     "conflicts/",
    #     views.ConflictListView.as_view(),
    #     name="conflict_list",
    # ),
    # path(
    #     "conflicts/<int:pk>/resolve/",
    #     views.ConflictResolveView.as_view(),
    #     name="conflict_resolve",
    # ),
    # path(
    #     "conflicts/batch-resolve/",
    #     views.ConflictBatchResolveView.as_view(),
    #     name="conflict_batch_resolve",
    # ),

    # Sling push URLs (if you want to push employees to Sling)
    # path(
    #     "sling/push-employee/<int:pk>/",
    #     views.PushEmployeeToSlingView.as_view(),
    #     name="push_employee_to_sling",
    # ),
]

# Note: For most use cases, you can manage everything through:
# 1. Django Admin (for conflict resolution)
# 2. Management commands (for syncing)
# 3. Celery tasks (for automated syncing)
#
# Web views are optional and mainly useful if you want custom UI
