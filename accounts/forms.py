from django import forms

from trainers.models import TrainerProfile


class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = TrainerProfile
        fields = ["full_name", "phone_number", "designation"]
        widgets = {
            "full_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Full name"}
            ),
            "phone_number": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Phone number"}
            ),
            "designation": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Designation"}
            ),
        }
