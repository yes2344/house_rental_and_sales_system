import json
import logging
from email.utils import parseaddr
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


logger = logging.getLogger(__name__)


class BrevoEmailDeliveryError(OSError):
    pass


class BrevoEmailBackend(BaseEmailBackend):
    api_url = 'https://api.brevo.com/v3/smtp/email'

    def send_messages(self, email_messages):
        sent_count = 0
        for message in email_messages:
            try:
                self._send_message(message)
            except BrevoEmailDeliveryError:
                if self.fail_silently:
                    continue
                raise
            sent_count += 1
        return sent_count

    def _send_message(self, message):
        api_key = getattr(settings, 'BREVO_API_KEY', '').strip()
        if not api_key:
            raise BrevoEmailDeliveryError('BREVO_API_KEY is not configured.')

        sender_name, sender_email = parseaddr(message.from_email or settings.DEFAULT_FROM_EMAIL)
        if not sender_email:
            raise BrevoEmailDeliveryError('DEFAULT_FROM_EMAIL is not a valid sender address.')

        recipients = [
            {'email': recipient}
            for recipient in message.to
        ]
        if not message.recipients():
            return
        if not recipients:
            raise BrevoEmailDeliveryError('Brevo email requires at least one primary recipient.')

        payload = {
            'sender': {'email': sender_email},
            'to': recipients,
            'subject': message.subject,
            'textContent': message.body,
        }
        if sender_name:
            payload['sender']['name'] = sender_name

        html_content = next(
            (
                content
                for content, mimetype in getattr(message, 'alternatives', ())
                if mimetype == 'text/html'
            ),
            None,
        )
        if html_content is not None:
            payload['htmlContent'] = html_content

        if message.cc:
            payload['cc'] = [{'email': address} for address in message.cc]
        if message.bcc:
            payload['bcc'] = [{'email': address} for address in message.bcc]
        if message.reply_to:
            reply_to_name, reply_to_email = parseaddr(message.reply_to[0])
            if reply_to_email:
                payload['replyTo'] = {'email': reply_to_email}
                if reply_to_name:
                    payload['replyTo']['name'] = reply_to_name

        request = Request(
            self.api_url,
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'api-key': api_key,
            },
            method='POST',
        )
        try:
            with urlopen(request, timeout=settings.EMAIL_TIMEOUT) as response:
                status_code = response.status
        except HTTPError as exc:
            logger.warning('Brevo email API returned HTTP %s.', exc.code)
            raise BrevoEmailDeliveryError(
                f'Brevo email API returned HTTP {exc.code}.'
            ) from exc
        except URLError as exc:
            logger.warning(
                'Brevo email API request failed (%s).',
                type(exc.reason).__name__,
            )
            raise BrevoEmailDeliveryError(
                f'Brevo email API request failed ({type(exc.reason).__name__}).'
            ) from exc
        except OSError as exc:
            logger.warning('Brevo email API request failed (%s).', type(exc).__name__)
            raise BrevoEmailDeliveryError(
                f'Brevo email API request failed ({type(exc).__name__}).'
            ) from exc
        if not 200 <= status_code < 300:
            logger.warning('Brevo email API returned HTTP %s.', status_code)
            raise BrevoEmailDeliveryError(
                f'Brevo email API returned HTTP {status_code}.'
            )
