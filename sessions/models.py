from django.core.exceptions import ValidationError
from django.db import models, transaction

from classes.models import SchoolClass, Subject
from timetable.models import Timetable
from trainers.models import TrainerProfile, School


class Session(models.Model):
    """A completed teaching session (post-class report)."""

    trainer = models.ForeignKey(
        TrainerProfile, on_delete=models.CASCADE, related_name="sessions"
    )
    school = models.ForeignKey(
        School, on_delete=models.CASCADE, related_name="sessions",
        null=True, blank=True,
    )
    timetable = models.ForeignKey(
        Timetable,
        on_delete=models.SET_NULL,
        related_name="sessions",
        null=True,
        blank=True,
    )
    school_class = models.ForeignKey(
        SchoolClass, on_delete=models.CASCADE, related_name="sessions"
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="sessions"
    )
    session_number = models.PositiveIntegerField(null=True, blank=True)
    date = models.DateField(db_index=True)
    period = models.PositiveSmallIntegerField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    students_present = models.IntegerField(default=0)
    total_students = models.IntegerField(null=True, blank=True)
    students_absent = models.IntegerField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True)
    topic_taught = models.TextField()
    activity = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Session"
        ordering = ["-date", "-start_time", "-session_number"]
        indexes = [
            models.Index(fields=["trainer", "date"]),
            models.Index(fields=["school_class", "subject"]),
            models.Index(fields=["date"]),
        ]

    def __str__(self):
        return f"{self.school_class} / {self.subject} — Session {self.session_number}"

    def clean(self):
        if self.students_present is not None and self.students_present < 0:
            raise ValidationError("Students present cannot be negative.")
        if (
            self.total_students is not None
            and self.students_present is not None
            and self.students_present > self.total_students
        ):
            raise ValidationError(
                "Students present cannot exceed total students."
            )
        if self.topic_taught and not self.topic_taught.strip():
            raise ValidationError("Topic taught cannot be empty.")


def get_next_session_number(school_class, subject):
    """
    Compute the next session number for a class + subject.

    Numbering rule (documented):
    * The next session number is always (highest existing session number for
      this class + subject) + 1.
    * Numbering is independent per class + subject — never global.
    * Deleting a session does NOT renumber historical sessions. If sessions
      1-4 exist and session 3 is deleted, the next number is still 5.
    * Concurrent submissions are safe: the class row is locked with
      select_for_update inside a transaction, which serializes number
      generation for that class. (Historical August records imported from the
      monthly report keep the numbers written in that report and may be
      non-sequential per class, which is why there is no unique database
      constraint on (school_class, subject, session_number).)
    """
    with transaction.atomic():
        SchoolClass.objects.select_for_update().get(pk=school_class.pk)
        last = (
            Session.objects.filter(school_class=school_class, subject=subject)
            .exclude(session_number__isnull=True)
            .order_by("-session_number")
            .values_list("session_number", flat=True)
            .first()
        )
        return (last + 1) if last else 1
