import logging
import smtplib
from binascii import Error as Base64DecodeError
from urllib.parse import urlencode, urlsplit

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from accounts.email_backend import BrevoEmailDeliveryError

logger = logging.getLogger(__name__)


class AccountEmailDeliveryError(Exception):
    pass


def _frontend_link(path, query):
    base_url = settings.PUBLIC_FRONTEND_URL
    parsed = urlsplit(base_url)
    if (
        parsed.scheme not in ({'http', 'https'} if settings.DEBUG else {'https'})
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.path not in {'', '/'}
        or parsed.query
        or parsed.fragment
    ):
        raise AccountEmailDeliveryError('Public frontend URL is not configured safely.')
    return f'{base_url.rstrip("/")}{path}?{urlencode(query)}'


def _deliver(subject, body, recipient):
    try:
        sent_count = send_mail(
            subject=subject,
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
    except (OSError, smtplib.SMTPException) as exc:
        if isinstance(exc, BrevoEmailDeliveryError):
            logger.warning('Account email delivery failed: %s', exc)
        else:
            logger.warning('Account email delivery failed (%s).', type(exc).__name__)
        raise AccountEmailDeliveryError('Account email delivery failed.') from exc
    if sent_count != 1:
        logger.warning('Account email delivery did not accept a message.')
        raise AccountEmailDeliveryError('Account email delivery failed.')


def send_verification_email(user, token, next_path='/'):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    link = _frontend_link('/verify-email', {'uid': uid, 'token': token, 'next': next_path})
    _deliver(
        'Verify your Habesha Home Center account',
        (
            'Hello,\n\n'
            'Verify your email address to activate your Habesha Home Center account:\n'
            f'{link}\n\n'
            'This link expires after '
            f'{settings.EMAIL_VERIFICATION_TIMEOUT.total_seconds() / 3600:g} hour(s). '
            'If you did not create this account, you can ignore this message.'
        ),
        user.email,
    )


def send_password_reset_email(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    link = _frontend_link('/reset-password', {'uid': uid, 'token': token})
    _deliver(
        'Reset your Habesha Home Center password',
        (
            'A password reset was requested for your Habesha Home Center account.\n\n'
            f'Choose a new password using this link:\n{link}\n\n'
            'If you did not request this change, you can ignore this message.'
        ),
        user.email,
    )


def get_user_from_uid(uid):
    try:
        user_id = urlsafe_base64_decode_uid(uid)
        return get_user_model().objects.get(pk=user_id)
    except (
        Base64DecodeError,
        TypeError,
        UnicodeDecodeError,
        ValueError,
        OverflowError,
        get_user_model().DoesNotExist,
    ):
        return None


def urlsafe_base64_decode_uid(uid):
    from django.utils.http import urlsafe_base64_decode

    return urlsafe_base64_decode(uid).decode('utf-8')
