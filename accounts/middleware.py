from django.http import HttpResponseForbidden


from django.conf import settings
from django.middleware.csrf import CsrfViewMiddleware


class LocalInvitationCsrfViewMiddleware(CsrfViewMiddleware):
    def process_view(self, request, callback, callback_args, callback_kwargs):
        if (
            settings.DEBUG
            and request.method == 'POST'
            and request.path == '/admin-portal/delegated-accounts/'
            and request.META.get('HTTP_ORIGIN') == 'null'
        ):
            # Keep Django's CSRF cookie/token checks, but support local opaque-origin form hosts.
            request.META.pop('HTTP_ORIGIN')
        return super().process_view(request, callback, callback_args, callback_kwargs)


class OwnerOnlyDjangoAdminMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.path.startswith('/admin/')
            and request.user.is_authenticated
            and not (request.user.is_active and request.user.is_superuser)
        ):
            return HttpResponseForbidden('Django administration is reserved for the platform owner.')
        return self.get_response(request)
