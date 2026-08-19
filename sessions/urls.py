from django.urls import path

from . import views

app_name = "sessions"

urlpatterns = [
    path("", views.session_list, name="session_list"),
    path("complete/<int:timetable_id>/", views.session_complete, name="session_complete"),
    path(
        "complete/manual/<int:manual_id>/",
        views.session_complete_manual,
        name="session_complete_manual",
    ),
    path("<int:pk>/", views.session_detail, name="session_detail"),
    path("<int:pk>/edit/", views.session_edit, name="session_edit"),
    path("<int:pk>/delete/", views.session_delete, name="session_delete"),
]