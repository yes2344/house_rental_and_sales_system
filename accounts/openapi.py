from drf_spectacular.extensions import OpenApiAuthenticationExtension


class TabSessionAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = 'accounts.authentication.TabSessionAuthentication'
    name = 'tabSessionAuth'

    def get_security_definition(self, auto_schema):
        return {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'opaque session token',
        }
