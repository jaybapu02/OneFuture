from django.contrib import admin

from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "trainer",
        "school_class",
        "subject",
        "date",
        "priority",
        "status",
    )
    list_filter = ("status", "priority", "subject")
    search_fields = ("title", "trainer__full_name", "school_class__name")
    date_hierarchy = "date"
    list_select_related = ("trainer", "school_class", "subject")
    raw_id_fields = ("trainer", "timetable", "school_class", "subject")
    readonly_fields = ("created_at", "updated_at")
