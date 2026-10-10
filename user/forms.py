from django import forms

from .models import Property, ViewingRequest
from viewings.serializers import appointment_is_in_past


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs['multiple'] = 'multiple'


class MultipleFileField(forms.FileField):
    def clean(self, data, initial=None):
        if not data:
            return []
        files = data if isinstance(data, (list, tuple)) else [data]
        return [super().clean(file, initial) for file in files]


class PropertyForm(forms.ModelForm):
    images = MultipleFileField(
        required=False,
        widget=MultipleFileInput(attrs={'accept': 'image/*'}),
    )

    class Meta:
        model = Property
        fields = [
            'title',
            'location',
            'latitude',
            'longitude',
            'exact_location_is_public',
            'property_type',
            'listing_type',
            'price',
            'bedrooms',
            'bathrooms',
            'area_sqft',
            'description',
            'features',
            'status',
            'is_featured',
        ]

    def clean_images(self):
        files = self.files.getlist('images')
        existing_images = self.instance.images.count() if self.instance and self.instance.pk else 0
        if existing_images + len(files) > 10:
            raise forms.ValidationError(
                'A property can have up to 10 photos in total. Remove existing photos before adding more.'
            )
        return files

    def clean(self):
        cleaned_data = super().clean()
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')
        if (latitude is None) != (longitude is None):
            self.add_error('latitude', 'Enter both latitude and longitude, or leave both blank.')
        return cleaned_data


class ViewingRequestForm(forms.ModelForm):
    class Meta:
        model = ViewingRequest
        fields = ['full_name', 'email', 'phone', 'preferred_date', 'preferred_time', 'message']
        widgets = {
            'preferred_date': forms.DateInput(attrs={'type': 'date'}),
            'preferred_time': forms.TimeInput(attrs={'type': 'time'}),
            'message': forms.Textarea(attrs={'rows': 5}),
        }

    def clean(self):
        cleaned_data = super().clean()
        preferred_date = cleaned_data.get('preferred_date')
        preferred_time = cleaned_data.get('preferred_time')
        if preferred_date and appointment_is_in_past(preferred_date, preferred_time):
            self.add_error('preferred_time', 'Preferred appointment time cannot be in the past.')
        return cleaned_data


class ViewingRequestAdminForm(forms.ModelForm):
    reject_request = forms.BooleanField(required=False)

    class Meta:
        model = ViewingRequest
        fields = ['proposed_date', 'proposed_time', 'agent_notes']
        widgets = {
            'proposed_date': forms.DateInput(attrs={'type': 'date'}),
            'proposed_time': forms.TimeInput(attrs={'type': 'time'}),
            'agent_notes': forms.Textarea(attrs={'rows': 4}),
        }

    def clean(self):
        cleaned_data = super().clean()
        proposed_date = cleaned_data.get('proposed_date')
        proposed_time = cleaned_data.get('proposed_time')
        proposal_changed = (
            proposed_date != self.instance.proposed_date
            or proposed_time != self.instance.proposed_time
        )
        if proposal_changed and (not proposed_date or not proposed_time):
            self.add_error('proposed_date', 'A proposal needs both a date and a time.')
        if proposal_changed and self.instance.status == ViewingRequest.Status.CONFIRMED:
            self.add_error('proposed_date', 'A confirmed appointment cannot be changed.')
        if cleaned_data.get('reject_request') and proposal_changed:
            self.add_error('reject_request', 'Reject the request or propose a time, not both.')
        if cleaned_data.get('reject_request') and self.instance.status in (
            ViewingRequest.Status.CONFIRMED,
            ViewingRequest.Status.DECLINED,
        ):
            self.add_error('reject_request', 'A completed visitor decision cannot be rejected.')
        if proposed_date and proposed_time:
            if appointment_is_in_past(proposed_date, proposed_time):
                self.add_error('proposed_time', 'Proposed appointment time cannot be in the past.')
        return cleaned_data
