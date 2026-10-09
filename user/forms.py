from django import forms

from .models import Property, ViewingRequest


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs['multiple'] = 'multiple'


class PropertyForm(forms.ModelForm):
    images = forms.FileField(
        required=False,
        widget=MultipleFileInput(attrs={'accept': 'image/*'}),
    )

    class Meta:
        model = Property
        fields = [
            'title',
            'location',
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
        if len(files) > 10:
            raise forms.ValidationError('You can upload up to 10 photos per property.')
        return files


class ViewingRequestForm(forms.ModelForm):
    class Meta:
        model = ViewingRequest
        fields = ['full_name', 'email', 'phone', 'preferred_date', 'preferred_time', 'message']
        widgets = {
            'preferred_date': forms.DateInput(attrs={'type': 'date'}),
            'preferred_time': forms.TimeInput(attrs={'type': 'time'}),
            'message': forms.Textarea(attrs={'rows': 5}),
        }


class ViewingRequestAdminForm(forms.ModelForm):
    class Meta:
        model = ViewingRequest
        fields = ['status', 'scheduled_date', 'scheduled_time', 'agent_notes']
        widgets = {
            'scheduled_date': forms.DateInput(attrs={'type': 'date'}),
            'scheduled_time': forms.TimeInput(attrs={'type': 'time'}),
            'agent_notes': forms.Textarea(attrs={'rows': 4}),
        }
