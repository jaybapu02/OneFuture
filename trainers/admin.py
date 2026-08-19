from django.contrib import admin

from .models import School, TrainerProfile


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "address", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "address")
    readonly_fields = ("created_at", "updated_at")


@admin.register(TrainerProfile)
class TrainerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "employee_id",
        "school",
        "user",
        "phone_number",
        "designation",
        "is_active",
        "joining_date",
    )
    list_filter = ("is_active", "designation", "joining_date", "school")
    search_fields = ("full_name", "employee_id", "phone_number", "user__username")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("user", "school")