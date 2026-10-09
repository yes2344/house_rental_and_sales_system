from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from admin.audit import record_admin_action
from user.forms import PropertyForm, ViewingRequestAdminForm
from user.models import Property, PropertyImage, ViewingRequest


@staff_member_required
def dashboard(request):
    active_count = Property.objects.filter(status__in=['active', 'available']).count()
    inactive_count = Property.objects.filter(status='inactive').count()
    pending_requests = ViewingRequest.objects.filter(status='pending').count()
    recent_requests = ViewingRequest.objects.select_related('property').order_by('-created_at')[:5]
    return render(request, 'admin/dashboard.html', {
        'active_count': active_count,
        'inactive_count': inactive_count,
        'pending_requests': pending_requests,
        'recent_requests': recent_requests,
    })


@staff_member_required
def property_list(request):
    properties = Property.objects.all().order_by('-created_at')
    return render(request, 'admin/property_list.html', {'properties': properties})


@staff_member_required
def property_form(request, pk=None):
    property_obj = get_object_or_404(Property, id=pk) if pk else None
    if request.method == 'POST':
        form = PropertyForm(request.POST, request.FILES, instance=property_obj)
        if form.is_valid():
            property_instance = form.save()
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


@staff_member_required
def viewing_requests(request):
    requests = ViewingRequest.objects.select_related('property').order_by('-created_at')
    return render(request, 'admin/viewing_requests.html', {'requests': requests})


@staff_member_required
def update_viewing_request(request, pk):
    viewing = get_object_or_404(ViewingRequest, id=pk)

    if request.method == 'POST':
        form = ViewingRequestAdminForm(request.POST, instance=viewing)
        if form.is_valid():
            previous_status = viewing.status
            viewing_obj = form.save(commit=False)
            if viewing_obj.status == 'confirmed':
                if not viewing_obj.scheduled_date:
                    viewing_obj.scheduled_date = viewing_obj.preferred_date
                if not viewing_obj.scheduled_time:
                    viewing_obj.scheduled_time = viewing_obj.preferred_time
            viewing_obj.save()
            changes = {}
            if previous_status != viewing_obj.status:
                changes['status'] = {'from': previous_status, 'to': viewing_obj.status}
            if 'scheduled_date' in form.changed_data:
                changes['scheduled_date'] = 'updated'
            if 'scheduled_time' in form.changed_data:
                changes['scheduled_time'] = 'updated'
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
            messages.success(request, f'Viewing request for {viewing.property.title} was updated.')
            return redirect('admin_viewing_requests')
    else:
        form = ViewingRequestAdminForm(
            instance=viewing,
            initial={
                'scheduled_date': viewing.preferred_date,
                'scheduled_time': viewing.preferred_time,
            },
        )

    return render(request, 'admin/viewing_request_update.html', {'form': form, 'viewing': viewing})


@staff_member_required
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


@staff_member_required
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
