"""Compatibility exports for the original server-rendered Django application."""

from properties.models import Amenity, Property, PropertyAgentAssignment, PropertyImage
from viewings.models import ViewingRequest

__all__ = [
    'Amenity',
    'Property',
    'PropertyAgentAssignment',
    'PropertyImage',
    'ViewingRequest',
]
