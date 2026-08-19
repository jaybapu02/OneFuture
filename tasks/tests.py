from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from classes.models import SchoolClass, Subject
from trainers.models import TrainerProfile

from .models import Task


def make_trainer(username="t1", password="Pass@123", employee_id="T1"):
    user = User.objects.create_user(username=username, password=password)
    return TrainerProfile.objects.create(
        user=user, employee_id=employee_id, full_name=username.title()
    )


def make_lookup():
    cls = SchoolClass.objects.create(name="Class 6", section="A")
    subject = Subject.objects.create(name="Artificial Intelligence")
    return cls, subject


class TaskModelTests(TestCase):
    def setUp(self):
        self.trainer = make_trainer()
        self.cls, self.subject = make_lookup()

    def create_task(self, **kwargs):
        data = {
            "trainer": self.trainer,
            "school_class": self.cls,
            "subject": self.subject,
            "title": "Do the worksheet",
            "date": "2026-01-10",
            "priority": Task.Priority.MEDIUM,
            "status": Task.Status.PENDING,
        }
        data.update(kwargs)
        return Task.objects.create(**data)

    def test_task_defaults(self):
        task = self.create_task()
        self.assertEqual(task.status, Task.Status.PENDING)
        self.assertEqual(task.priority, Task.Priority.MEDIUM)

    def test_end_before_start_rejected(self):
        with self.assertRaises(Exception):
            self.create_task(start_time="10:00", end_time="09:00")


class TaskViewTests(TestCase):
    def setUp(self):
        self.trainer = make_trainer()
        self.cls, self.subject = make_lookup()
        self.client.login(username="t1", password="Pass@123")

    def test_create_edit_delete_flow(self):
        # Create
        response = self.client.post(
            reverse("tasks:task_create"),
            {
                "title": "Prepare demo",
                "description": "Show robot demo",
                "school_class": self.cls.pk,
                "subject": self.subject.pk,
                "date": "2026-01-15",
                "start_time": "09:00",
                "end_time": "10:00",
                "priority": "High",
                "status": "Pending",
            },
        )
        self.assertEqual(response.status_code, 302)
        task = Task.objects.get(trainer=self.trainer)
        self.assertEqual(task.title, "Prepare demo")
        self.assertEqual(task.trainer, self.trainer)

        # Edit
        response = self.client.post(
            reverse("tasks:task_edit", args=[task.pk]),
            {
                "title": "Prepare demo v2",
                "description": "Show robot demo",
                "school_class": self.cls.pk,
                "subject": self.subject.pk,
                "date": "2026-01-16",
                "start_time": "09:00",
                "end_time": "10:00",
                "priority": "Low",
                "status": "In Progress",
            },
        )
        self.assertEqual(response.status_code, 302)
        task.refresh_from_db()
        self.assertEqual(task.title, "Prepare demo v2")
        self.assertEqual(task.status, Task.Status.IN_PROGRESS)

        # Complete via toggle
        response = self.client.post(reverse("tasks:task_toggle", args=[task.pk]))
        self.assertEqual(response.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.COMPLETED)

        # Delete
        response = self.client.post(reverse("tasks:task_delete", args=[task.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Task.objects.filter(pk=task.pk).exists())

    def test_task_created_from_timetable_prefilled(self):
        from timetable.models import Timetable

        timetable = Timetable.objects.create(
            trainer=self.trainer,
            school_class=self.cls,
            subject=self.subject,
            day_of_week="Monday",
            start_time="09:00",
            end_time="10:00",
        )
        response = self.client.post(
            reverse("tasks:task_create") + f"?timetable={timetable.pk}",
            {
                "title": "Chapter task",
                "description": "",
                "school_class": self.cls.pk,
                "subject": self.subject.pk,
                "date": "2026-01-19",
                "start_time": "09:00",
                "end_time": "10:00",
                "priority": "Medium",
                "status": "Pending",
            },
        )
        self.assertEqual(response.status_code, 302)
        task = Task.objects.get(trainer=self.trainer)
        self.assertEqual(task.timetable, timetable)
        self.assertEqual(task.school_class, self.cls)
        self.assertEqual(task.subject, self.subject)

    def test_cannot_create_task_from_another_trainers_timetable(self):
        from timetable.models import Timetable

        other = make_trainer("t2", employee_id="T2")
        timetable = Timetable.objects.create(
            trainer=other,
            school_class=self.cls,
            subject=self.subject,
            day_of_week="Monday",
            start_time="09:00",
            end_time="10:00",
        )
        response = self.client.get(
            reverse("tasks:task_create") + f"?timetable={timetable.pk}"
        )
        self.assertEqual(response.status_code, 404)