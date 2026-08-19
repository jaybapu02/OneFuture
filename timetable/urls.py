from django.urls import path

from . import views

app_name = "timetable"

urlpatterns = [
    path("", views.my_timetable, name="my_timetable"),
    path("manage/", views.manage_list, name="manage_list"),
    path("manage/create/", views.manage_create, name="manage_create"),
    path("manage/<int:pk>/edit/", views.manage_edit, name="manage_edit"),
    path("manage/<int:pk>/delete/", views.manage_delete, name="manage_delete"),
]