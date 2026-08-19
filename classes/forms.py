from django import forms

from .models import SchoolClass, Subject


class ClassForm(forms.ModelForm):
    class Meta:
        model = SchoolClass
        fields = ["name", "grade", "section", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. Class 6"}
            ),
            "grade": forms.NumberInput(attrs={"class": "form-control"}),
            "section": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. A"}
            ),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ["name", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "e.g. Artificial Intelligence"}
            ),
            "description": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
