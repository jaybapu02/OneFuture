from django import forms

from .models import DAYS_OF_WEEK, Timetable


class TimetableForm(forms.ModelForm):
    class Meta:
        model = Timetable
        fields = [
            "trainer",
            "school_class",
            "subject",
            "day_of_week",
            "start_time",
            "end_time",
            "room",
            "is_active",
        ]
        widgets = {
            "trainer": forms.Select(attrs={"class": "form-select"}),
            "school_class": forms.Select(attrs={"class": "form-select"}),
            "subject": forms.Select(attrs={"class": "form-select"}),
            "day_of_week": forms.Select(attrs={"class": "form-select"}),
            "start_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "end_time": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "room": forms.TextInput(attrs={"class": "form-control"}),
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
