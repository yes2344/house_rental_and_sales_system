from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from accounts.models import Profile
from accounts.permissions import effective_management_permissions


ADMINISTRATOR_PERMISSIONS = [
    (Profile.Permission.USERS_MANAGE, 'Manage broker accounts'),
]
BROKER_PERMISSIONS = [
    (Profile.Permission.PROPERTY_MANAGE_ASSIGNED, 'Manage assigned listings'),
    (Profile.Permission.VIEWING_MANAGE_ASSIGNED, 'Manage assigned viewing requests'),
    (Profile.Permission.OWNER_ANNOUNCEMENTS_REVIEW, 'Review owner property announcements'),
]
PERMISSION_CHOICES = ADMINISTRATOR_PERMISSIONS + BROKER_PERMISSIONS
OWNER_ONLY_PERMISSIONS = {
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

    def __init__(self, *args, actor=None, **kwargs):
        self.actor = actor
        super().__init__(*args, **kwargs)
        if actor and not actor.is_superuser:
            self.fields['role'].choices = [(Profile.Role.BROKER, 'Broker')]
            self.fields['role'].initial = Profile.Role.BROKER
            self.fields['management_permissions'].choices = BROKER_PERMISSIONS
            if not self.is_bound:
                self.initial.setdefault(
                    'management_permissions',
                    [permission for permission, _ in BROKER_PERMISSIONS],
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
        if self.actor and not self.actor.is_superuser and role != Profile.Role.BROKER:
            self.add_error('role', 'Administrators may manage broker accounts only.')
        if OWNER_ONLY_PERMISSIONS.intersection(permissions):
            self.add_error(
                'management_permissions',
                'Delegated-account control remains owner-only.',
            )
        if role == Profile.Role.BROKER and permissions - {
            Profile.Permission.PROPERTY_MANAGE_ASSIGNED,
            Profile.Permission.VIEWING_MANAGE_ASSIGNED,
            Profile.Permission.OWNER_ANNOUNCEMENTS_REVIEW,
        }:
            self.add_error(
                'management_permissions',
                'Brokers may receive only broker-work permissions.',
            )
        if role == Profile.Role.ADMINISTRATOR and permissions - {
            Profile.Permission.USERS_MANAGE,
        }:
            self.add_error(
                'management_permissions',
                'Administrators may only manage broker accounts.',
            )
        if role == Profile.Role.ADMINISTRATOR and not permissions:
            cleaned_data['management_permissions'] = [Profile.Permission.USERS_MANAGE]
        elif role == Profile.Role.BROKER and not permissions:
            cleaned_data['management_permissions'] = [
                Profile.Permission.PROPERTY_MANAGE_ASSIGNED,
                Profile.Permission.VIEWING_MANAGE_ASSIGNED,
                Profile.Permission.OWNER_ANNOUNCEMENTS_REVIEW,
            ]
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

    def __init__(self, *args, profile, actor=None, **kwargs):
        self.profile = profile
        self.actor = actor
        super().__init__(*args, **kwargs)
        if actor and not actor.is_superuser:
            self.fields['role'].choices = [(Profile.Role.BROKER, 'Broker')]
            self.fields['management_permissions'].choices = BROKER_PERMISSIONS
        else:
            choices = BROKER_PERMISSIONS if profile.role == Profile.Role.BROKER else ADMINISTRATOR_PERMISSIONS
            if args and args[0].get('role') == Profile.Role.BROKER:
                choices = BROKER_PERMISSIONS
            self.fields['management_permissions'].choices = choices
        if not self.is_bound:
            self.initial.update({
                'role': profile.role,
                'is_active': profile.user.is_active,
                'management_permissions': effective_management_permissions(profile.user),
            })

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        permissions = set(cleaned_data.get('management_permissions', []))
        if self.actor and not self.actor.is_superuser and role != Profile.Role.BROKER:
            self.add_error('role', 'Administrators may manage broker accounts only.')
        if OWNER_ONLY_PERMISSIONS.intersection(permissions):
            self.add_error('management_permissions', 'These permissions remain owner-only.')
        if role == Profile.Role.BROKER and permissions - {
            Profile.Permission.PROPERTY_MANAGE_ASSIGNED,
            Profile.Permission.VIEWING_MANAGE_ASSIGNED,
            Profile.Permission.OWNER_ANNOUNCEMENTS_REVIEW,
        }:
            self.add_error(
                'management_permissions',
                'Brokers may receive only broker-work permissions.',
            )
        if role == Profile.Role.ADMINISTRATOR and permissions - {
            Profile.Permission.USERS_MANAGE,
        }:
            self.add_error(
                'management_permissions',
                'Administrators may only manage broker accounts.',
            )
        if role == Profile.Role.ADMINISTRATOR and not permissions:
            cleaned_data['management_permissions'] = [Profile.Permission.USERS_MANAGE]
        return cleaned_data
