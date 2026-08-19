from django.contrib import admin

from .models import SchoolClass, Subject


@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ("name", "section", "grade", "is_active", "created_at")
    list_filter = ("is_active", "grade")
    search_fields = ("name", "section")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
