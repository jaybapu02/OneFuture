from django.urls import path

from . import views

app_name = "trainers"

urlpatterns = [
    path("", views.trainer_list, name="trainer_list"),
    path("create/", views.trainer_create, name="trainer_create"),
    path("<int:pk>/edit/", views.trainer_edit, name="trainer_edit"),
    path("<int:pk>/toggle/", views.trainer_toggle, name="trainer_toggle"),
]
