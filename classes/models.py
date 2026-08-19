from django.db import models


class SchoolClass(models.Model):
    """A class/batch, e.g. "Class 6" section "A"."""

    name = models.CharField(max_length=80, help_text='e.g. "Class 6"')
    grade = models.PositiveSmallIntegerField(null=True, blank=True)
    section = models.CharField(max_length=10, blank=True, help_text='e.g. "A"')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["grade", "name", "section"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "section"], name="unique_class_name_section"
            )
        ]

    def __str__(self):
        if self.section:
            return f"{self.name} - {self.section}"
        return self.name


class Subject(models.Model):
    """A subject taught by trainers, e.g. Artificial Intelligence."""

    name = models.CharField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
