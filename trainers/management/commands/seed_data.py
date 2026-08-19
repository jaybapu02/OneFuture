"""
Seed the application with the actual school, trainer and weekly timetable.

Usage:
    python manage.py seed_data

This seeds only real data — nothing is fabricated:

* School : BMC Bagurai School, Bhadrak (from the actual Google Sheet)
* Trainer: Jaychandra Dash (the trainer named in the Google Sheet)
* Classes: Class 3 to Class 8
* Subject: Artificial Intelligence (the classes in the Google Sheet are AI)
* Weekly timetable: the actual 12 recurring entries (Periods 4-7, Mon-Fri)

No mock tasks or sessions are created — the dashboard starts with real
empty states.

Safe to re-run: it refuses to run if a trainer already exists.
"""
import datetime

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from classes.models import SchoolClass, Subject
from timetable.models import Timetable
from trainers.models import School, TrainerProfile

SCHOOL = {
    "name": "BMC Bagurai School",
    "address": "Bhadrak, Odisha",
}

TRAINER = {
    "username": "jaychandra",
    "password": "Jay@123",
    "employee_id": "EMP-001",
    "full_name": "Jaychandra Dash",
    "phone_number": "",
    "designation": "Trainer",
    "joining_date": "2026-01-01",
}

SUBJECTS = ["Artificial Intelligence"]

# Actual weekly timetable (source of truth, 12 classes Mon-Fri).
# (day_of_week, period, class_grade, start_time, end_time)
WEEKLY_TIMETABLE = [
    ("Monday", 4, 7, "12:30", "13:15"),
    ("Monday", 6, 5, "14:00", "14:40"),
    ("Monday", 7, 8, "15:20", "16:00"),
    ("Tuesday", 6, 3, "14:40", "15:20"),
    ("Tuesday", 7, 6, "15:20", "16:00"),
    ("Wednesday", 5, 4, "14:00", "14:40"),
    ("Wednesday", 6, 8, "14:40", "15:20"),
    ("Wednesday", 7, 3, "15:20", "16:00"),
    ("Thursday", 5, 7, "14:00", "14:40"),
    ("Thursday", 7, 5, "15:20", "16:00"),
    ("Friday", 6, 4, "14:40", "15:20"),
    ("Friday", 7, 6, "15:20", "16:00"),
]


class Command(BaseCommand):
    help = (
        "Seed the actual school, trainer and 12-entry weekly timetable "
        "(BMC Bagurai School / Jaychandra Dash)."
    )

    def handle(self, *args, **options):
        if TrainerProfile.objects.exists() or School.objects.exists():
            self.stdout.write(
                self.style.WARNING(
                    "Data already exists. Skipping (run on a fresh database to reseed)."
                )
            )
            return

        school = School.objects.create(
            name=SCHOOL["name"], address=SCHOOL["address"]
        )
        self.stdout.write(f"School: {school}")

        user = User.objects.create_user(
            username=TRAINER["username"],
            password=TRAINER["password"],
            is_active=True,
        )
        trainer = TrainerProfile.objects.create(
            user=user,
            school=school,
            employee_id=TRAINER["employee_id"],
            full_name=TRAINER["full_name"],
            phone_number=TRAINER["phone_number"],
            designation=TRAINER["designation"],
            joining_date=datetime.date.fromisoformat(TRAINER["joining_date"]),
        )
        self.stdout.write(f"Trainer: {trainer.full_name} ({trainer.user.username})")

        class_map = {}
        for grade in range(3, 9):
            class_obj = SchoolClass.objects.create(
                name=f"Class {grade}", section="", grade=grade
            )
            class_map[grade] = class_obj

        subject = None
        for name in SUBJECTS:
            subject = Subject.objects.create(name=name)
        self.stdout.write(f"Subject: {subject}")

        for day, period, grade, start, end in WEEKLY_TIMETABLE:
            Timetable.objects.create(
                trainer=trainer,
                school=school,
                school_class=class_map[grade],
                subject=subject,
                day_of_week=day,
                period=period,
                start_time=datetime.time.fromisoformat(start),
                end_time=datetime.time.fromisoformat(end),
                source="EXCEL",
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {len(WEEKLY_TIMETABLE)} weekly timetable entries "
                f"(Monday=3, Tuesday=2, Wednesday=3, Thursday=2, Friday=2)."
            )
        )
        self.stdout.write(
            self.style.SUCCESS("Seed complete — no mock tasks or sessions created.")
        )
