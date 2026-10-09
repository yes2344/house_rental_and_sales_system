import { ArrowUpRight, Mail, Phone, Send } from 'lucide-react';
import { Link } from 'react-router-dom';

import type { BrokerageContact } from '../api/brokerage';
import type { MessageKey } from '../i18n';

interface FooterProps {
  contact: BrokerageContact;
  contactError: string;
  text: (key: MessageKey) => string;
}

const socialLinks = [
  ['facebook_url', 'Facebook'],
  ['instagram_url', 'Instagram'],
  ['tiktok_url', 'TikTok'],
  ['youtube_url', 'YouTube'],
  ['linkedin_url', 'LinkedIn'],
] as const;

function SocialMark({ name }: {
  name: (typeof socialLinks)[number][1] | 'WhatsApp' | 'Telegram';
}) {
  if (name === 'Facebook') {
    return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M13.4 21v-8h2.7l.4-3.1h-3.1v-2c0-.9.3-1.5 1.6-1.5h1.7V3.6c-.3 0-1.3-.1-2.4-.1-2.4 0-4.1 1.5-4.1 4.2v2.2H7.5V13h2.7v8h3.2Z" fill="currentColor" /></svg>;
  }
  if (name === 'Instagram') {
    return <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3.5" y="3.5" width="17" height="17" rx="5" fill="none" stroke="currentColor" strokeWidth="2" /><circle cx="12" cy="12" r="4" fill="none" stroke="currentColor" strokeWidth="2" /><circle cx="17.7" cy="6.6" r="1.2" fill="currentColor" /></svg>;
  }
  if (name === 'WhatsApp') {
    return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 11.7a8 8 0 0 1-11.8 7L4 20l1.3-4A8 8 0 1 1 20 11.7Z" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" /><path d="M9 8.2c.2-.5.5-.5.8-.5h.4c.2 0 .3.1.4.4l.7 1.7c.1.2 0 .4-.1.6l-.5.6c-.2.2-.2.4 0 .6.5.8 1.2 1.4 2 1.8.2.1.4.1.6-.1l.7-.8c.2-.2.4-.2.6-.1l1.6.8c.2.1.3.2.3.4 0 .4-.2 1-.6 1.3-.4.4-1 .6-1.6.5-1-.1-2.2-.7-3.4-1.7-1.4-1.2-2.3-2.6-2.5-3.6-.2-.8.1-1.5.6-1.9Z" fill="currentColor" /></svg>;
  }
  if (name === 'Telegram') {
    return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m21 4-3.2 16c-.2 1.1-.9 1.3-1.8.8l-5-3.7-2.4 2.3c-.3.3-.5.5-1 .5l.4-5.1L17.3 7c.4-.4-.1-.6-.6-.3L5.3 13.8.4 12.3c-1.1-.3-1.1-1 .2-1.5L19.8 3.4c.9-.3 1.6.2 1.2.6Z" fill="currentColor" transform="translate(1 1) scale(.92)" /></svg>;
  }
  if (name === 'YouTube') {
    return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M22 8.1a2.8 2.8 0 0 0-2-2C18.2 5.6 12 5.6 12 5.6s-6.2 0-8 .5a2.8 2.8 0 0 0-2 2A29 29 0 0 0 1.5 12a29 29 0 0 0 .5 3.9 2.8 2.8 0 0 0 2 2c1.8.5 8 .5 8 .5s6.2 0 8-.5a2.8 2.8 0 0 0 2-2 29 29 0 0 0 .5-3.9 29 29 0 0 0-.5-3.9ZM10 15.2V8.8l5.5 3.2-5.5 3.2Z" fill="currentColor" /></svg>;
  }
  if (name === 'LinkedIn') {
    return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5.2 8.6a1.8 1.8 0 1 0 0-3.6 1.8 1.8 0 0 0 0 3.6ZM3.7 10h3v9h-3v-9Zm4.9 0h2.9v1.2h.1a3.2 3.2 0 0 1 2.9-1.5c3.1 0 3.7 2 3.7 4.6V19h-3v-4.2c0-1 0-2.4-1.5-2.4s-1.8 1.1-1.8 2.3V19h-3v-9Z" fill="currentColor" /></svg>;
  }
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M13.3 3v11.1a3.5 3.5 0 1 1-2.8-3.4V7.8a6.3 6.3 0 1 0 5.7 6.3V8.6a8.4 8.4 0 0 0 4.1 1.1V6.8A5.5 5.5 0 0 1 16 5.4 5.5 5.5 0 0 1 14.4 3h-1.1Z" fill="currentColor" /></svg>;
}

export function Footer({ contact, contactError, text }: FooterProps) {
  const configuredSocial = socialLinks.filter(([field]) => contact[field]);

  return (
    <footer className="site-footer">
      <div className="container footer-main">
        <div className="footer-brand">
          <Link className="brand brand-footer" to="/">
            <span className="brand-mark" aria-hidden="true">
              <svg viewBox="0 0 36 36" fill="none">
                <path d="M5 17.1 18 6l13 11.1v12.1H5V17.1Z" fill="currentColor" />
                <path d="m3 17.4 15-13 15 13" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M15 20h6v9h-6z" fill="#153F35" />
              </svg>
            </span>
            <span className="brand-copy"><strong>{contact.business_name || 'Habesha Homes'}</strong><small>DEBRE MARKOS</small></span>
          </Link>
          <p>{text('footerNote')}</p>
        </div>
        <div className="footer-links">
          <Link to="/properties">{text('footerBrowse')} <ArrowUpRight size={14} aria-hidden="true" /></Link>
          <Link to="/login">{text('footerAccount')} <ArrowUpRight size={14} aria-hidden="true" /></Link>
        </div>
        <section className="footer-contact" aria-label={text('brokerContactTitle')}>
          <h2>{text('brokerContactTitle')}</h2>
          {contact.phone && (
            <a href={`tel:${contact.phone}`}><Phone size={15} aria-hidden="true" />{contact.phone}</a>
          )}
          {contact.whatsapp_url && (
            <a href={contact.whatsapp_url} target="_blank" rel="noreferrer"><SocialMark name="WhatsApp" />WhatsApp</a>
          )}
          {contact.telegram_url && (
            <a href={contact.telegram_url} target="_blank" rel="noreferrer"><Send size={15} aria-hidden="true" />Telegram</a>
          )}
          {contact.email && (
            <a href={`mailto:${contact.email}`}><Mail size={15} aria-hidden="true" />{contact.email}</a>
          )}
          {configuredSocial.length > 0 && (
            <div className="footer-socials" aria-label={text('brokerSocialLinks')}>
              {configuredSocial.map(([field, name]) => (
                <a
                  key={field}
                  href={contact[field]}
                  target="_blank"
                  rel="noreferrer"
                  aria-label={name}
                  title={name}
                >
                  <SocialMark name={name} />
                </a>
              ))}
            </div>
          )}
          {contactError && <p className="footer-contact-error" role="status">{text('brokerContactUnavailable')}</p>}
        </section>
      </div>
      <div className="container footer-bottom">
        <span>© {new Date().getFullYear()} {contact.business_name || 'Habesha Homes'}</span>
        <span>Debre Markos, Ethiopia</span>
      </div>
    </footer>
  );
}
