from threading import Thread

from django.contrib.auth.models import User
from django.db import transaction
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from classes.models import SchoolClass, Subject
from trainers.models import TrainerProfile

from .models import Session, get_next_session_number


def make_fixture(trainer_username="t"):
    user = User.objects.create_user(username=trainer_username, password="Pass@123")
    trainer = TrainerProfile.objects.create(
        user=user, employee_id=trainer_username.upper(), full_name="Trainer"
    )
    cls = SchoolClass.objects.create(name="Class 6", section="A")
    other_cls = SchoolClass.objects.create(name="Class 7", section="A")
    subject = Subject.objects.create(name="Artificial Intelligence")
    other_subject = Subject.objects.create(name="Robotics")
    return trainer, cls, other_cls, subject, other_subject


class SessionNumberingTests(TestCase):
    def setUp(self):
        self.trainer, self.cls, self.other_cls, self.subject, self.other_subject = (
            make_fixture()
        )

    def create_session(self, cls=None, subject=None, **kwargs):
        data = {
            "trainer": self.trainer,
            "school_class": cls or self.cls,
            "subject": subject or self.subject,
            "date": "2026-01-10",
            "students_present": 20,
            "topic_taught": "Lesson",
        }
        data.update(kwargs)
        if "session_number" not in data:
            data["session_number"] = get_next_session_number(
                data["school_class"], data["subject"]
            )
        return Session.objects.create(**data)

    def test_first_session_is_number_one(self):
        session = self.create_session()
        self.assertEqual(session.session_number, 1)

    def test_second_session_is_number_two(self):
        self.create_session()
        session = self.create_session()
        self.assertEqual(session.session_number, 2)

    def test_third_session_is_number_three(self):
        self.create_session()
        self.create_session()
        session = self.create_session()
        self.assertEqual(session.session_number, 3)

    def test_separate_classes_have_independent_numbering(self):
        self.create_session()
        self.create_session()
        first_other = self.create_session(cls=self.other_cls)
        self.assertEqual(first_other.session_number, 1)

    def test_separate_subjects_have_independent_numbering(self):
        self.create_session()
        self.create_session()
        first_other_subject = self.create_session(subject=self.other_subject)
        self.assertEqual(first_other_subject.session_number, 1)

    def test_deleting_a_session_does_not_renumber(self):
        s1 = self.create_session()
        self.create_session()
        s3 = self.create_session()
        self.create_session()
        s3.delete()
        next_number = get_next_session_number(self.cls, self.subject)
        self.assertEqual(next_number, 5)
        self.assertEqual(Session.objects.filter(school_class=self.cls).count(), 3)
        self.assertEqual(
            list(
                Session.objects.filter(school_class=self.cls)
                .order_by("session_number")
                .values_list("session_number", flat=True)
            ),
            [1, 2, 4],
        )

    def test_next_number_derives_from_highest_plus_one(self):
        self.create_session(session_number=7)
        self.assertEqual(get_next_session_number(self.cls, self.subject), 8)

    def test_duplicate_historical_numbers_are_allowed(self):
        """The August report contains irregular per-class numbers (e.g. two
        sessions numbered 2 for one class). Historical numbers are stored
        exactly as written, so no unique DB constraint exists anymore."""
        first = self.create_session(session_number=2)
        second = self.create_session(session_number=2)
        self.assertEqual(first.session_number, second.session_number)
        self.assertEqual(Session.objects.count(), 2)
        self.assertEqual(get_next_session_number(self.cls, self.subject), 3)

    def test_null_session_number_is_allowed(self):
        session = Session.objects.create(
            trainer=self.trainer,
            school_class=self.cls,
            subject=self.subject,
            date="2026-08-12",
            students_present=20,
            topic_taught="Number not recorded",
        )
        self.assertIsNone(session.session_number)
        self.assertEqual(get_next_session_number(self.cls, self.subject), 1)


