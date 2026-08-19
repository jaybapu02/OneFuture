from django.db import models
from django.db.models import Q

from classes.models import SchoolClass, Subject
from trainers.models import TrainerProfile

DAYS_OF_WEEK = [
    ("Monday", "Monday"),
    ("Tuesday", "Tuesday"),
    ("Wednesday", "Wednesday"),
    ("Thursday", "Thursday"),
    ("Friday", "Friday"),
    ("Saturday", "Saturday"),
    ("Sunday", "Sunday"),
]


class Timetable(models.Model):
    """A recurring weekly slot: which trainer teaches which class/subject when."""

    trainer = models.ForeignKey(
        TrainerProfile, on_delete=models.CASCADE, related_name="timetable"
    )
    school_class = models.ForeignKey(
        SchoolClass, on_delete=models.CASCADE, related_name="timetable"
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="timetable"
    )
    day_of_week = models.CharField(max_length=9, choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(max_length=60, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["day_of_week", "start_time"]
        indexes = [
            models.Index(fields=["trainer", "day_of_week"]),
            models.Index(fields=["school_class", "day_of_week"]),
            models.Index(fields=["day_of_week", "start_time"]),
        ]

    def __str__(self):
        return (
            f"{self.get_day_of_week_display()} {self.start_time:%H:%M} "
            f"{self.school_class} · {self.subject}"
        )

    def overlaps(self, other):
        """True when this entry overlaps another on the same day."""
        return (
            other.pk != self.pk
            and other.day_of_week == self.day_of_week
            and other.is_active
            and self.is_active
            and other.start_time < self.end_time
            and self.start_time < other.end_time
        )

    def trainer_conflicts(self):
        """Other active entries for the same trainer on the same day that overlap."""
        return (
            Timetable.objects.filter(
                trainer=self.trainer, day_of_week=self.day_of_week, is_active=True
            )
            .exclude(pk=self.pk)
            .filter(
                Q(start_time__lt=self.end_time) & Q(end_time__gt=self.start_time)
            )
        )

    def class_conflicts(self):
        """Other active entries for the same class on the same day that overlap."""
        return (
            Timetable.objects.filter(
                school_class=self.school_class,
                day_of_week=self.day_of_week,
                is_active=True,
            )
            .exclude(pk=self.pk)
            .filter(
                Q(start_time__lt=self.end_time) & Q(end_time__gt=self.start_time)
            )
        )
