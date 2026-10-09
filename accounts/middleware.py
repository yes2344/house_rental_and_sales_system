from django.http import HttpResponseForbidden


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