class ConcurrentSessionNumberingTests(TransactionTestCase):
    """Real concurrency: parallel threads must get unique numbers."""

    def setUp(self):
        user = User.objects.create_user(username="conc", password="Pass@123")
        self.trainer = TrainerProfile.objects.create(
            user=user, employee_id="CONC", full_name="Concurrent"
        )
        self.cls = SchoolClass.objects.create(name="Class 9", section="A")
        self.subject = Subject.objects.create(name="AI Lab")

    def test_ten_parallel_creations_get_unique_numbers(self):
        results = []

        def worker():
            try:
                with transaction.atomic():
                    number = get_next_session_number(self.cls, self.subject)
                    Session.objects.create(
                        trainer=self.trainer,
                        school_class=self.cls,
                        subject=self.subject,
                        session_number=number,
                        date="2026-02-01",
                        students_present=15,
                        topic_taught="Parallel",
                    )
                results.append(number)
            except Exception as exc:  # pragma: no cover - failure path
                results.append(exc)
            finally:
                # Each thread gets its own DB connection; close it so the
                # test database can be dropped afterwards.
                from django.db import connections

                connections.close_all()

        threads = [Thread(target=worker) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        numbers = sorted(r for r in results if isinstance(r, int))
        self.assertEqual(len(numbers), 10)
        self.assertEqual(numbers, list(range(1, 11)))
        self.assertEqual(Session.objects.count(), 10)


class SessionFormTests(TestCase):
    def setUp(self):
        self.trainer, self.cls, _, self.subject, _ = make_fixture()
        from timetable.models import Timetable

        self.timetable = Timetable.objects.create(
            trainer=self.trainer,
            school_class=self.cls,
            subject=self.subject,
            day_of_week="Monday",
            start_time="09:00",
            end_time="10:00",
        )
        self.client.login(username="t", password="Pass@123")

    def test_valid_session_creation_via_workflow(self):
        response = self.client.post(
            reverse("sessions:session_complete", args=[self.timetable.pk]),
            {
                "date": "2026-01-12",
                "start_time": "09:00",
                "end_time": "10:00",
                "students_present": "25",
                "topic_taught": "Introduction to AI",
                "activity": "",
                "notes": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        session = Session.objects.get(timetable=self.timetable)
        self.assertEqual(session.session_number, 1)
        self.assertEqual(session.students_present, 25)
        self.assertEqual(session.trainer, self.trainer)
        self.assertEqual(session.school_class, self.cls)

    def test_negative_students_rejected(self):
        response = self.client.post(
            reverse("sessions:session_complete", args=[self.timetable.pk]),
            {
                "date": "2026-01-12",
                "start_time": "09:00",
                "end_time": "10:00",
                "students_present": "-1",
                "topic_taught": "Topic",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Session.objects.exists())

    def test_empty_topic_rejected(self):
        response = self.client.post(
            reverse("sessions:session_complete", args=[self.timetable.pk]),
            {
                "date": "2026-01-12",
                "start_time": "09:00",
                "end_time": "10:00",
                "students_present": "20",
                "topic_taught": "   ",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Session.objects.exists())

    def test_end_before_start_rejected(self):
        response = self.client.post(
            reverse("sessions:session_complete", args=[self.timetable.pk]),
            {
                "date": "2026-01-12",
                "start_time": "10:00",
                "end_time": "09:00",
                "students_present": "20",
                "topic_taught": "Topic",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Session.objects.exists())

    def test_complete_page_shows_next_session_number(self):
        session = Session.objects.create(
            trainer=self.trainer,
            timetable=self.timetable,
            school_class=self.cls,
            subject=self.subject,
            session_number=1,
            date="2026-01-05",
            students_present=20,
            topic_taught="Old lesson",
        )
        response = self.client.get(
            reverse("sessions:session_complete", args=[self.timetable.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Session Number: 2")

    def test_trainer_cannot_complete_another_trainers_timetable(self):
        other_user = User.objects.create_user(
            username="other", password="Pass@123"
        )
        other = TrainerProfile.objects.create(
            user=other_user, employee_id="OTH", full_name="Other"
        )
        from timetable.models import Timetable

        other_timetable = Timetable.objects.create(
            trainer=other,
            school_class=self.cls,
            subject=self.subject,
            day_of_week="Tuesday",
            start_time="09:00",
            end_time="10:00",
        )
        response = self.client.get(
            reverse("sessions:session_complete", args=[other_timetable.pk])
        )
        self.assertEqual(response.status_code, 404)

    def test_double_completion_redirects_to_existing(self):
        from django.utils import timezone

        session = Session.objects.create(
            trainer=self.trainer,
            timetable=self.timetable,
            school_class=self.cls,
            subject=self.subject,
            session_number=1,
            date=timezone.localdate(),
            students_present=20,
            topic_taught="Already done",
        )
        response = self.client.get(
            reverse("sessions:session_complete", args=[self.timetable.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            reverse("sessions:session_detail", args=[session.pk]), response.url
        )
        self.assertEqual(Session.objects.count(), 1)

    def test_session_edit_preserves_number_and_identity(self):
        session = Session.objects.create(
            trainer=self.trainer,
            timetable=self.timetable,
            school_class=self.cls,
            subject=self.subject,
            session_number=4,
            date="2026-01-12",
            students_present=20,
            topic_taught="Original",
        )
        response = self.client.post(
            reverse("sessions:session_edit", args=[session.pk]),
            {
                "date": "2026-01-13",
                "start_time": "09:00",
                "end_time": "10:00",
                "students_present": "30",
                "topic_taught": "Edited topic",
                "activity": "New activity",
                "notes": "",
            },
        )
        self.assertEqual(response.status_code, 302)
        session.refresh_from_db()
        self.assertEqual(session.session_number, 4)
        self.assertEqual(session.trainer, self.trainer)
        self.assertEqual(session.students_present, 30)
        self.assertEqual(session.topic_taught, "Edited topic")