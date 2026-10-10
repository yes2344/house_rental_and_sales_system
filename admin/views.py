from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import DelegatedAccountInvitation, Profile
from admin.staff_forms import DelegatedAccountCreateForm, DelegatedAccountUpdateForm
from admin.audit import record_admin_action
from user.forms import PropertyForm, ViewingRequestAdminForm
from user.models import Property, PropertyImage, ViewingRequest
from viewings.models import ViewingRequestEvent


def owner_required(view_func):
    return user_passes_test(
        lambda user: user.is_authenticated and user.is_active and user.is_superuser,
        login_url='/admin/login/',
    )(view_func)


@owner_required
def dashboard(request):
    active_count = Property.objects.filter(status__in=['active', 'available']).count()
    inactive_count = Property.objects.filter(status='inactive').count()
    pending_requests = ViewingRequest.objects.filter(
        status__in=[ViewingRequest.Status.PENDING, ViewingRequest.Status.PROPOSED]
    ).count()
    recent_requests = ViewingRequest.objects.select_related('property').order_by('-created_at')[:5]
    return render(request, 'admin/dashboard.html', {
        'active_count': active_count,
        'inactive_count': inactive_count,
        'pending_requests': pending_requests,
        'recent_requests': recent_requests,
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
def viewing_requests(request):
    requests = ViewingRequest.objects.select_related('property').order_by('-created_at')
    return render(request, 'admin/viewing_requests.html', {'requests': requests})


@owner_required
@transaction.atomic
def update_viewing_request(request, pk):
    viewing = get_object_or_404(
        ViewingRequest.objects.select_for_update().select_related('property'),
        id=pk,
    )

    if request.method == 'POST':
        form = ViewingRequestAdminForm(request.POST, instance=viewing)
        if form.is_valid():
            previous_status = viewing.status
            proposal_changed = (
                'proposed_date' in form.changed_data
                or 'proposed_time' in form.changed_data
            )
            viewing_obj = form.save(commit=False)
            if proposal_changed:
                viewing_obj.status = ViewingRequest.Status.PROPOSED
            elif form.cleaned_data['reject_request']:
                viewing_obj.status = ViewingRequest.Status.REJECTED
            viewing_obj.save()
            changes = {}
            if previous_status != viewing_obj.status:
                changes['status'] = {'from': previous_status, 'to': viewing_obj.status}
            if 'proposed_date' in form.changed_data:
                changes['proposed_date'] = 'updated'
            if 'proposed_time' in form.changed_data:
                changes['proposed_time'] = 'updated'
            if 'agent_notes' in form.changed_data:
                changes['agent_notes'] = 'updated'
            if changes:
                record_admin_action(
                    request.user,
                    action='viewing_request_updated',
                    object_type='viewing_request',
                    object_id=viewing_obj.pk,
                    changes=changes,
                )
            if proposal_changed:
                event_type = (
                    ViewingRequestEvent.Type.PROPOSAL_REVISED
                    if previous_status == ViewingRequest.Status.PROPOSED
                    else ViewingRequestEvent.Type.PROPOSAL_SENT
                )
                ViewingRequestEvent.objects.create(
                    viewing_request=viewing_obj,
                    actor=request.user,
                    event_type=event_type,
                    from_status=previous_status,
                    to_status=viewing_obj.status,
                    proposed_date=viewing_obj.proposed_date,
                    proposed_time=viewing_obj.proposed_time,
                )
            elif form.cleaned_data['reject_request'] and previous_status != viewing_obj.status:
                ViewingRequestEvent.objects.create(
                    viewing_request=viewing_obj,
                    actor=request.user,
                    event_type=ViewingRequestEvent.Type.REJECTED,
                    from_status=previous_status,
                    to_status=viewing_obj.status,
                )
            messages.success(request, f'Viewing request for {viewing.property.title} was updated.')
            return redirect('admin_viewing_requests')
    else:
        form = ViewingRequestAdminForm(instance=viewing)

    events = viewing.events.select_related('actor')
    return render(request, 'admin/viewing_request_update.html', {
        'form': form,
        'viewing': viewing,
        'events': events,
        'appointment_timezone': settings.TIME_ZONE,
    })


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


@owner_required
def delegated_accounts(request):
    profiles = Profile.objects.filter(
        role__in=[Profile.Role.ADMINISTRATOR, Profile.Role.BROKER],
        user__is_superuser=False,
    ).select_related('user').order_by('user__username')
    invitation_token = None
    selected_profile = None

    if request.method == 'POST' and request.POST.get('account_id'):
        selected_profile = get_object_or_404(profiles, user_id=request.POST['account_id'])
        form = DelegatedAccountUpdateForm(request.POST, profile=selected_profile)
        if form.is_valid():
            user = selected_profile.user
            before = {
                'role': selected_profile.role,
                'permissions': list(selected_profile.management_permissions),
                'is_active': user.is_active,
            }
            selected_profile.role = form.cleaned_data['role']
            selected_profile.management_permissions = form.cleaned_data['management_permissions']
            selected_profile.broker_approved = selected_profile.role == Profile.Role.BROKER
            user.is_staff = selected_profile.role == Profile.Role.ADMINISTRATOR
            user.is_active = form.cleaned_data['is_active']
            selected_profile.save(update_fields=[
                'role',
                'management_permissions',
                'broker_approved',
                'updated_at',
            ])
            user.save(update_fields=['is_staff', 'is_active'])
            after = {
                'role': selected_profile.role,
                'permissions': list(selected_profile.management_permissions),
                'is_active': user.is_active,
            }
            changes = {
                key: {'from': before[key], 'to': value}
                for key, value in after.items()
                if before[key] != value
            }
            if changes:
                record_admin_action(
                    request.user,
                    action='delegated_account_updated',
                    object_type='user',
                    object_id=user.pk,
                    changes=changes,
                )
            messages.success(request, f'Access updated for {user.get_username()}.')
            return redirect('admin_delegated_accounts')
    elif request.method == 'POST':
        form = DelegatedAccountCreateForm(request.POST)
        if form.is_valid():
            from django.contrib.auth import get_user_model

            User = get_user_model()
            role = form.cleaned_data['role']
            user = User(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                is_active=False,
                is_staff=role == Profile.Role.ADMINISTRATOR,
            )
            user.set_unusable_password()
            user.save()
            profile = Profile.objects.create(
                user=user,
                role=role,
                broker_approved=role == Profile.Role.BROKER,
                management_permissions=form.cleaned_data['management_permissions'],
            )
            invitation, invitation_token = DelegatedAccountInvitation.issue(user, request.user)
            record_admin_action(
                request.user,
                action='delegated_account_created',
                object_type='user',
                object_id=user.pk,
                changes={
                    'role': profile.role,
                    'management_permissions': profile.management_permissions,
                    'is_active': user.is_active,
                },
            )
            messages.success(request, f'Invitation created for {user.get_username()}.')
            form = DelegatedAccountCreateForm()
    elif request.GET.get('account_id'):
        selected_profile = get_object_or_404(profiles, user_id=request.GET['account_id'])
        form = DelegatedAccountUpdateForm(profile=selected_profile)
    else:
        form = DelegatedAccountCreateForm()

    response = render(request, 'admin/delegated_accounts.html', {
        'profiles': profiles,
        'create_form': form if selected_profile is None else DelegatedAccountCreateForm(),
        'edit_form': form if selected_profile is not None else None,
        'selected_profile': selected_profile,
        'invitation_token': invitation_token,
    })
    response['Cache-Control'] = 'no-store'
    response['Referrer-Policy'] = 'no-referrer'
    return response
