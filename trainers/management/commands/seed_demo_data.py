"""
Seed demo data for TrainerHub.

Usage:
    python manage.py seed_demo_data

Creates an admin, demo trainers, classes, subjects, a full weekly timetable,
tasks and session history. Safe to re-run: it refuses to run if data exists.

Demo logins (documented in README):
    admin   / Admin@123
    jay     / Jay@123
    priya   / Priya@123
    rahul   / Rahul@123
"""
import datetime

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from classes.models import SchoolClass, Subject
from sessions.models import Session, get_next_session_number
from tasks.models import Task
from timetable.models import Timetable
from trainers.models import TrainerProfile

TRAINERS = [
    {
        "username": "jay",
        "password": "Jay@123",
        "employee_id": "EMP-001",
        "full_name": "Jaychandra",
        "phone_number": "+91 90000 00001",
        "designation": "Senior Trainer",
        "joining_date": "2024-06-01",
    },
    {
        "username": "priya",
        "password": "Priya@123",
        "employee_id": "EMP-002",
        "full_name": "Priya Sharma",
        "phone_number": "+91 90000 00002",
        "designation": "Trainer",
        "joining_date": "2024-08-15",
    },
    {
        "username": "rahul",
        "password": "Rahul@123",
        "employee_id": "EMP-003",
        "full_name": "Rahul Verma",
        "phone_number": "+91 90000 00003",
        "designation": "Junior Trainer",
        "joining_date": "2025-01-10",
    },
]

CLASSES = [
    ("Class 6", "A", 6),
    ("Class 6", "B", 6),
    ("Class 7", "A", 7),
    ("Class 7", "B", 7),
    ("Class 8", "A", 8),
    ("Class 8", "B", 8),
]

SUBJECTS = [
    "Artificial Intelligence",
    "Robotics",
    "Computer Science",
    "Python",
]

TOPICS = [
    "Introduction to Computer Vision",
    "Image classification activity",
    "Machine learning basics",
    "Building a simple chatbot",
    "Sensors and actuators",
    "Robot movement programming",
    "Variables and data types",
    "Loops and conditionals",
    "Functions and modules",
    "Mini project: quiz app",
]

# Schedule: trainer username -> list of (day, start, end, class_idx, subject_idx, room)
SCHEDULE = {
    "jay": [
        ("Monday", "09:00", "10:00", 0, 0, "Lab 1"),
        ("Monday", "10:00", "11:00", 2, 0, "Lab 1"),
        ("Monday", "11:00", "12:00", 4, 1, "Lab 2"),
        ("Tuesday", "09:00", "10:00", 1, 2, "Lab 1"),
        ("Tuesday", "10:00", "11:00", 3, 2, "Lab 1"),
        ("Wednesday", "09:00", "10:00", 0, 0, "Lab 1"),
        ("Wednesday", "11:00", "12:00", 4, 0, "Lab 2"),
        ("Thursday", "09:00", "10:00", 2, 1, "Lab 2"),
        ("Thursday", "10:00", "11:00", 5, 3, "Lab 1"),
        ("Friday", "09:00", "10:00", 0, 2, "Lab 1"),
        ("Friday", "10:00", "11:00", 4, 3, "Lab 2"),
        ("Saturday", "09:00", "10:00", 2, 0, "Lab 1"),
    ],
    "priya": [
        ("Monday", "11:00", "12:00", 1, 1, "Lab 2"),
        ("Monday", "14:00", "15:00", 3, 0, "Lab 1"),
        ("Tuesday", "11:00", "12:00", 0, 3, "Lab 1"),
        ("Tuesday", "14:00", "15:00", 5, 2, "Lab 2"),
        ("Wednesday", "10:00", "11:00", 1, 3, "Lab 2"),
        ("Thursday", "11:00", "12:00", 3, 1, "Lab 2"),
        ("Friday", "11:00", "12:00", 5, 0, "Lab 1"),
        ("Friday", "14:00", "15:00", 2, 3, "Lab 1"),
    ],
    "rahul": [
        ("Monday", "14:00", "15:00", 4, 2, "Lab 2"),
        ("Tuesday", "11:00", "12:00", 4, 3, "Lab 2"),
        ("Tuesday", "14:00", "15:00", 1, 0, "Lab 1"),
        ("Wednesday", "10:00", "11:00", 3, 3, "Lab 1"),
        ("Thursday", "11:00", "12:00", 0, 1, "Lab 2"),
        ("Friday", "14:00", "15:00", 1, 2, "Lab 1"),
    ],
}


