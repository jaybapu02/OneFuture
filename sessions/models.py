from django.core.exceptions import ValidationError
from django.db import models, transaction

from classes.models import SchoolClass, Subject
from timetable.models import Timetable
from trainers.models import TrainerProfile


class Session(models.Model):
    """A completed teaching session (post-class report)."""

    trainer = models.ForeignKey(
        TrainerProfile, on_delete=models.CASCADE, related_name="sessions"
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
    session_number = models.PositiveIntegerField()
    date = models.DateField(db_index=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    students_present = models.IntegerField(default=0)
    topic_taught = models.TextField()
    activity = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Session"
        ordering = ["-date", "-start_time", "-session_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["school_class", "subject", "session_number"],
                name="unique_session_number_per_class_subject",
            )
        ]
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
      generation for that class. The database unique constraint
      (school_class, subject, session_number) acts as a backstop.
    """
    with transaction.atomic():
        SchoolClass.objects.select_for_update().get(pk=school_class.pk)
        last = (
            Session.objects.filter(school_class=school_class, subject=subject)
            .order_by("-session_number")
            .values_list("session_number", flat=True)
            .first()
        )
        return (last + 1) if last else 1
