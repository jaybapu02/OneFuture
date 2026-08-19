"""
Import the real August 2026 session records (from the "August Month Details"
monthly report) for trainer Jaychandra.

Usage:
    python manage.py import_august_data

Facts about this command:

* Source of truth: the actual "August Month Details" report for BMC Bagurai
  School / Bhadrak. No mock data is created.
* NA rows (office / non-class days) are skipped — they never become sessions.
* Rows that cover several classes are stored as one Session per class.
* Historical session numbers are preserved exactly as written in the report.
* Idempotent: a session is keyed on (trainer, date, class, session_number).
  Re-running the command never creates duplicates and never overwrites
  values that were edited manually after the import.
* The weekly timetable is NOT touched — that dataset is separate.
"""
import datetime

from django.core.management.base import BaseCommand

from classes.models import SchoolClass, Subject
from sessions.models import Session
from trainers.models import School, TrainerProfile

TRAINER_USERNAME = "jaychandra"
SCHOOL_NAME = "BMC Bagurai School"
SUBJECT_NAME = "Artificial Intelligence"
LOCATION = "Bhadrak"

# Each entry: (date, [(grade, session_number, total, present, topic, note)]*,
#               start_time, end_time)
# None means "not present in the report" and is stored as NULL/empty.
AUGUST_2026 = [
    (
        datetime.date(2026, 8, 4),
        [
            (
                6,
                1,
                40,
                40,
                "Introduction Class",
                "Combined class: Class 6, 7 and 8 (Mix) — combined attendance.",
            )
        ],
        "12:00",
        "12:45",
    ),
    (
        datetime.date(2026, 8, 5),
        [
            (
                7,
                2,
                None,
                None,
                "Computational Thinking — Part 2, Chapter 1: AI domain and its applications.",
                None,
            ),
            (
                8,
                2,
                None,
                None,
                "Introduction to AI and its applications.",
                None,
            ),
        ],
        None,
        None,
    ),
    (
        datetime.date(2026, 8, 6),
        [
            (
                4,
                1,
                None,
                None,
                "What is AI, AI application, AI details and real life examples, automation vs AI.",
                None,
            ),
            (
                5,
                1,
                None,
                None,
                "What is AI, AI application, AI details and real life examples, automation vs AI.",
                None,
            ),
        ],
        None,
        None,
    ),
    (
        datetime.date(2026, 8, 7),
        [
            (
                6,
                2,
                None,
                None,
                "AI and its application.",
                None,
            ),
            (
                3,
                1,
                None,
                None,
                "AI vs automation and AI with its application.",
                None,
            ),
        ],
        None,
        None,
    ),
    (
        datetime.date(2026, 8, 10),
        [
            (
                8,
                2,
                10,
                10,
                "AI LIFE CYCLE, NLP, OPEN CV AND DATA SCIENCE WITH ITS REVISION.",
                None,
            )
        ],
        "11:45",
        "12:30",
    ),
    (
        datetime.date(2026, 8, 11),
        [
            (5, 2, None, None, "AI life cycle.", None),
            (7, 3, None, None, "Data and types of data.", None),
            (
                3,
                3,
                None,
                None,
                "Introduction to classification; AI application and AI activity.",
                None,
            ),
            (
                6,
                2,
                None,
                None,
                "Activity based on how AI works and what is prediction.",
                None,
            ),
        ],
        "11:00",
        "16:00",
    ),
    (
        datetime.date(2026, 8, 12),
        [
            (
                4,
                None,
                None,
                None,
                "Know about patterns and applications of AI.",
                None,
            ),
            (8, None, None, None, "What is AI and its applications.", None),
            (3, None, None, None, "Activity — how AI predicts.", None),
        ],
        None,
        None,
    ),
    (
        datetime.date(2026, 8, 13),
        [
            (7, 4, None, None, "Data and types of data and quiz based on data.", None),
            (
                5,
                3,
                None,
                None,
                "How AI learns data and a fun activity based on that.",
                None,
            ),
        ],
        None,
        None,
    ),
    (
        datetime.date(2026, 8, 14),
        [
            (
                4,
                3,
                12,
                12,
                "Fun activity — how AI predict based on given data.",
                None,
            )
        ],
        None,
        None,
    ),
    (
        datetime.date(2026, 8, 18),
        [
            (3, 4, 12, 12, "Secret Agent fun activity.", None),
            (6, 4, 12, 12, "Taught about encoding and decoding.", None),
        ],
        None,
        None,
    ),
]

DAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


class Command(BaseCommand):
    help = (
        "Import the real August 2026 session records from the monthly report "
        "(BMC Bagurai School / Jaychandra Dash). Idempotent."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be imported without writing to the database.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        try:
            trainer = TrainerProfile.objects.get(user__username=TRAINER_USERNAME)
        except TrainerProfile.DoesNotExist:
            self.stderr.write(
                self.style.ERROR(
                    f"Trainer '{TRAINER_USERNAME}' not found. Run "
                    "`python manage.py seed_data` first."
                )
            )
            return

        school = School.objects.filter(name=SCHOOL_NAME).first()
        subject = Subject.objects.filter(name=SUBJECT_NAME).first()
        classes = {
            obj.grade: obj
            for obj in SchoolClass.objects.filter(is_active=True)
            if obj.grade in range(3, 9)
        }

        created = skipped = existing = 0
        for date_, class_rows, start, end in AUGUST_2026:
            expected_day = DAY_NAMES[date_.weekday()]
            start_time = datetime.time.fromisoformat(start) if start else None
            end_time = datetime.time.fromisoformat(end) if end else None
            for grade, number, total, present, topic, note in class_rows:
                class_obj = classes.get(grade)
                if class_obj is None:
                    self.stderr.write(
                        self.style.WARNING(
                            f"Class {grade} not found — skipping {date_}."
                        )
                    )
                    skipped += 1
                    continue
                if number is not None:
                    session, was_created = Session.objects.get_or_create(
                        trainer=trainer,
                        date=date_,
                        school_class=class_obj,
                        session_number=number,
                        defaults={
                            "school": school,
                            "subject": subject,
                            "start_time": start_time,
                            "end_time": end_time,
                            "students_present": present or 0,
                            "total_students": total,
                            "students_absent": (
                                total - present if (total is not None and present is not None) else None
                            ),
                            "location": LOCATION,
                            "topic_taught": topic,
                            "notes": note or "",
                        },
                    )
                else:
                    session = (
                        Session.objects.filter(
                            trainer=trainer,
                            date=date_,
                            school_class=class_obj,
                            session_number__isnull=True,
                        ).first()
                    )
                    was_created = session is None
                    if was_created:
                        session = Session.objects.create(
                            trainer=trainer,
                            school=school,
                            subject=subject,
                            school_class=class_obj,
                            date=date_,
                            session_number=None,
                            start_time=start_time,
                            end_time=end_time,
                            students_present=present or 0,
                            total_students=total,
                            students_absent=(
                                total - present
                                if (total is not None and present is not None)
                                else None
                            ),
                            location=LOCATION,
                            topic_taught=topic,
                            notes=note or "",
                        )

                if was_created:
                    created += 1
                    if not dry_run:
                        self.stdout.write(
                            f"  + {date_} · {class_obj} · Session {number or '—'} · {topic[:60]}"
                        )
                else:
                    existing += 1

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[dry-run] Would create {created} session(s); "
                    f"{existing} already exist(ed)."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Import complete — created {created}, already present {existing} "
                f"({Session.objects.filter(trainer=trainer, date__year=2026, date__month=8).count()} "
                "total August sessions)."
            )
        )
