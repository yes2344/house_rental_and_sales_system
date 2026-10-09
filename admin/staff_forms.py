from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from accounts.models import Profile


PERMISSION_CHOICES = list(Profile.Permission.choices)
BROKER_PERMISSIONS = [
    (Profile.Permission.PROPERTY_MANAGE_ASSIGNED, 'Manage assigned listings'),
    (Profile.Permission.VIEWING_MANAGE_ASSIGNED, 'Manage assigned viewing requests'),
]
OWNER_ONLY_PERMISSIONS = {
    Profile.Permission.SETTINGS_MANAGE,
    Profile.Permission.STAFF_MANAGE,
}


class DelegatedAccountCreateForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    role = forms.ChoiceField(choices=[
        (Profile.Role.ADMINISTRATOR, 'Administrator'),
        (Profile.Role.BROKER, 'Broker'),
    ])
    management_permissions = forms.MultipleChoiceField(
        choices=PERMISSION_CHOICES,
        required=False,
    )

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        User = get_user_model()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('A user with this username already exists.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        User = get_user_model()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('A user with this email already exists.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        permissions = set(cleaned_data.get('management_permissions', []))
        if OWNER_ONLY_PERMISSIONS.intersection(permissions):
            self.add_error(
                'management_permissions',
                'Platform settings and delegated-account control remain owner-only.',
            )
        if role == Profile.Role.BROKER and permissions - {
            Profile.Permission.PROPERTY_MANAGE_ASSIGNED,
            Profile.Permission.VIEWING_MANAGE_ASSIGNED,
        }:
            self.add_error(
                'management_permissions',
                'Brokers may receive only assigned-listing and assigned-viewing permissions.',
            )
        return cleaned_data


class DelegatedAccountUpdateForm(forms.Form):
    role = forms.ChoiceField(choices=[
        (Profile.Role.ADMINISTRATOR, 'Administrator'),
        (Profile.Role.BROKER, 'Broker'),
    ])
    is_active = forms.BooleanField(required=False)
    management_permissions = forms.MultipleChoiceField(
        choices=PERMISSION_CHOICES,
        required=False,
    )

    def __init__(self, *args, profile, **kwargs):
        self.profile = profile
        choices = (
            BROKER_PERMISSIONS
            if (args and args[0].get('role') == Profile.Role.BROKER)
            or (not args and profile.role == Profile.Role.BROKER)
            else PERMISSION_CHOICES
        )
        super().__init__(*args, **kwargs)
        self.fields['management_permissions'].choices = choices
        if not self.is_bound:
            self.initial.update({
                'role': profile.role,
                'is_active': profile.user.is_active,
                'management_permissions': profile.management_permissions,
            })

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        permissions = set(cleaned_data.get('management_permissions', []))
        if OWNER_ONLY_PERMISSIONS.intersection(permissions):
            self.add_error('management_permissions', 'These permissions remain owner-only.')
        if role == Profile.Role.BROKER and permissions - {
            Profile.Permission.PROPERTY_MANAGE_ASSIGNED,
            Profile.Permission.VIEWING_MANAGE_ASSIGNED,
        }:
            self.add_error(
                'management_permissions',
                'Brokers may receive only assigned-listing and assigned-viewing permissions.',
            )
        return cleaned_data
