from django.contrib import messages
from django.contrib.auth import logout
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import Profile, TabSessionToken
from accounts.permissions import can_manage_broker_accounts
from admin.staff_forms import DelegatedAccountCreateForm, DelegatedAccountUpdateForm
from admin.audit import record_admin_action
from user.forms import PropertyForm
from user.models import Property, PropertyImage


def owner_required(view_func):
    def redirect_to_broker_management(request, *args, **kwargs):
        if request.user.is_authenticated and request.user.is_active and request.user.is_superuser:
            return redirect('admin_delegated_accounts')
        return redirect('/admin/login/')

    return redirect_to_broker_management


@require_POST
def portal_logout(request):
    logout(request)
    return redirect('/admin/login/')


@owner_required
def dashboard(request):
    active_count = Property.objects.filter(status__in=['active', 'available']).count()
    inactive_count = Property.objects.filter(status='inactive').count()
    return render(request, 'admin/dashboard.html', {
        'active_count': active_count,
        'inactive_count': inactive_count,
    })


@owner_required
def property_list(request):
    properties = Property.objects.filter(
        service_type=Property.ServiceType.BROKER_MANAGED,
    ).order_by('-created_at')
    return render(request, 'admin/property_list.html', {'properties': properties})


@owner_required
@transaction.atomic
def property_form(request, pk=None):
    property_obj = get_object_or_404(
        Property,
        id=pk,
        service_type=Property.ServiceType.BROKER_MANAGED,
    ) if pk else None
    if request.method == 'POST':
        form = PropertyForm(request.POST, request.FILES, instance=property_obj)
        if form.is_valid():
            property_instance = form.save()
            if pk is None:
                property_instance.publication_status = Property.PublicationStatus.PUBLISHED
                property_instance.save(update_fields=['publication_status', 'updated_at'])
            action = 'property_updated' if pk else 'property_created'
            record_admin_action(
                request.user,
                action=action,
                object_type='property',
                object_id=property_instance.pk,
                changes={'fields': list(form.changed_data)},
            )
            uploaded_files = form.cleaned_data.get('images', [])
            if uploaded_files:
                current_images = property_instance.images.count()
                for image in uploaded_files[:10 - current_images]:
                    PropertyImage.objects.create(property=property_instance, image=image)

            messages.success(request, 'Property saved successfully.')
            return redirect('admin_property_list')
    else:
        form = PropertyForm(instance=property_obj)

    return render(request, 'admin/property_form.html', {'form': form, 'property': property_obj})


@owner_required
@require_POST
def toggle_property(request, pk):
    property_obj = get_object_or_404(Property, pk=pk)
    old_status = property_obj.status
    property_obj.status = (
        Property.Status.AVAILABLE if property_obj.status == Property.Status.INACTIVE else Property.Status.INACTIVE
    )
    property_obj.save(update_fields=['status', 'updated_at'])
    record_admin_action(
        request.user,
        action='property_status_changed',
        object_type='property',
        object_id=property_obj.pk,
        changes={'status': {'from': old_status, 'to': property_obj.status}},
    )
    messages.success(request, f'{property_obj.title} status updated.')
    return redirect('admin_property_list')


@owner_required
@require_POST
def delete_property(request, pk):
    property_obj = get_object_or_404(Property, pk=pk)
    property_id = property_obj.pk
    for image in property_obj.images.all():
        image.image.delete(save=False)
    record_admin_action(
        request.user,
        action='property_deleted',
        object_type='property',
        object_id=property_id,
        changes={'title': property_obj.title},
    )
    property_obj.delete()
    messages.success(request, f'{property_obj.title} was deleted.')
    return redirect('admin_property_list')


