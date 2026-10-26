from django.conf import settings
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.utils.cache import patch_vary_headers


class LocalInvitationOriginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            settings.DEBUG
            and request.method == 'POST'
            and request.path == '/admin-portal/delegated-accounts/'
            and request.META.get('HTTP_ORIGIN') == 'null'
        ):
            request.META.pop('HTTP_ORIGIN')
        return self.get_response(request)


class ApiCorsMiddleware:
    allowed_methods = frozenset({'DELETE', 'GET', 'HEAD', 'OPTIONS', 'PATCH', 'POST', 'PUT'})
    allowed_headers = frozenset({'authorization', 'content-type', 'x-csrftoken'})

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.headers.get('Origin')
        if (
            not origin
            or origin not in settings.CORS_ALLOWED_ORIGINS
            or not request.path.startswith('/api/')
        ):
            return self.get_response(request)

        if request.method == 'OPTIONS' and request.headers.get('Access-Control-Request-Method'):
            requested_method = request.headers['Access-Control-Request-Method'].upper()
            requested_headers = {
                header.strip().lower()
                for header in request.headers.get('Access-Control-Request-Headers', '').split(',')
                if header.strip()
            }
            if (
                requested_method not in self.allowed_methods
                or not requested_headers.issubset(self.allowed_headers)
            ):
                response = HttpResponse(status=403)
            else:
                response = HttpResponse(status=204)
                response['Access-Control-Allow-Methods'] = ', '.join(sorted(self.allowed_methods))
                response['Access-Control-Allow-Headers'] = ', '.join(sorted(self.allowed_headers))
                response['Access-Control-Max-Age'] = '600'
        else:
            response = self.get_response(request)

        response['Access-Control-Allow-Origin'] = origin
        response['Access-Control-Allow-Credentials'] = 'true'
        patch_vary_headers(response, ('Origin',))
        return response


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
