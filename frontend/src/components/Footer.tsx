import { ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';

import type { MessageKey } from '../i18n';

interface FooterProps {
  text: (key: MessageKey) => string;
}

export function Footer({ text }: FooterProps) {
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
            <span className="brand-copy"><strong>habesha<span>homes</span></strong><small>DEBRE MARKOS</small></span>
          </Link>
          <p>{text('footerNote')}</p>
        </div>
        <div className="footer-links">
          <Link to="/properties">{text('footerBrowse')} <ArrowUpRight size={14} aria-hidden="true" /></Link>
          <Link to="/login">{text('footerAccount')} <ArrowUpRight size={14} aria-hidden="true" /></Link>
        </div>
      </div>
      <div className="container footer-bottom">
        <span>© {new Date().getFullYear()} Habesha Homes</span>
        <span>Debre Markos, Ethiopia</span>
      </div>
    </footer>
  );
}
