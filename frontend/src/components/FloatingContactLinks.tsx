import { Mail, Phone } from 'lucide-react';

import { useBrokerageContact } from '../BrokerageContactContext';
import type { MessageKey } from '../i18n';
import { SocialMark, socialPlatformNames } from './SocialMark';

interface FloatingContactLinksProps {
  text: (key: MessageKey) => string;
}

export function FloatingContactLinks({ text }: FloatingContactLinksProps) {
  const { contact } = useBrokerageContact();
  const socialLinks = contact.social_links.filter((link) => (
    link.is_enabled
    && link.url
    && (link.platform === 'whatsapp' || link.platform === 'telegram')
  ));
  if (!contact.phone && !contact.email && socialLinks.length === 0) return null;

  return (
    <nav className="floating-contact-links" aria-label={text('floatingContactLinks')}>
      {contact.phone && (
        <a className="floating-contact-link floating-contact-phone" href={`tel:${contact.phone}`} aria-label={text('contactByPhone')}>
          <Phone aria-hidden="true" />
        </a>
      )}
      {contact.email && (
        <a className="floating-contact-link floating-contact-email" href={`mailto:${contact.email}`} aria-label={text('contactByEmail')}>
          <Mail aria-hidden="true" />
        </a>
      )}
      {socialLinks.map((link) => (
        <a
          className={`floating-contact-link floating-contact-social floating-contact-${link.platform}`}
          key={link.platform}
          href={link.url}
          target="_blank"
          rel="noopener noreferrer"
          aria-label={
            link.platform === 'whatsapp'
              ? text('contactByWhatsApp')
              : link.platform === 'telegram'
                ? text('contactByTelegram')
                : socialPlatformNames[link.platform]
          }
        >
          <SocialMark platform={link.platform} />
        </a>
      ))}
    </nav>
  );
}
