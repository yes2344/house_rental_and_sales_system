import hashlib
import re
import secrets
from decimal import Decimal
from urllib.parse import urlencode

from django.db import transaction
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from admin.models import BrokerageSettings, HomepageNote, SocialMediaLink
from .forms import ViewingRequestForm
from .models import Property, ViewingRequest
from viewings.models import ViewingRequestEvent
from viewings.serializers import appointment_is_in_past
from properties.access import public_properties


STOPWORDS = {
    'the', 'and', 'for', 'with', 'this', 'that', 'from', 'your', 'home', 'house',
    'in', 'at', 'near', 'where', 'want', 'need', 'find', 'looking', 'room', 'rooms',
    'bed', 'bath', 'price', 'list', 'property', 'properties'
}


def _public_properties():
    return public_properties()


def _public_context(**context):
    return {
        **context,
        'brokerage_contact': BrokerageSettings.objects.filter(pk=1).first(),
        'brokerage_social_links': SocialMediaLink.objects.filter(
            brokerage_id=1,
            is_enabled=True,
        ).order_by('display_order', 'platform'),
        'homepage_notes': HomepageNote.objects.filter(
            is_published=True,
        ).order_by('display_order', '-created_at'),
    }


def _public_map_embed_url(property_obj):
    if not property_obj.has_public_coordinates:
        return ''
    latitude = property_obj.latitude
    longitude = property_obj.longitude
    offset = Decimal('0.004')
    bounds = (
        max(Decimal('-180'), longitude - offset),
        max(Decimal('-90'), latitude - offset),
        min(Decimal('180'), longitude + offset),
        min(Decimal('90'), latitude + offset),
    )
    query = urlencode({
        'bbox': ','.join(f'{coordinate:.6f}' for coordinate in bounds),
        'layer': 'mapnik',
        'marker': f'{latitude:.6f},{longitude:.6f}',
    })
    return f'https://www.openstreetmap.org/export/embed.html?{query}'


def _public_owner_contact(property_obj):
    if property_obj.service_type != Property.ServiceType.OWNER_ANNOUNCED:
        return None
    announcement = property_obj.owner_announcement
    today = timezone.localdate()
    agreement_is_public = any(
        agreement.status == 'active'
        and agreement.start_date <= today <= agreement.end_date
        and agreement.public_contact_visible
        for agreement in announcement.agreements.all()
    )
    if not (announcement.public_contact_visible and agreement_is_public):
        return None
    return {
        'name': announcement.public_contact_name,
        'phone': announcement.public_contact_phone,
        'email': announcement.public_contact_email,
    }


def _smart_search(query):
    if not query:
        return _public_properties().order_by('-is_featured', '-created_at')

    terms = [word.lower() for word in re.findall(r"[a-zA-Z0-9]+", query) if len(word) > 2 and word.lower() not in STOPWORDS]
    if not terms:
        return _public_properties().order_by('-is_featured', '-created_at')

    queryset = _public_properties()
    scored = []

    for property_obj in queryset:
        text = ' '.join([
            property_obj.title,
            property_obj.location,
            property_obj.property_type,
            property_obj.description,
            property_obj.features,
        ]).lower()

        score = 0
        for term in terms:
            if term in text:
                score += 1
            if term in property_obj.title.lower():
                score += 4
            if term in property_obj.location.lower():
                score += 3
            if term in property_obj.features.lower():
                score += 2

        if score > 0:
            scored.append((score, property_obj))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [property_obj for _, property_obj in scored]


def home(request):
    featured = _public_properties().order_by('-is_featured', '-created_at')[:6]
    return render(request, 'user/home.html', _public_context(featured=featured))


def listings(request):
    query = request.GET.get('q', '').strip()
    properties = _smart_search(query)
    return render(
        request,
        'user/listings.html',
        _public_context(properties=properties, query=query),
    )


def property_detail(request, slug):
    property_obj = get_object_or_404(_public_properties(), slug=slug)
    images = property_obj.images.all().order_by('id')
    return render(
        request,
        'user/property_detail.html',
        _public_context(
            property=property_obj,
            images=images,
            property_map_embed_url=_public_map_embed_url(property_obj),
            public_owner_contact=_public_owner_contact(property_obj),
        ),
    )


