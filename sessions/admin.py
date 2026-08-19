from django.contrib import admin

from .models import Session


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "school",
        "school_class",
        "subject",
        "session_number",
        "trainer",
        "students_present",
        "total_students",
        "students_absent",
        "location",
        "topic_taught",
    )
    list_filter = ("subject", "school", "location", "date")
    search_fields = (
        "school_class__name",
        "subject__name",
        "trainer__full_name",
        "topic_taught",
    )
    date_hierarchy = "date"
    list_select_related = ("trainer", "school", "school_class", "subject")
    raw_id_fields = ("trainer", "timetable", "school", "school_class", "subject")
    readonly_fields = (
        "session_number",
        "created_at",
        "updated_at",
    )