class Command(BaseCommand):
    help = "Seed demo data: admin, trainers, classes, subjects, timetable, tasks, sessions."

    def handle(self, *args, **options):
        if TrainerProfile.objects.exists() or SchoolClass.objects.exists():
            self.stdout.write(
                self.style.WARNING(
                    "Data already exists. Skipping (run with a fresh database to reseed)."
                )
            )
            return

        today = timezone.localdate()

        # Admin -------------------------------------------------------------
        admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@trainerhub.local",
            password="Admin@123",
        )
        self.stdout.write(f"Admin created: {admin_user.username}")

        # Classes & subjects -------------------------------------------------
        class_map = {}
        for name, section, grade in CLASSES:
            obj = SchoolClass.objects.create(
                name=name, section=section, grade=grade
            )
            class_map[(name, section)] = obj

        subject_map = {}
        for name in SUBJECTS:
            subject_map[name] = Subject.objects.create(name=name)

        # Trainers ------------------------------------------------------------
        trainer_map = {}
        for data in TRAINERS:
            user = User.objects.create_user(
                username=data["username"],
                password=data["password"],
                is_active=True,
            )
            trainer_map[data["username"]] = TrainerProfile.objects.create(
                user=user,
                employee_id=data["employee_id"],
                full_name=data["full_name"],
                phone_number=data["phone_number"],
                designation=data["designation"],
                joining_date=datetime.date.fromisoformat(data["joining_date"]),
            )

        # Timetable ------------------------------------------------------------
        timetable_map = {}  # (trainer, class, subject, day) -> entry
        for username, slots in SCHEDULE.items():
            trainer = trainer_map[username]
            for day, start, end, class_idx, subject_idx, room in slots:
                name, section, _ = CLASSES[class_idx]
                entry = Timetable.objects.create(
                    trainer=trainer,
                    school_class=class_map[(name, section)],
                    subject=subject_map[SUBJECTS[subject_idx]],
                    day_of_week=day,
                    start_time=datetime.time.fromisoformat(start),
                    end_time=datetime.time.fromisoformat(end),
                    room=room,
                )
                timetable_map[(username, day, start)] = entry
        self.stdout.write(
            f"Timetable: {Timetable.objects.count()} entries created."
        )

        # Tasks ----------------------------------------------------------------
        task_seeds = [
            ("jay", "Complete Chapter 3 activity", "Monday", "09:00",
             "Students will create a simple AI classification activity.", "High"),
            ("jay", "Prepare quiz questions", "Wednesday", "09:00",
             "20 questions on computer vision.", "Medium"),
            ("priya", "Grade Python assignments", "Tuesday", "11:00",
             "", "Medium"),
            ("rahul", "Set up robotics kits", "Thursday", "11:00",
             "Check all sensor kits before class.", "High"),
        ]
        for username, title, day, start, description, priority in task_seeds:
            date = _recent_weekday(today, day)
            if date is None:
                continue
            slot = timetable_map[(username, day, start)]
            Task.objects.create(
                trainer=trainer_map[username],
                timetable=slot,
                school_class=slot.school_class,
                subject=slot.subject,
                title=title,
                description=description,
                date=date,
                start_time=slot.start_time,
                end_time=slot.end_time,
                priority=priority,
                status=Task.Status.PENDING
                if date >= today
                else Task.Status.COMPLETED,
            )
        self.stdout.write(f"Tasks: {Task.objects.count()} created.")

        # Sessions --------------------------------------------------------------
        session_count = 0
        topic_index = 0
        for username, slots in SCHEDULE.items():
            trainer = trainer_map[username]
            for day, start, end, class_idx, subject_idx, room in slots:
                name, section, _ = CLASSES[class_idx]
                school_class = class_map[(name, section)]
                subject = subject_map[SUBJECTS[subject_idx]]
                entry = timetable_map[(username, day, start)]

                for date in _recent_occurrences(today, day, count=4):
                    if date > today:
                        continue
                    start_time = datetime.time.fromisoformat(start)
                    end_time = datetime.time.fromisoformat(end)
                    number = get_next_session_number(school_class, subject)
                    Session.objects.create(
                        trainer=trainer,
                        timetable=entry,
                        school_class=school_class,
                        subject=subject,
                        session_number=number,
                        date=date,
                        start_time=start_time,
                        end_time=end_time,
                        students_present=20 + ((session_count * 3) % 12),
                        topic_taught=TOPICS[topic_index % len(TOPICS)],
                        activity="Group activity with hands-on practice."
                        if session_count % 2 == 0
                        else "",
                        notes="Students participated well."
                        if session_count % 3 == 0
                        else "",
                    )
                    session_count += 1
                    topic_index += 1
        self.stdout.write(f"Sessions: {session_count} created.")

        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully."))


def _recent_weekday(today, weekday_name):
    """Most recent date (<= today) matching the weekday name."""
    target = next(
        (i for i in range(7) if (today - datetime.timedelta(days=i)).strftime("%A") == weekday_name),
        None,
    )
    if target is None:
        return None
    return today - datetime.timedelta(days=target)


def _recent_occurrences(today, weekday_name, count):
    """Last `count` dates (<= today) matching the weekday name, ascending."""
    dates = []
    cursor = today
    while len(dates) < count:
        if cursor.strftime("%A") == weekday_name:
            dates.append(cursor)
        cursor -= datetime.timedelta(days=1)
    return list(reversed(dates))