def delegated_accounts(request):
    if not can_manage_broker_accounts(request.user):
        return redirect('/')

    profiles = Profile.objects.filter(
        role=Profile.Role.BROKER,
        user__is_staff=False,
        user__is_superuser=False,
    )
    profiles = profiles.select_related('user').order_by('user__username')
    selected_profile = None

    if request.method == 'POST' and request.POST.get('delete_account_id'):
        selected_profile = get_object_or_404(profiles, user_id=request.POST['delete_account_id'])
        user = selected_profile.user
        record_admin_action(
            request.user,
            action='broker_account_deleted',
            object_type='user',
            object_id=user.pk,
            changes={'username': user.username},
        )
        user.delete()
        messages.success(request, 'Agent account deleted.')
        return redirect('admin_delegated_accounts')

    if request.method == 'POST' and request.POST.get('account_id'):
        selected_profile = get_object_or_404(profiles, user_id=request.POST['account_id'])
        form = DelegatedAccountUpdateForm(request.POST, profile=selected_profile, actor=request.user)
        if form.is_valid():
            user = selected_profile.user
            was_active = user.is_active
            before = {
                'username': user.username,
                'assigned_city_id': selected_profile.assigned_city_id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'phone': selected_profile.phone,
                'is_active': user.is_active,
                'broker_onboarding_required': selected_profile.broker_onboarding_required,
                'broker_password_changed': selected_profile.broker_password_changed,
            }
            user.username = form.cleaned_data['username']
            selected_profile.assigned_city = form.cleaned_data['assigned_city']
            user.email = form.cleaned_data['email']
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.is_staff = False
            user.is_active = form.cleaned_data['is_active']
            reset_password = form.cleaned_data['initial_password']
            if reset_password:
                user.set_password(reset_password)
                selected_profile.broker_approved = False
                selected_profile.broker_onboarding_required = True
                selected_profile.broker_password_changed = False
            selected_profile.phone = form.cleaned_data['phone']
            selected_profile.save(update_fields=[
                'phone',
                'assigned_city',
                'broker_approved',
                'broker_onboarding_required',
                'broker_password_changed',
                'updated_at',
            ])
            user.save(update_fields=[
                'username',
                'email',
                'first_name',
                'last_name',
                'is_staff',
                'is_active',
                *(['password'] if reset_password else []),
            ])
            if (was_active and not user.is_active) or reset_password:
                TabSessionToken.objects.filter(
                    user=user,
                    revoked_at__isnull=True,
                ).update(revoked_at=timezone.now())
            after = {
                'username': user.username,
                'assigned_city_id': selected_profile.assigned_city_id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'phone': selected_profile.phone,
                'is_active': user.is_active,
                'broker_onboarding_required': selected_profile.broker_onboarding_required,
                'broker_password_changed': selected_profile.broker_password_changed,
            }
            changes = {
                key: {'from': before[key], 'to': value}
                for key, value in after.items()
                if before[key] != value
            }
            if changes:
                record_admin_action(
                    request.user,
                    action='broker_account_updated',
                    object_type='user',
                    object_id=user.pk,
                    changes=changes,
                )
            messages.success(request, f'Access updated for {user.get_username()}.')
            return redirect('admin_delegated_accounts')
    elif request.method == 'POST':
        form = DelegatedAccountCreateForm(request.POST, actor=request.user)
        if form.is_valid():
            from django.contrib.auth import get_user_model

            User = get_user_model()
            role = form.cleaned_data['role']
            user = User(
                username=form.cleaned_data['username'],
        is_active=True,
        is_staff=False,
            )
            user.set_password(form.cleaned_data['password'])
            user.save()
            profile = Profile.objects.create(
        user=user,
        role=role,
        assigned_city=form.cleaned_data['assigned_city'],
        broker_approved=False,
        broker_onboarding_required=True,
        broker_password_changed=False,
        management_permissions=form.cleaned_data['management_permissions'],
            )
            record_admin_action(
                request.user,
        action='broker_account_created',
                object_type='user',
                object_id=user.pk,
                changes={
                    'role': profile.role,
                    'assigned_city_id': profile.assigned_city_id,
                    'management_permissions': profile.management_permissions,
                    'is_active': user.is_active,
            'broker_onboarding_required': profile.broker_onboarding_required,
        },
            )
            messages.success(request, f'Agent account created for {user.get_username()}.')
            form = DelegatedAccountCreateForm(actor=request.user)
    elif request.GET.get('account_id'):
        selected_profile = get_object_or_404(profiles, user_id=request.GET['account_id'])
        form = DelegatedAccountUpdateForm(profile=selected_profile, actor=request.user)
    else:
        form = DelegatedAccountCreateForm(actor=request.user)

    response = render(request, 'admin/delegated_accounts.html', {
        'profiles': profiles,
        'create_form': form if selected_profile is None else DelegatedAccountCreateForm(actor=request.user),
        'edit_form': form if selected_profile is not None else None,
        'selected_profile': selected_profile,
        'is_platform_owner': False,
    })
    response['Cache-Control'] = 'no-store'
    response['Referrer-Policy'] = 'no-referrer'
    return response
