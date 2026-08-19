from django.urls import path

from . import views

app_name = "trainers"

urlpatterns = [
    path("", views.trainer_list, name="trainer_list"),
    path("create/", views.trainer_create, name="trainer_create"),
    path("<int:pk>/edit/", views.trainer_edit, name="trainer_edit"),
    path("<int:pk>/toggle/", views.trainer_toggle, name="trainer_toggle"),
    path("schools/", views.school_list, name="school_list"),
    path("schools/create/", views.school_create, name="school_create"),
    path("schools/<int:pk>/edit/", views.school_edit, name="school_edit"),
    path("schools/<int:pk>/toggle/", views.school_toggle, name="school_toggle"),
]
