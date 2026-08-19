from django.contrib import admin

from .models import TrainerProfile


@admin.register(TrainerProfile)
class TrainerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "employee_id",
        "user",
        "phone_number",
        "designation",
        "is_active",
        "joining_date",
    )
    list_filter = ("is_active", "designation", "joining_date")
    search_fields = ("full_name", "employee_id", "phone_number", "user__username")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("user",)
