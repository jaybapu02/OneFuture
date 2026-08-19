from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from classes.models import SchoolClass, Subject
from timetable.models import Timetable
from trainers.models import TrainerProfile, School


class Task(models.Model):
    """A task a trainer assigns to themselves for a timetabled class."""

    class Priority(models.TextChoices):
        LOW = "Low", "Low"
        MEDIUM = "Medium", "Medium"
        HIGH = "High", "High"

    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        IN_PROGRESS = "In Progress", "In Progress"
        COMPLETED = "Completed", "Completed"

    trainer = models.ForeignKey(
        TrainerProfile, on_delete=models.CASCADE, related_name="tasks"
    )
    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name="tasks",
        null=True, blank=True,
    )
    timetable = models.ForeignKey(
        Timetable,
        on_delete=models.SET_NULL,
        related_name="tasks",
        null=True,
        blank=True,
    )
    school_class = models.ForeignKey(
        SchoolClass, on_delete=models.CASCADE, related_name="tasks"
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="tasks"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    date = models.DateField(db_index=True)
    period = models.PositiveSmallIntegerField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM
    )
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date", "start_time"]
        indexes = [
            models.Index(fields=["trainer", "status"]),
            models.Index(fields=["trainer", "date"]),
            models.Index(fields=["school_class"]),
            models.Index(fields=["subject"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.school_class})"

    def clean(self):
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValidationError("End time must be after start time.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
