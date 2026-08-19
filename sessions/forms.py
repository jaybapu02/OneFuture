from django import forms

from .models import Session


class SessionForm(forms.ModelForm):
    """
    Form for completing/editing a session report.

    The session number, trainer, class and subject are NEVER entered here.
    They are always derived from the timetable / computed by the backend.
    """

    class Meta:
        model = Session
        fields = [
            "date",
            "start_time",
            "end_time",
            "students_present",
            "topic_taught",
            "activity",
            "notes",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "start_time": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "end_time": forms.TimeInput(attrs={"class": "form-control", "type": "time"}),
            "students_present": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "inputmode": "numeric",
                    "placeholder": "e.g. 25",
                }
            ),
            "topic_taught": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "What did you teach in this class?",
                }
            ),
            "activity": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "Activity / project done (optional)",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "Any additional notes (optional)",
                }
            ),
        }

    def clean_students_present(self):
        value = self.cleaned_data["students_present"]
        if value is None or value < 0:
            raise forms.ValidationError("Students present cannot be negative.")
        return value

    def clean_topic_taught(self):
        value = self.cleaned_data.get("topic_taught", "")
        if not value or not value.strip():
            raise forms.ValidationError("Please enter what was taught.")
        return value

    def clean(self):
        cleaned = super().clean()
        start_time = cleaned.get("start_time")
        end_time = cleaned.get("end_time")
        if start_time and end_time and end_time <= start_time:
            self.add_error("end_time", "End time must be after start time.")
        return cleaned