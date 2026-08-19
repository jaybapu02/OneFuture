"""
Tests for the real August 2026 session import ("August Month Details" report).

These tests prove:
* NA / office rows never become sessions.
* One row with several classes becomes one Session per class.
* Historical session numbers are preserved exactly as written.
* The import is idempotent (no duplicates on re-run).
* Manual edits are never overwritten by a re-import.
* The weekly timetable is untouched by the import.
* The monthly filter and summary are database-driven.
"""
import datetime

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from classes.models import SchoolClass, Subject
from sessions.models import Session
from timetable.models import Timetable
from trainers.models import School, TrainerProfile

SCHOOL_NAME = "BMC Bagurai School"


class AugustImportTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name=SCHOOL_NAME, address="Bhadrak, Odisha"
        )
        self.user = User.objects.create_user(
            username="jaychandra", password="Jay@123"
        )
        self.trainer = TrainerProfile.objects.create(
            user=self.user, school=self.school, full_name="Jaychandra Dash"
        )
        self.subject = Subject.objects.create(name="Artificial Intelligence")
        self.classes = {}
        for grade in range(3, 9):
            self.classes[grade] = SchoolClass.objects.create(
                name=f"Class {grade}", section="", grade=grade
            )
        call_command("import_august_data")

    def session_count(self):
        return Session.objects.filter(
            trainer=self.trainer, date__year=2026, date__month=8
        ).count()

    # ---- real records ----
    def test_total_import_count(self):
        self.assertEqual(self.session_count(), 20)

    def test_na_rows_do_not_become_sessions(self):
        for day in (3, 8, 15, 17):
            self.assertFalse(
                Session.objects.filter(
                    trainer=self.trainer, date=datetime.date(2026, 8, day)
                ).exists()
            )

    def test_multi_class_row_becomes_separate_sessions(self):
        aug_11 = Session.objects.filter(
            trainer=self.trainer, date=datetime.date(2026, 8, 11)
        )
        self.assertEqual(aug_11.count(), 4)
        self.assertEqual(
            set(aug_11.values_list("school_class__grade", flat=True)), {3, 5, 6, 7}
        )

    def test_historical_session_numbers_preserved(self):
        def numbers(grade):
            return set(
                Session.objects.filter(
                    trainer=self.trainer, school_class=self.classes[grade]
                ).values_list("session_number", flat=True)
            )

        self.assertEqual(numbers(3), {1, 3, 4, None})
        self.assertEqual(numbers(4), {1, 3, None})
        self.assertEqual(numbers(5), {1, 2, 3})
        self.assertEqual(numbers(6), {1, 2, 4})
        self.assertEqual(numbers(7), {2, 3, 4})
        self.assertEqual(numbers(8), {2, None})

    def test_attendance_values_preserved(self):
        s = Session.objects.get(
            trainer=self.trainer,
            date=datetime.date(2026, 8, 4),
            school_class=self.classes[6],
        )
        self.assertEqual(s.students_present, 40)
        self.assertEqual(s.total_students, 40)
        self.assertEqual(s.students_absent, 0)

        aug_14 = Session.objects.get(
            trainer=self.trainer,
            date=datetime.date(2026, 8, 14),
            school_class=self.classes[4],
        )
        self.assertEqual(aug_14.students_present, 12)
        self.assertEqual(aug_14.total_students, 12)
        self.assertEqual(aug_14.students_absent, 0)

    def test_lesson_plans_and_location_preserved(self):
        aug_13 = Session.objects.get(
            trainer=self.trainer,
            date=datetime.date(2026, 8, 13),
            school_class=self.classes[7],
        )
        self.assertEqual(
            aug_13.topic_taught,
            "Data and types of data and quiz based on data.",
        )
        self.assertEqual(aug_13.location, "Bhadrak")
        self.assertEqual(aug_13.school, self.school)

        for session in Session.objects.filter(trainer=self.trainer):
            self.assertEqual(session.location, "Bhadrak")
            self.assertEqual(session.school, self.school)

    def test_separate_timings_kept_per_class(self):
        aug_04 = Session.objects.get(
            trainer=self.trainer,
            date=datetime.date(2026, 8, 4),
            school_class=self.classes[6],
        )
        self.assertEqual(aug_04.start_time, datetime.time(12, 0))
        self.assertEqual(aug_04.end_time, datetime.time(12, 45))

    def test_import_is_idempotent(self):
        call_command("import_august_data")
        self.assertEqual(self.session_count(), 20)

    def test_import_does_not_overwrite_manual_edits(self):
        session = Session.objects.get(
            trainer=self.trainer,
            date=datetime.date(2026, 8, 14),
            school_class=self.classes[4],
        )
        session.students_present = 11
        session.topic_taught = "Edited by trainer"
        session.save()
        call_command("import_august_data")
        session.refresh_from_db()
        self.assertEqual(session.students_present, 11)
        self.assertEqual(session.topic_taught, "Edited by trainer")

    def test_weekly_timetable_untouched_by_import(self):
        self.assertEqual(Timetable.objects.count(), 0)
        call_command("import_august_data")
        self.assertEqual(Timetable.objects.count(), 0)


class AugustMonthlyViewTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name=SCHOOL_NAME, address="Bhadrak, Odisha"
        )
        self.user = User.objects.create_user(
            username="jaychandra", password="Jay@123"
        )
        self.trainer = TrainerProfile.objects.create(
            user=self.user, school=self.school, full_name="Jaychandra Dash"
        )
        self.subject = Subject.objects.create(name="Artificial Intelligence")
        for grade in range(3, 9):
            SchoolClass.objects.create(
                name=f"Class {grade}", section="", grade=grade
            )
        call_command("import_august_data")
        self.client.login(username="jaychandra", password="Jay@123")

    def test_month_filter_shows_only_august(self):
        response = self.client.get(reverse("sessions:session_list"), {"month": "2026-08"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["summary"]["total_sessions"], 20)
        page = response.context["sessions"]
        self.assertTrue(all(s.date.month == 8 and s.date.year == 2026 for s in page))

    def test_summary_calculated_from_database(self):
        response = self.client.get(reverse("sessions:session_list"), {"month": "2026-08"})
        summary = response.context["summary"]
        self.assertEqual(summary["total_sessions"], 20)
        self.assertEqual(summary["working_days"], 10)
        self.assertEqual(summary["classes_covered"], 6)
        # present: 40 (4 Aug) + 10 (10 Aug) + 12 (14 Aug) + 12 + 12 (18 Aug)
        self.assertEqual(summary["students_present"], 86)
        self.assertEqual(summary["students_absent"], 0)

    def test_dashboard_stats_come_from_real_records(self):
        response = self.client.get(reverse("dashboard"))
        stats = response.context["stats"]
        self.assertEqual(stats["completed_sessions"], 20)
        self.assertEqual(stats["students_total"], 86)
        self.assertEqual(stats["classes_covered"], 6)
        recent = list(response.context["recent_sessions"])
        self.assertEqual(len(recent), 5)
        self.assertEqual(recent[0].date, datetime.date(2026, 8, 18))

    def test_next_number_continues_after_imported_history(self):
        cls_4 = SchoolClass.objects.get(name="Class 4")
        self.assertEqual(
            Session.objects.filter(
                trainer=self.trainer, school_class=cls_4
            ).count(),
            3,
        )
        self.assertEqual(
            Session.objects.filter(
                trainer=self.trainer, school_class=cls_4
            ).exclude(session_number__isnull=True).order_by("-session_number").first().session_number,
            3,
        )
        # New session for Class 4 should get number 4 (max + 1).
        from sessions.models import get_next_session_number

        self.assertEqual(get_next_session_number(cls_4, self.subject), 4)

    def test_trainer_cannot_see_another_trainer_sessions(self):
        other_user = User.objects.create_user(username="other", password="Pass@123")
        other = TrainerProfile.objects.create(
            user=other_user, employee_id="OTH-001", full_name="Other Trainer"
        )
        cls_8 = SchoolClass.objects.get(name="Class 8")
        Session.objects.create(
            trainer=other,
            school=other.school,
            subject=self.subject,
            school_class=cls_8,
            session_number=1,
            date="2026-08-05",
            students_present=10,
            topic_taught="Other's session",
        )
        response = self.client.get(reverse("sessions:session_list"))
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Other's session", response.content.decode())