from django.contrib import admin

from .models import ManualClass, ScheduleException, Timetable, TimetableOccurrenceRemoval


@admin.register(Timetable)
class TimetableAdmin(admin.ModelAdmin):
    list_display = (
        "trainer",
        "school",
        "school_class",
        "subject",
        "day_of_week",
        "period",
        "start_time",
        "end_time",
        "source",
        "is_active",
    )
    list_filter = ("day_of_week", "period", "source", "is_active", "school")
    search_fields = (
        "trainer__full_name",
        "school_class__name",
        "subject__name",
        "room",
    )
    list_select_related = ("trainer", "school", "school_class", "subject")
    raw_id_fields = ("trainer", "school", "school_class", "subject")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ManualClass)
class ManualClassAdmin(admin.ModelAdmin):
    list_display = (
        "trainer",
        "school",
        "school_class",
        "subject",
        "date",
        "period",
        "start_time",
        "end_time",
        "is_active",
    )
    list_filter = ("is_active", "school", "date")
    search_fields = ("trainer__full_name", "school_class__name")
    list_select_related = ("trainer", "school", "school_class", "subject")
    raw_id_fields = ("trainer", "school", "school_class", "subject")
    readonly_fields = ("created_at", "updated_at")


@admin.register(TimetableOccurrenceRemoval)
class TimetableOccurrenceRemovalAdmin(admin.ModelAdmin):
    list_display = ("timetable", "date", "created_at")
    list_filter = ("date",)
    raw_id_fields = ("timetable",)


@admin.register(ScheduleException)
class ScheduleExceptionAdmin(admin.ModelAdmin):
    list_display = ("trainer", "school", "date", "type", "timetable", "created_by", "created_at")
    list_filter = ("type", "date", "school")
    search_fields = ("trainer__full_name", "reason")
    list_select_related = ("trainer", "school", "timetable", "created_by")
    raw_id_fields = ("trainer", "school", "timetable", "created_by")
    readonly_fields = ("created_at",)