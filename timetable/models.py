from django.db import models
from django.db.models import Q

from classes.models import SchoolClass, Subject
from trainers.models import TrainerProfile, School

DAYS_OF_WEEK = [
    ("Monday", "Monday"),
    ("Tuesday", "Tuesday"),
    ("Wednesday", "Wednesday"),
    ("Thursday", "Thursday"),
    ("Friday", "Friday"),
    ("Saturday", "Saturday"),
    ("Sunday", "Sunday"),
]

SOURCE_CHOICES = [
    ("EXCEL", "Excel Upload"),
    ("MANUAL", "Manual"),
]


class Timetable(models.Model):
    """A recurring weekly slot: which trainer teaches which class/subject when.

    This is the weekly source of truth. It repeats every week; today's classes
    are derived from the current day of week + these entries. It is never used
    to store 52 individual weeks.
    """

    trainer = models.ForeignKey(
        TrainerProfile, on_delete=models.CASCADE, related_name="timetable"
    )
    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name="timetable",
        null=True, blank=True,
    )
    school_class = models.ForeignKey(
        SchoolClass, on_delete=models.CASCADE, related_name="timetable"
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.SET_NULL, related_name="timetable",
        null=True, blank=True,
    )
    day_of_week = models.CharField(max_length=9, choices=DAYS_OF_WEEK)
    period = models.PositiveSmallIntegerField(null=True, blank=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(max_length=60, blank=True)
    source = models.CharField(
        max_length=10, choices=SOURCE_CHOICES, default="MANUAL"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["day_of_week", "period", "start_time"]
        indexes = [
            models.Index(fields=["trainer", "day_of_week"]),
            models.Index(fields=["school_class", "day_of_week"]),
            models.Index(fields=["day_of_week", "start_time"]),
            models.Index(fields=["trainer", "school", "is_active"]),
        ]

    def __str__(self):
        return (
            f"{self.get_day_of_week_display()} P{self.period or '-'} "
            f"{self.start_time:%H:%M} {self.school_class} · {self.subject or '-'}"
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


class TimetableOccurrenceRemoval(models.Model):
    """A recurring timetable entry removed for ONE specific date only.

    Used by "Remove for this date": the recurring rule stays untouched, only
    that single occurrence is suppressed.
    """

    timetable = models.ForeignKey(
        Timetable, on_delete=models.CASCADE, related_name="occurrence_removals"
    )
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date"]
        constraints = [
            models.UniqueConstraint(
                fields=["timetable", "date"],
                name="unique_occurrence_removal_per_timetable_date",
            )
        ]

    def __str__(self):
        return f"{self.timetable} removed on {self.date}"


class ManualClass(models.Model):
    """A one-off class on a specific date, added by the trainer.

    This does NOT modify the recurring weekly timetable.
    """

    trainer = models.ForeignKey(
        TrainerProfile, on_delete=models.CASCADE, related_name="manual_classes"
    )
    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name="manual_classes",
        null=True, blank=True,
    )
    school_class = models.ForeignKey(
        SchoolClass, on_delete=models.CASCADE, related_name="manual_classes"
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.SET_NULL, related_name="manual_classes",
        null=True, blank=True,
    )
    date = models.DateField(db_index=True)
    period = models.PositiveSmallIntegerField(null=True, blank=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    notes = models.CharField(max_length=300, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "period", "start_time"]
        indexes = [
            models.Index(fields=["trainer", "date"]),
            models.Index(fields=["trainer", "school"]),
        ]

    def __str__(self):
        return (
            f"{self.date} P{self.period or '-'} {self.school_class} "
            f"{self.start_time:%H:%M} (Manual)"
        )