from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from classes.models import SchoolClass, Subject
from trainers.models import TrainerProfile

from .forms import TimetableForm
from .models import Timetable


def make_models():
    user1 = User.objects.create_user(username="t1", password="Pass@123")
    user2 = User.objects.create_user(username="t2", password="Pass@123")
    trainer1 = TrainerProfile.objects.create(
        user=user1, employee_id="T1", full_name="Trainer One"
    )
    trainer2 = TrainerProfile.objects.create(
        user=user2, employee_id="T2", full_name="Trainer Two"
    )
    cls_a = SchoolClass.objects.create(name="Class 6", section="A")
    cls_b = SchoolClass.objects.create(name="Class 6", section="B")
    subject = Subject.objects.create(name="Artificial Intelligence")
    return trainer1, trainer2, cls_a, cls_b, subject


class TimetableModelTests(TestCase):
    def setUp(self):
        self.t1, self.t2, self.cls_a, self.cls_b, self.subject = make_models()

    def make_entry(self, trainer, cls, day="Monday", start="09:00", end="10:00"):
        return Timetable.objects.create(
            trainer=trainer,
            school_class=cls,
            subject=self.subject,
            day_of_week=day,
            start_time=start,
            end_time=end,
        )

    def test_valid_entries_do_not_conflict(self):
        self.make_entry(self.t1, self.cls_a, start="09:00", end="10:00")
        entry = self.make_entry(self.t1, self.cls_b, start="10:00", end="11:00")
        self.assertFalse(entry.trainer_conflicts().exists())

    def test_same_trainer_overlap_detected(self):
        self.make_entry(self.t1, self.cls_a, start="09:00", end="10:00")
        entry = self.make_entry(self.t1, self.cls_b, start="09:30", end="10:30")
        self.assertTrue(entry.trainer_conflicts().exists())

    def test_same_trainer_overlap_across_days_not_detected(self):
        self.make_entry(self.t1, self.cls_a, day="Monday", start="09:00", end="10:00")
        entry = self.make_entry(self.t1, self.cls_b, day="Tuesday", start="09:00", end="10:00")
        self.assertFalse(entry.trainer_conflicts().exists())

    def test_same_class_overlap_with_other_trainer_detected(self):
        self.make_entry(self.t1, self.cls_a, start="09:00", end="10:00")
        entry = self.make_entry(self.t2, self.cls_a, start="09:30", end="10:30")
        self.assertTrue(entry.class_conflicts().exists())

    def test_same_class_different_trainer_no_overlap_ok(self):
        self.make_entry(self.t1, self.cls_a, start="09:00", end="10:00")
        entry = self.make_entry(self.t2, self.cls_a, start="10:00", end="11:00")
        self.assertFalse(entry.class_conflicts().exists())


class TimetableFormTests(TestCase):
    def setUp(self):
        self.t1, self.t2, self.cls_a, self.cls_b, self.subject = make_models()

    def base_data(self, **overrides):
        data = {
            "trainer": self.t1.pk,
            "school_class": self.cls_a.pk,
            "subject": self.subject.pk,
            "day_of_week": "Monday",
            "period": "4",
            "start_time": "09:00",
            "end_time": "10:00",
            "room": "",
            "source": "MANUAL",
            "is_active": "on",
        }
        data.update(overrides)
        return data

    def test_valid_form(self):
        form = TimetableForm(data=self.base_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_end_time_before_start_rejected(self):
        form = TimetableForm(data=self.base_data(start_time="11:00", end_time="10:00"))
        self.assertFalse(form.is_valid())
        self.assertIn("end_time", form.errors)

    def test_trainer_conflict_rejected(self):
        Timetable.objects.create(
            trainer=self.t1,
            school_class=self.cls_a,
            subject=self.subject,
            day_of_week="Monday",
            start_time="09:00",
            end_time="10:00",
        )
        form = TimetableForm(
            data=self.base_data(school_class=self.cls_b.pk, start_time="09:30", end_time="10:30")
        )
        self.assertFalse(form.is_valid())
        self.assertIn("Conflict", form.errors.as_text())

    def test_class_conflict_with_another_trainer_rejected(self):
        Timetable.objects.create(
            trainer=self.t1,
            school_class=self.cls_a,
            subject=self.subject,
            day_of_week="Monday",
            start_time="09:00",
            end_time="10:00",
        )
        form = TimetableForm(
            data=self.base_data(trainer=self.t2.pk, start_time="09:30", end_time="10:30")
        )
        self.assertFalse(form.is_valid())
        self.assertIn("Conflict", form.errors.as_text())

    def test_editing_own_entry_does_not_self_conflict(self):
        entry = Timetable.objects.create(
            trainer=self.t1,
            school_class=self.cls_a,
            subject=self.subject,
            day_of_week="Monday",
            start_time="09:00",
            end_time="10:00",
        )
        form = TimetableForm(
            instance=entry,
            data=self.base_data(start_time="09:00", end_time="10:00"),
        )
        self.assertTrue(form.is_valid(), form.errors)


class TimetableAdminViewsTests(TestCase):
    def setUp(self):
        self.t1, self.t2, self.cls_a, self.cls_b, self.subject = make_models()
        User.objects.create_superuser(username="admin", password="Admin@123")

    def test_admin_can_create_timetable_entry(self):
        self.client.login(username="admin", password="Admin@123")
        response = self.client.post(
            reverse("timetable:manage_create"),
            {
                "trainer": self.t1.pk,
                "school_class": self.cls_a.pk,
                "subject": self.subject.pk,
                "day_of_week": "Wednesday",
                "period": "4",
                "start_time": "09:00",
                "end_time": "10:00",
                "room": "Lab 1",
                "source": "MANUAL",
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Timetable.objects.count(), 1)

    def test_admin_delete_requires_post(self):
        entry = Timetable.objects.create(
            trainer=self.t1,
            school_class=self.cls_a,
            subject=self.subject,
            day_of_week="Monday",
            start_time="09:00",
            end_time="10:00",
        )
        self.client.login(username="admin", password="Admin@123")
        response = self.client.post(
            reverse("timetable:manage_delete", args=[entry.pk])
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Timetable.objects.filter(pk=entry.pk).exists())