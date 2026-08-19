from django.contrib import admin

from .models import Timetable


@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    list_display = (
        "trainer",
        "school_class",
        "subject",
        "day_of_week",
        "start_time",
        "end_time",
        "room",
        "is_active",
    )
    list_filter = ("day_of_week", "is_active", "subject")
    search_fields = (
        "trainer__full_name",
        "school_class__name",
        "subject__name",
        "room",
    )
    list_select_related = ("trainer", "school_class", "subject")
    autocomplete_fields = ()
    raw_id_fields = ("trainer", "school_class", "subject")
    readonly_fields = ("created_at", "updated_at")
