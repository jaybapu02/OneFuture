"""
Root URL configuration for the TrainerHub project.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from accounts.views import dashboard

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="dashboard", permanent=False)),
    path("dashboard/", dashboard, name="dashboard"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("trainers/", include("trainers.urls")),
    path("classes/", include("classes.urls")),
    path("timetable/", include("timetable.urls")),
    path("tasks/", include("tasks.urls")),
    path("sessions/", include("sessions.urls")),
    path("reports/", include("reports.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
