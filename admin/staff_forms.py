from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError

from accounts.models import Profile
from accounts.permissions import agent_work_permissions
from properties.models import Location


OWNER_ONLY_PERMISSIONS = {
    Profile.Permission.STAFF_MANAGE,
}


class DelegatedAccountCreateForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput, strip=False)
    assigned_city = forms.ModelChoiceField(
        queryset=Location.objects.filter(
            location_type=Location.Type.CITY,
            is_active=True,
        ),
    )

    def __init__(self, *args, actor=None, **kwargs):
        self.actor = actor
        super().__init__(*args, **kwargs)

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        User = get_user_model()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('A user with this username already exists.')
        return username

    def clean_password(self):
        password = self.cleaned_data['password']
        User = get_user_model()
        candidate_user = User(username=self.cleaned_data.get('username', ''))
        try:
            password_validation.validate_password(password, user=candidate_user)
        except ValidationError as exc:
            raise ValidationError(exc.messages) from exc
        return password

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['role'] = Profile.Role.AGENT
        cleaned_data['management_permissions'] = agent_work_permissions()
        permissions = set(cleaned_data['management_permissions'])
        if OWNER_ONLY_PERMISSIONS.intersection(permissions):
            self.add_error(
                'management_permissions',
                'Delegated-account control remains owner-only.',
            )
        return cleaned_data


class DelegatedAccountUpdateForm(forms.Form):
    username = forms.CharField(max_length=150)
    assigned_city = forms.ModelChoiceField(
        queryset=Location.objects.filter(
            location_type=Location.Type.CITY,
            is_active=True,
        ),
    )
    initial_password = forms.CharField(
        required=False,
        strip=False,
        widget=forms.PasswordInput,
    )
    email = forms.EmailField(required=False)
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    phone = forms.CharField(max_length=50, required=False)
    is_active = forms.BooleanField(required=False)
    def __init__(self, *args, profile, actor=None, **kwargs):
        self.profile = profile
        self.actor = actor
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.initial.update({
                'username': profile.user.username,
                'assigned_city': profile.assigned_city_id,
                'email': profile.user.email,
                'first_name': profile.user.first_name,
                'last_name': profile.user.last_name,
                'phone': profile.phone,
                'is_active': profile.user.is_active,
            })

    def clean_username(self):
        username = self.cleaned_data['username'].strip()
        User = get_user_model()
        if User.objects.filter(username__iexact=username).exclude(pk=self.profile.user_id).exists():
            raise ValidationError('A user with this username already exists.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        User = get_user_model()
        if email and User.objects.filter(email__iexact=email).exclude(pk=self.profile.user_id).exists():
            raise ValidationError('A user with this email already exists.')
        return email

    def clean_initial_password(self):
        password = self.cleaned_data['initial_password']
        if not password:
            return password
        User = get_user_model()
        candidate_user = User(
            username=self.cleaned_data.get('username') or self.profile.user.username,
            email=self.cleaned_data.get('email') or self.profile.user.email,
            first_name=self.cleaned_data.get('first_name') or self.profile.user.first_name,
            last_name=self.cleaned_data.get('last_name') or self.profile.user.last_name,
        )
        try:
            password_validation.validate_password(password, user=candidate_user)
        except ValidationError as exc:
            raise ValidationError(exc.messages) from exc
        return password

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['role'] = Profile.Role.AGENT
        cleaned_data['management_permissions'] = agent_work_permissions()
        return cleaned_data
