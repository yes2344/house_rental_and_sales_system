import re

from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ViewingRequestForm
from .models import Property, ViewingRequest


STOPWORDS = {
    'the', 'and', 'for', 'with', 'this', 'that', 'from', 'your', 'home', 'house',
    'in', 'at', 'near', 'where', 'want', 'need', 'find', 'looking', 'room', 'rooms',
    'bed', 'bath', 'price', 'list', 'property', 'properties'
}


def _smart_search(query):
    if not query:
        return Property.objects.filter(status='active').order_by('-is_featured', '-created_at')

    terms = [word.lower() for word in re.findall(r"[a-zA-Z0-9]+", query) if len(word) > 2 and word.lower() not in STOPWORDS]
    if not terms:
        return Property.objects.filter(status='active').order_by('-is_featured', '-created_at')

    queryset = Property.objects.filter(status='active')
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
    featured = Property.objects.filter(status='active').order_by('-is_featured', '-created_at')[:6]
    return render(request, 'user/home.html', {'featured': featured})


def listings(request):
    query = request.GET.get('q', '').strip()
    properties = _smart_search(query)
    context = {'properties': properties, 'query': query}
    return render(request, 'user/listings.html', context)


def property_detail(request, slug):
    property_obj = get_object_or_404(Property, slug=slug, status='active')
    images = property_obj.images.all().order_by('id')
    return render(request, 'user/property_detail.html', {'property': property_obj, 'images': images})


def viewing_request(request, property_id=None):
    property_obj = None
    if property_id:
        property_obj = get_object_or_404(Property, id=property_id, status='active')

    if request.method == 'POST':
        form = ViewingRequestForm(request.POST)
        if form.is_valid():
            viewing = form.save(commit=False)
            selected = request.POST.get('property_id')
            property_ref = get_object_or_404(Property, id=selected, status='active') if selected else property_obj
            viewing.property = property_ref
            viewing.save()
            messages.success(request, 'Your viewing request has been submitted successfully.')
            return redirect('user_property_detail', slug=property_ref.slug)
    else:
        form = ViewingRequestForm(initial={'property_id': property_obj.id if property_obj else None})

    return render(request, 'user/viewing_request.html', {
        'form': form,
        'property': property_obj,
        'property_list': Property.objects.filter(status='active').order_by('-created_at'),
    })
