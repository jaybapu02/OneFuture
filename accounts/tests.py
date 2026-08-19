from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from trainers.models import TrainerProfile


def create_trainer(username="trainer1", password="Trainer@123", employee_id="E1"):
    user = User.objects.create_user(username=username, password=password)
    return TrainerProfile.objects.create(
        user=user, employee_id=employee_id, full_name=username.title()
    )


class LoginTests(TestCase):
    def test_trainer_login_success(self):
        create_trainer()
        ok = self.client.login(username="trainer1", password="Trainer@123")
        self.assertTrue(ok)

    def test_trainer_login_wrong_password(self):
        create_trainer()
        ok = self.client.login(username="trainer1", password="wrong-password")
        self.assertFalse(ok)

    def test_deactivated_trainer_cannot_login(self):
        profile = create_trainer()
        profile.is_active = False
        profile.user.is_active = False
        profile.user.save(update_fields=["is_active"])
        profile.save(update_fields=["is_active"])
        ok = self.client.login(username="trainer1", password="Trainer@123")
        self.assertFalse(ok)

    def test_admin_login_success(self):
        User.objects.create_superuser(username="admin", password="Admin@123")
        ok = self.client.login(username="admin", password="Admin@123")
        self.assertTrue(ok)

    def test_login_page_renders(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)


class AccessControlTests(TestCase):
    def setUp(self):
        self.trainer = create_trainer()
        self.admin_user = User.objects.create_superuser(
            username="admin", password="Admin@123"
        )
        self.other = create_trainer("trainer2", employee_id="E2")

    def test_unauthenticated_user_redirected_to_login(self):
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_trainer_cannot_access_admin_pages(self):
        self.client.login(username="trainer1", password="Trainer@123")
        response = self.client.get("/trainers/")
        self.assertEqual(response.status_code, 403)

    def test_trainer_cannot_access_other_trainers_tasks(self):
        from classes.models import SchoolClass, Subject
        from tasks.models import Task

        cls = SchoolClass.objects.create(name="Class 1", section="A")
        subject = Subject.objects.create(name="Maths")
        task = Task.objects.create(
            trainer=self.other,
            school_class=cls,
            subject=subject,
            title="Secret task",
            date="2026-01-10",
        )

        self.client.login(username="trainer1", password="Trainer@123")
        response = self.client.get(reverse("tasks:task_edit", args=[task.pk]))
        self.assertEqual(response.status_code, 404)

        response = self.client.post(
            reverse("tasks:task_delete", args=[task.pk])
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Task.objects.filter(pk=task.pk).exists())

    def test_trainer_cannot_view_other_trainers_session(self):
        from classes.models import SchoolClass, Subject
        from sessions.models import Session

        cls = SchoolClass.objects.create(name="Class 2", section="A")
        subject = Subject.objects.create(name="Physics")
        session = Session.objects.create(
            trainer=self.other,
            school_class=cls,
            subject=subject,
            session_number=1,
            date="2026-01-10",
            students_present=10,
            topic_taught="Motion",
        )
        self.client.login(username="trainer1", password="Trainer@123")
        response = self.client.get(
            reverse("sessions:session_detail", args=[session.pk])
        )
        self.assertEqual(response.status_code, 403)

    def test_admin_can_view_all_sessions(self):
        from classes.models import SchoolClass, Subject
        from sessions.models import Session

        cls = SchoolClass.objects.create(name="Class 2", section="A")
        subject = Subject.objects.create(name="Physics")
        session = Session.objects.create(
            trainer=self.trainer,
            school_class=cls,
            subject=subject,
            session_number=1,
            date="2026-01-10",
            students_present=10,
            topic_taught="Motion",
        )
        self.client.login(username="admin", password="Admin@123")
        response = self.client.get(
            reverse("sessions:session_detail", args=[session.pk])
        )
        self.assertEqual(response.status_code, 200)

    def test_trainer_dashboard_shows_own_name_only(self):
        self.client.login(username="trainer1", password="Trainer@123")
        response = self.client.get("/dashboard/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Trainer1")
        self.assertNotContains(response, "Trainer2")