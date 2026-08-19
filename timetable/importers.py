"""Persisting parsed timetable rows into the database.

An uploaded weekly timetable belongs to the logged-in trainer and their
school — the trainer is never asked to pick a trainer per cell.
"""
from classes.models import SchoolClass, Subject
from timetable.models import Timetable

DEFAULT_SUBJECT_NAME = "Artificial Intelligence"


def get_default_subject():
    """The subject recorded in the actual timetable data (AI classes)."""
    return Subject.objects.filter(
        name=DEFAULT_SUBJECT_NAME, is_active=True
    ).first()


def import_timetable_rows(profile, rows, mode="replace"):
    """Create recurring Timetable entries from parsed rows.

    ``mode``:
      replace — deactivate the trainer's existing EXCEL entries (historical
      sessions/tasks keep their links) and create the new weekly timetable.
      update  — same behaviour (the weekly timetable is a single source of
      truth, so an upload always replaces the current weekly schedule).

    Returns the number of entries created.
    """
    school = profile.school
    if school is None:
        raise ValueError(
            "Trainer has no school assigned. Contact the administrator."
        )

    if mode == "replace":
        Timetable.objects.filter(
            trainer=profile, source="EXCEL", is_active=True
        ).update(is_active=False)

    subject = get_default_subject()
    created = 0
    for row in rows:
        school_class, _ = SchoolClass.objects.get_or_create(
            name=row["class_name"],
            section="",
            defaults={"grade": row["grade"]},
        )
        Timetable.objects.create(
            trainer=profile,
            school=school,
            school_class=school_class,
            subject=subject,
            day_of_week=row["day"],
            period=row["period"],
            start_time=row["start_time"],
            end_time=row["end_time"],
            source="EXCEL",
        )
        created += 1
    return created
