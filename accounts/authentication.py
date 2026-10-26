import hashlib

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from accounts.models import TabSessionToken


class TabSessionAuthentication(BaseAuthentication):
    def authenticate(self, request):
        authorization = get_authorization_header(request).split()
        if not authorization:
            return None
        if authorization[0].lower() != b'bearer':
            return None
        if len(authorization) != 2:
            raise AuthenticationFailed('Invalid session authorization header.')

        try:
            token = authorization[1].decode('ascii')
        except UnicodeDecodeError as error:
            raise AuthenticationFailed('Invalid session token.') from error

        digest = hashlib.sha256(token.encode('utf-8')).hexdigest()
        try:
            session_token = TabSessionToken.objects.select_related('user').get(
                token_digest=digest,
                revoked_at__isnull=True,
                expires_at__gt=timezone.now(),
                user__is_active=True,
            )
        except TabSessionToken.DoesNotExist as error:
            raise AuthenticationFailed('Invalid or expired session token.') from error

        return session_token.user, session_token