@never_cache
def viewing_request(request, property_id=None):
    property_obj = None
    if property_id:
        property_obj = get_object_or_404(
            Property.objects.filter(
                publication_status=Property.PublicationStatus.PUBLISHED,
                status__in=[Property.Status.AVAILABLE, Property.Status.LEGACY_ACTIVE],
            ),
            id=property_id,
        )

    if request.method == 'POST':
        form = ViewingRequestForm(request.POST)
        if form.is_valid():
            selected = request.POST.get('property_id') or (property_obj.pk if property_obj else None)
            if isinstance(selected, str) and not selected.isdecimal():
                selected = None
            public_properties = Property.objects.filter(
                publication_status=Property.PublicationStatus.PUBLISHED,
                status__in=[Property.Status.AVAILABLE, Property.Status.LEGACY_ACTIVE],
            )
            property_ref = public_properties.filter(pk=selected).first() if selected else None
            if property_ref is None:
                form.add_error(None, 'Select an available property before submitting a request.')
            else:
                receipt_token = secrets.token_urlsafe(32)
                with transaction.atomic():
                    viewing = form.save(commit=False)
                    viewing.property = property_ref
                    viewing.requester = request.user if request.user.is_authenticated else None
                    viewing.receipt_token_digest = hashlib.sha256(receipt_token.encode()).hexdigest()
                    viewing.save()
                    ViewingRequestEvent.objects.create(
                        viewing_request=viewing,
                        actor=viewing.requester,
                        event_type=ViewingRequestEvent.Type.SUBMITTED,
                        to_status=viewing.status,
                    )
                return render(
                    request,
                    'user/viewing_request_receipt.html',
                    _public_context(viewing=viewing, receipt_token=receipt_token),
                )
    else:
        form = ViewingRequestForm(initial={'property_id': property_obj.id if property_obj else None})

    return render(
        request,
        'user/viewing_request.html',
        _public_context(
            form=form,
            property=property_obj,
            property_list=Property.objects.filter(
                publication_status=Property.PublicationStatus.PUBLISHED,
                status__in=[Property.Status.AVAILABLE, Property.Status.LEGACY_ACTIVE],
            ).order_by('-created_at'),
        ),
    )


@never_cache
@require_http_methods(['GET', 'POST'])
def viewing_request_status(request):
    receipt_token = ''
    viewing = None
    error = ''
    if request.method == 'POST':
        receipt_token = request.POST.get('receipt_token', '').strip()
        if receipt_token and len(receipt_token) <= 200:
            digest = hashlib.sha256(receipt_token.encode()).hexdigest()
            decision = request.POST.get('decision')
            with transaction.atomic():
                queryset = ViewingRequest.objects.select_related('property')
                if decision in ('accept', 'decline'):
                    queryset = queryset.select_for_update()
                viewing = queryset.filter(receipt_token_digest=digest).first()
                if viewing and decision in ('accept', 'decline'):
                    if viewing.status != ViewingRequest.Status.PROPOSED:
                        error = 'There is no pending appointment proposal to decide.'
                        viewing = None
                    elif decision == 'accept' and appointment_is_in_past(
                        viewing.proposed_date,
                        viewing.proposed_time,
                    ):
                        error = 'This appointment proposal has expired. Contact the property manager.'
                        viewing = None
                    else:
                        previous_status = viewing.status
                        if decision == 'accept':
                            viewing.status = ViewingRequest.Status.CONFIRMED
                            viewing.scheduled_date = viewing.proposed_date
                            viewing.scheduled_time = viewing.proposed_time
                            event_type = ViewingRequestEvent.Type.PROPOSAL_ACCEPTED
                        else:
                            viewing.status = ViewingRequest.Status.DECLINED
                            event_type = ViewingRequestEvent.Type.PROPOSAL_DECLINED
                        viewing.guest_responded_at = timezone.now()
                        viewing.save(update_fields=[
                            'status',
                            'scheduled_date',
                            'scheduled_time',
                            'guest_responded_at',
                        ])
                        ViewingRequestEvent.objects.create(
                            viewing_request=viewing,
                            event_type=event_type,
                            from_status=previous_status,
                            to_status=viewing.status,
                            proposed_date=viewing.proposed_date,
                            proposed_time=viewing.proposed_time,
                        )
        else:
            error = 'Enter the private receipt token provided when the request was submitted.'
        if viewing is None and not error:
            error = 'The request could not be found. Check the private receipt token and try again.'

    return render(
        request,
        'user/viewing_request_status.html',
        _public_context(
            receipt_token=receipt_token,
            viewing=viewing,
            error=error,
            appointment_timezone=timezone.get_current_timezone_name(),
        ),
    )
