from django.urls import path

from . import views

app_name = "timetable"

urlpatterns = [
    path("", views.my_timetable, name="my_timetable"),
    path("upload/", views.upload_timetable, name="upload_timetable"),
    path("download-template/", views.download_template, name="download_template"),
    path("assign/", views.assign_manual_class, name="assign_manual_class"),
    path(
        "manual/<int:pk>/delete/",
        views.manual_class_delete,
        name="manual_class_delete",
    ),
    path("entry/<int:pk>/", views.class_detail, name="class_detail"),
    path(
        "entry/<int:pk>/remove-date/",
        views.occurrence_remove_date,
        name="occurrence_remove_date",
    ),
    path(
        "entry/<int:pk>/remove-weekly/",
        views.recurring_remove_weekly,
        name="recurring_remove_weekly",
    ),
    path("manage/", views.manage_list, name="manage_list"),
    path("manage/create/", views.manage_create, name="manage_create"),
    path("manage/<int:pk>/edit/", views.manage_edit, name="manage_edit"),
    path("manage/<int:pk>/delete/", views.manage_delete, name="manage_delete"),
]
