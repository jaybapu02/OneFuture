from django.contrib.auth.models import User
from django.db import models


class TrainerProfile(models.Model):
    """Profile extending Django's User model with trainer-specific data."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profile"
    )
    employee_id = models.CharField(max_length=30, unique=True)
    full_name = models.CharField(max_length=120)
    phone_number = models.CharField(max_length=20, blank=True)
    profile_photo = models.ImageField(
        upload_to="profiles/", blank=True, null=True
    )
    designation = models.CharField(max_length=120, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name
