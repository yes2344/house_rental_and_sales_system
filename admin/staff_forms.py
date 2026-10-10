from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from accounts.models import Profile
from accounts.permissions import broker_work_permissions


OWNER_ONLY_PERMISSIONS = {
    Profile.Permission.STAFF_MANAGE,
}


class DelegatedAccountCreateForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    role = forms.ChoiceField(choices=[
        (Profile.Role.ADMINISTRATOR, 'Administrator'),
        (Profile.Role.BROKER, 'Broker'),
    ], help_text='Administrators manage broker accounts. Approved brokers manage marketplace operations; delegated-account control remains owner-only.')
    def __init__(self, *args, actor=None, **kwargs):
        self.actor = actor
        super().__init__(*args, **kwargs)
        if actor and not actor.is_superuser:
            self.fields['role'].choices = [(Profile.Role.BROKER, 'Broker')]
            self.fields['role'].initial = Profile.Role.BROKER

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
        permissions = set()
        if role == Profile.Role.BROKER:
            cleaned_data['management_permissions'] = broker_work_permissions()
            permissions = set(cleaned_data['management_permissions'])
        if self.actor and not self.actor.is_superuser and role != Profile.Role.BROKER:
            self.add_error('role', 'Administrators may manage broker accounts only.')
        if OWNER_ONLY_PERMISSIONS.intersection(permissions):
            self.add_error(
                'management_permissions',
                'Delegated-account control remains owner-only.',
            )
        if role == Profile.Role.ADMINISTRATOR and not permissions:
            cleaned_data['management_permissions'] = [Profile.Permission.USERS_MANAGE]
        return cleaned_data


class DelegatedAccountUpdateForm(forms.Form):
    role = forms.ChoiceField(choices=[
        (Profile.Role.ADMINISTRATOR, 'Administrator'),
        (Profile.Role.BROKER, 'Broker'),
    ], help_text='Administrators manage broker accounts. Approved brokers manage marketplace operations; delegated-account control remains owner-only.')
    is_active = forms.BooleanField(required=False)
    def __init__(self, *args, profile, actor=None, **kwargs):
        self.profile = profile
        self.actor = actor
        super().__init__(*args, **kwargs)
        if actor and not actor.is_superuser:
            self.fields['role'].choices = [(Profile.Role.BROKER, 'Broker')]
        if not self.is_bound:
            self.initial.update({
                'role': profile.role,
                'is_active': profile.user.is_active,
            })

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        permissions = set()
        if role == Profile.Role.BROKER:
            cleaned_data['management_permissions'] = broker_work_permissions()
            permissions = set(cleaned_data['management_permissions'])
        if self.actor and not self.actor.is_superuser and role != Profile.Role.BROKER:
            self.add_error('role', 'Administrators may manage broker accounts only.')
        if OWNER_ONLY_PERMISSIONS.intersection(permissions):
            self.add_error('management_permissions', 'These permissions remain owner-only.')
        if role == Profile.Role.ADMINISTRATOR and not permissions:
            cleaned_data['management_permissions'] = [Profile.Permission.USERS_MANAGE]
        return cleaned_data
