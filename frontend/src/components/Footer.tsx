import { ArrowUpRight, Mail, Phone } from 'lucide-react';
import { Link } from 'react-router-dom';

import { useAuth } from '../AuthContext';
import type { BrokerageContact } from '../api/brokerage';
import type { MessageKey } from '../i18n';
import { SocialMark, socialPlatformNames } from './SocialMark';

interface FooterProps {
  contact: BrokerageContact;
  contactError: string;
  text: (key: MessageKey) => string;
}

export function Footer({ contact, contactError, text }: FooterProps) {
  const { account } = useAuth();
  const isAdministrator = account?.role === 'administrator';
  const configuredSocial = contact.social_links.filter((link) => link.is_enabled && link.url);
  const hasBrokerageContact = Boolean(contact.phone || contact.email || configuredSocial.length);

  return (
    <footer className="site-footer">
      <div className="container footer-main">
        <div className="footer-brand">
          <Link className="brand brand-footer" to={isAdministrator ? '/dashboard' : '/'}>
            {contact.site_logo ? (
              <img className="brand-logo" src={contact.site_logo} alt="" />
            ) : (
              <span className="brand-mark" aria-hidden="true">
                <svg viewBox="0 0 36 36" fill="none">
                  <path d="M5 17.1 18 6l13 11.1v12.1H5V17.1Z" fill="currentColor" />
                  <path d="m3 17.4 15-13 15 13" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M15 20h6v9h-6z" fill="#153F35" />
                </svg>
              </span>
            )}
            <span className="brand-copy"><strong>{contact.site_name || 'habeshahome'}</strong></span>
          </Link>
          <p>{text('footerNote')}</p>
        </div>
        {!isAdministrator && (
          <div className="footer-links">
            <Link to="/">{text('footerBrowse')} <ArrowUpRight size={14} aria-hidden="true" /></Link>
            <Link to={account ? '/account' : '/login'}>
              {text(account ? 'myAccount' : 'footerAccount')} <ArrowUpRight size={14} aria-hidden="true" />
            </Link>
          </div>
        )}
        {hasBrokerageContact && (
          <section className="footer-contact" aria-label={text('brokerContactTitle')}>
            <h2>{text('brokerContactTitle')}</h2>
            {contact.phone && (
              <a href={`tel:${contact.phone}`}><Phone size={15} aria-hidden="true" />{contact.phone}</a>
            )}
            {contact.email && (
              <a href={`mailto:${contact.email}`}><Mail size={15} aria-hidden="true" />{contact.email}</a>
            )}
            {configuredSocial.length > 0 && (
              <div className="footer-socials" aria-label={text('brokerSocialLinks')}>
                {configuredSocial.map((link) => (
                  <a
                    key={link.platform}
                    href={link.url}
                    target="_blank"
                    rel="noreferrer"
                    aria-label={socialPlatformNames[link.platform]}
                    title={socialPlatformNames[link.platform]}
                  >
                    <SocialMark platform={link.platform} />
                  </a>
                ))}
              </div>
            )}
            {contactError && <p className="footer-contact-error" role="status">{text('brokerContactUnavailable')}</p>}
          </section>
        )}
      </div>
      <div className="container footer-bottom">
        <span>© {new Date().getFullYear()} {contact.site_name || 'habeshahome'}</span>
      </div>
    </footer>
  );
}
