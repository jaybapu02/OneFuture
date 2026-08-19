from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import TrainerProfile


class TrainerAdminTests(TestCase):
    def setUp(self):
        User.objects.create_superuser(username="admin", password="Admin@123")

    def test_admin_can_create_trainer(self):
        self.client.login(username="admin", password="Admin@123")
        response = self.client.post(
            reverse("trainers:trainer_create"),
            {
                "username": "neha",
                "password": "Neha@12345",
                "full_name": "Neha Gupta",
                "employee_id": "EMP-100",
                "phone_number": "9999999999",
                "designation": "Trainer",
                "joining_date": "2026-01-01",
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="neha").exists())
        trainer = User.objects.get(username="neha").profile
        self.assertEqual(trainer.full_name, "Neha Gupta")
        self.assertTrue(trainer.user.check_password("Neha@12345"))

    def test_duplicate_username_rejected(self):
        User.objects.create_user(username="existing", password="Pass@12345")
        self.client.login(username="admin", password="Admin@123")
        response = self.client.post(
            reverse("trainers:trainer_create"),
            {
                "username": "existing",
                "password": "Neha@12345",
                "full_name": "Neha",
                "employee_id": "EMP-100",
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            TrainerProfile.objects.filter(employee_id="EMP-100").exists()
        )

    def test_deactivate_blocks_login(self):
        user = User.objects.create_user(username="x", password="Pass@12345")
        TrainerProfile.objects.create(
            user=user, employee_id="EMP-1", full_name="X", is_active=True
        )
        self.client.login(username="admin", password="Admin@123")
        response = self.client.post(
            reverse("trainers:trainer_toggle", args=[user.profile.pk])
        )
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_trainer_edit_resets_password(self):
        user = User.objects.create_user(username="y", password="Old@12345")
        TrainerProfile.objects.create(
            user=user, employee_id="EMP-2", full_name="Y"
        )
        self.client.login(username="admin", password="Admin@123")
        response = self.client.post(
            reverse("trainers:trainer_edit", args=[user.profile.pk]),
            {
                "full_name": "Y Updated",
                "employee_id": "EMP-2",
                "phone_number": "",
                "designation": "",
                "joining_date": "",
                "is_active": "on",
                "new_password": "New@12345",
            },
        )
        self.assertEqual(response.status_code, 302)
        user.refresh_from_db()
        self.assertTrue(user.check_password("New@12345"))