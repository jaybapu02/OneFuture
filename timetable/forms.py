from django import forms
from django.core.validators import FileExtensionValidator

from classes.models import SchoolClass, Subject

from .models import DAYS_OF_WEEK, ManualClass, Timetable

XLSX_VALIDATORS = [
    FileExtensionValidator(
        allowed_extensions=["xlsx"],
        message="Only .xlsx files are accepted.",
    )
]


class TimetableForm(forms.ModelForm):
    class Meta:
        model = Timetable
        fields = [
            "trainer",
            "school_class",
            "subject",
            "day_of_week",
            "period",
            "start_time",
            "end_time",
            "room",
            "source",
            "is_active",
        ]
        widgets = {
            "trainer": forms.Select(attrs={"class": "form-select"}),
            "school_class": forms.Select(attrs={"class": "form-select"}),
            "subject": forms.Select(attrs={"class": "form-select"}),
            "day_of_week": forms.Select(attrs={"class": "form-select"}),
            "period": forms.NumberInput(
                attrs={"class": "form-control", "min": "1", "placeholder": "e.g. 4"}
            ),
            "start_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "end_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "room": forms.TextInput(attrs={"class": "form-control"}),
            "source": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean(self):
        cleaned = super().clean()
        if not self.is_valid():
            return cleaned

        start_time = cleaned.get("start_time")
        end_time = cleaned.get("end_time")
        if start_time and end_time and end_time <= start_time:
            self.add_error("end_time", "End time must be after start time.")

        instance = self.instance
        # Build a temp instance so conflict queries work for creates too.
        if instance.pk is None:
            instance = Timetable(
                trainer=cleaned.get("trainer"),
                school_class=cleaned.get("school_class"),
                day_of_week=cleaned.get("day_of_week"),
                start_time=start_time,
                end_time=end_time,
                is_active=cleaned.get("is_active", True),
            )
        else:
            instance.trainer = cleaned.get("trainer")
            instance.school_class = cleaned.get("school_class")
            instance.day_of_week = cleaned.get("day_of_week")
            instance.start_time = start_time
            instance.end_time = end_time
            instance.is_active = cleaned.get("is_active", True)

        if not instance.is_active:
            return cleaned

        trainer_conflicts = instance.trainer_conflicts()
        if trainer_conflicts.exists():
            other = trainer_conflicts.first()
            self.add_error(
                None,
                (
                    f"Conflict: {instance.trainer} is already scheduled from "
                    f"{other.start_time:%H:%M} to {other.end_time:%H:%M} on "
                    f"{instance.day_of_week} ({other.school_class} · {other.subject})."
                ),
            )

        class_conflicts = instance.class_conflicts().exclude(
            trainer=instance.trainer
        )
        if class_conflicts.exists():
            other = class_conflicts.first()
            self.add_error(
                None,
                (
                    f"Conflict: {instance.school_class} is already scheduled with "
                    f"{other.trainer} from {other.start_time:%H:%M} to "
                    f"{other.end_time:%H:%M} on {instance.day_of_week}."
                ),
            )

        return cleaned


class ManualClassForm(forms.ModelForm):
    class Meta:
        model = ManualClass
        fields = [
            "school_class",
            "subject",
            "date",
            "period",
            "start_time",
            "end_time",
            "notes",
        ]
        labels = {
            "school_class": "Class",
            "period": "Period",
            "notes": "Notes (optional)",
        }
        widgets = {
            "school_class": forms.Select(attrs={"class": "form-select"}),
            "subject": forms.Select(attrs={"class": "form-select"}),
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "period": forms.NumberInput(
                attrs={"class": "form-control", "min": "1", "placeholder": "e.g. 6"}
            ),
            "start_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "end_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "notes": forms.TextInput(attrs={"class": "form-control"}),
        }
        help_texts = {
            "school_class": "This is a one-off class on a specific date. "
            "It does not change your recurring weekly timetable.",
        }

    def clean(self):
        cleaned = super().clean()
        start_time = cleaned.get("start_time")
        end_time = cleaned.get("end_time")
        if start_time and end_time and end_time <= start_time:
            self.add_error("end_time", "End time must be after start time.")
        return cleaned


class TimetableUploadForm(forms.Form):
    file = forms.FileField(
        label="Weekly timetable (.xlsx)",
        validators=XLSX_VALIDATORS,
        widget=forms.FileInput(
            attrs={"class": "form-control", "accept": ".xlsx"}
        ),
        help_text=(
            "Structure: a 'Day' column and 'Period N' columns. Each cell like "
            "'7th — 12:30–1:15'. Empty cells or '—' mean no class."
        ),
    )
