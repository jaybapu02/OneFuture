from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import SchoolClass, Subject


class ClassAdminTests(TestCase):
    def setUp(self):
        User.objects.create_superuser(username="admin", password="Admin@123")

    def test_admin_can_create_class(self):
        self.client.login(username="admin", password="Admin@123")
        response = self.client.post(
            reverse("classes:class_create"),
            {
                "name": "Class 6",
                "grade": 6,
                "section": "A",
                "description": "Regular batch",
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 302)
        cls = SchoolClass.objects.get(name="Class 6")
        self.assertEqual(str(cls), "Class 6 - A")

    def test_duplicate_class_rejected(self):
        SchoolClass.objects.create(name="Class 6", section="A")
        self.client.login(username="admin", password="Admin@123")
        response = self.client.post(
            reverse("classes:class_create"),
            {
                "name": "Class 6",
                "grade": 6,
                "section": "A",
                "description": "",
                "is_active": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(SchoolClass.objects.filter(name="Class 6").count(), 1)

    def test_admin_can_toggle_class(self):
        cls = SchoolClass.objects.create(name="Class 7", section="B")
        self.client.login(username="admin", password="Admin@123")
        response = self.client.post(reverse("classes:class_toggle", args=[cls.pk]))
        self.assertEqual(response.status_code, 302)
        cls.refresh_from_db()
        self.assertFalse(cls.is_active)

    def test_admin_can_create_subject(self):
        self.client.login(username="admin", password="Admin@123")
        response = self.client.post(
            reverse("classes:subject_create"),
            {"name": "Python", "description": "Programming", "is_active": "on"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Subject.objects.filter(name="Python").exists())