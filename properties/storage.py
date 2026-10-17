import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage, Storage
from django.utils.deconstruct import deconstructible


class PrivateCloudinaryStorage(Storage):
    def __init__(self):
        import cloudinary_storage.app_settings as cloudinary_settings

        self.prefix = cloudinary_settings.PREFIX.lstrip('/')
        self.tag = cloudinary_settings.MEDIA_TAG

    def _name(self, name):
        name = name.replace('\\', '/').lstrip('/')
        prefix = f'{self.prefix.rstrip("/")}/' if self.prefix else ''
        return name if not prefix or name.startswith(prefix) else f'{prefix}{name}'

    def _get_url(self, name):
        import cloudinary

        return cloudinary.utils.cloudinary_url(
            self._name(name),
            resource_type='image',
            type='private',
            sign_url=True,
            secure=True,
        )[0]

    def _open(self, name, mode='rb'):
        import requests
        from django.core.files.base import ContentFile

        response = requests.get(self._get_url(name), timeout=30)
        response.raise_for_status()
        file = ContentFile(response.content)
        file.name = name
        file.mode = mode
        return file

    def _save(self, name, content):
        import cloudinary

        name = self._name(name)
        options = {
            'type': 'private',
            'use_filename': True,
            'resource_type': 'image',
            'tags': self.tag,
        }
        folder = os.path.dirname(name)
        if folder:
            options['folder'] = folder
        response = cloudinary.uploader.upload(content, **options)
        return response['public_id']

    def delete(self, name):
        import cloudinary

        response = cloudinary.uploader.destroy(
            self._name(name),
            invalidate=True,
            resource_type='image',
            type='private',
        )
        return response['result'] == 'ok'

    def exists(self, name):
        import requests

        response = requests.head(self._get_url(name), timeout=30)
        if response.status_code == 404:
            return False
        response.raise_for_status()
        return True

    def size(self, name):
        import requests

        response = requests.head(self._get_url(name), timeout=30)
        if response.status_code == 404:
            raise FileNotFoundError(name)
        response.raise_for_status()
        return int(response.headers['content-length'])

    def url(self, name):
        return self._get_url(name)

    def get_available_name(self, name, max_length=None):
        return name if max_length is None else name[:max_length]


@deconstructible
class PrivatePropertyImageStorage(Storage):
    def __init__(self):
        self._backend_config = None
        self._backend = None

    @property
    def backend(self):
        backend_config = (bool(settings.CLOUDINARY_URL), str(settings.PRIVATE_MEDIA_ROOT))
        if backend_config != self._backend_config:
            self._backend = (
                PrivateCloudinaryStorage()
                if settings.CLOUDINARY_URL
                else FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT)
            )
            self._backend_config = backend_config
        return self._backend

    def _open(self, name, mode='rb'):
        return self.backend.open(name, mode)

    def _save(self, name, content):
        return self.backend.save(name, content)

    def delete(self, name):
        return self.backend.delete(name)

    def exists(self, name):
        return self.backend.exists(name)

    def size(self, name):
        return self.backend.size(name)

    def url(self, name):
        return self.backend.url(name)

    def path(self, name):
        return self.backend.path(name)

    def get_available_name(self, name, max_length=None):
        return self.backend.get_available_name(name, max_length)

    def listdir(self, path):
        return self.backend.listdir(path)


private_property_image_storage = PrivatePropertyImageStorage()
