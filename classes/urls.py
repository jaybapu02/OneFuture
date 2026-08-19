from django.urls import path

from . import views

app_name = "classes"

urlpatterns = [
    path("", views.class_list, name="class_list"),
    path("create/", views.class_create, name="class_create"),
    path("<int:pk>/edit/", views.class_edit, name="class_edit"),
    path("<int:pk>/toggle/", views.class_toggle, name="class_toggle"),
    path("subjects/", views.subject_list, name="subject_list"),
    path("subjects/create/", views.subject_create, name="subject_create"),
    path("subjects/<int:pk>/edit/", views.subject_edit, name="subject_edit"),
    path("subjects/<int:pk>/toggle/", views.subject_toggle, name="subject_toggle"),
]
