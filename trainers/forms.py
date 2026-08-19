from django import forms
from django.contrib.auth.models import User

from .models import School, TrainerProfile


class TrainerCreateForm(forms.ModelForm):
    username = forms.CharField(
        max_length=150,
        label="Username",
        widget=forms.TextInput(
            attrs={"class": "form-control", "autocomplete": "off"}
        ),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "autocomplete": "new-password"}
        ),
        help_text="The trainer will use this password to log in.",
    )

    class Meta:
        model = TrainerProfile
        fields = [
            "school",
            "full_name",
            "employee_id",
            "phone_number",
            "designation",
            "joining_date",
            "is_active",
        ]
        widgets = {
            "school": forms.Select(attrs={"class": "form-select"}),
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "employee_id": forms.TextInput(attrs={"class": "form-control"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "designation": forms.TextInput(attrs={"class": "form-control"}),
            "joining_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        help_texts = {
            "school": "Each trainer belongs to exactly one school.",
        }

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("A user with this username already exists.")
        return username

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = User.objects.create_user(
            username=self.cleaned_data["username"],
            password=self.cleaned_data["password"],
            is_active=profile.is_active,
        )
        profile.user = user
        if commit:
            profile.save()
        return profile


class TrainerEditForm(forms.ModelForm):
    new_password = forms.CharField(
        label="Reset password",
        required=False,
        widget=forms.PasswordInput(
            attrs={"class": "form-control", "autocomplete": "new-password"}
        ),
        help_text="Leave blank to keep the current password.",
    )

    class Meta:
        model = TrainerProfile
        fields = [
            "school",
            "full_name",
            "employee_id",
            "phone_number",
            "designation",
            "joining_date",
            "is_active",
        ]
        widgets = {
            "school": forms.Select(attrs={"class": "form-select"}),
            "full_name": forms.TextInput(attrs={"class": "form-control"}),
            "employee_id": forms.TextInput(attrs={"class": "form-control"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control"}),
            "designation": forms.TextInput(attrs={"class": "form-control"}),
            "joining_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
        help_texts = {
            "school": "Each trainer belongs to exactly one school.",
        }

    def save(self, commit=True):
        profile = super().save(commit=False)
        new_password = self.cleaned_data.get("new_password")
        if new_password:
            profile.user.set_password(new_password)
            profile.user.is_active = profile.is_active
            profile.user.save(update_fields=["password", "is_active"])
        else:
            profile.user.is_active = profile.is_active
            profile.user.save(update_fields=["is_active"])
        if commit:
            profile.save()
        return profile
