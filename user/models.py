"""Compatibility exports for the original server-rendered Django application."""

from properties.models import Amenity, Property, PropertyBrokerAssignment, PropertyImage
from viewings.models import ViewingRequest

__all__ = [
    'Amenity',
    'Property',
    'PropertyBrokerAssignment',
    'PropertyImage',
    'ViewingRequest',
]
