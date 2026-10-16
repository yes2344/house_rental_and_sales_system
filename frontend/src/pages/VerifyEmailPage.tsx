import { useEffect, useRef, useState, type FormEvent } from 'react';
import { ArrowRight, MailCheck } from 'lucide-react';
import { Link, useLocation, useSearchParams } from 'react-router-dom';

import { getErrorMessage } from '../api/client';
import { resendVerificationEmail, verifyEmail } from '../api/accounts';
import type { MessageKey } from '../i18n';

interface VerifyEmailPageProps {
  text: (key: MessageKey) => string;
}

interface VerificationLocationState {
  email?: string;
  next?: string;
}

function getSafeNextPath(candidate: string | null | undefined): string {
  return candidate?.startsWith('/') && !candidate.startsWith('//') && !candidate.includes('\\')
    ? candidate
    : '/';
}

export function VerifyEmailPage({ text }: VerifyEmailPageProps) {
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const state = location.state as VerificationLocationState | null;
  const uid = searchParams.get('uid');
  const token = searchParams.get('token');
  const next = getSafeNextPath(searchParams.get('next') ?? state?.next);
  const [email, setEmail] = useState(state?.email ?? '');
  const [status, setStatus] = useState(uid && token ? 'verifying' : 'ready');
  const [message, setMessage] = useState('');
  const verificationStarted = useRef(false);

  useEffect(() => {
    if (!uid || !token || verificationStarted.current) return;
    verificationStarted.current = true;
    void verifyEmail({ uid, token })
      .then(() => {
        setStatus('verified');
        setMessage(text('emailVerificationSuccess'));
      })
      .catch((error: unknown) => {
        setStatus('invalid');
        setMessage(getErrorMessage(error));
      });
  }, [uid, token, text]);

  const resend = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setStatus('sending');
    setMessage('');
    try {
      await resendVerificationEmail({ email: email.trim() });
      setStatus('sent');
      setMessage(text('verificationResendGeneric'));
    } catch (error: unknown) {
      setStatus('ready');
      setMessage(getErrorMessage(error));
    }
  };

  return (
    <main id="main-content" className="auth-page">
      <section className="auth-card">
        <span className="auth-icon"><MailCheck size={22} aria-hidden="true" /></span>
        <p className="eyebrow eyebrow-muted">{text('accountEyebrow')}</p>
        <h1>{text(status === 'verified' ? 'emailVerifiedTitle' : 'verifyEmailTitle')}</h1>
        <p className="auth-intro">
          {text(status === 'verified'
            ? 'emailVerifiedIntro'
            : uid && token
              ? status === 'verifying' ? 'emailVerifying' : 'emailVerificationFailed'
              : 'verificationEmailSentIntro')}
        </p>
        {message && (
          <p className={status === 'verified' || status === 'sent' ? 'auth-success' : 'auth-form-error'} role={status === 'verifying' ? 'status' : 'alert'}>
            {message}
          </p>
        )}
        {status === 'verified' ? (
          <Link className="button button-primary" to="/login" state={{ from: next }}>
            {text('continueToSignIn')}<ArrowRight size={16} aria-hidden="true" />
          </Link>
        ) : (
          <form className="auth-form" onSubmit={resend}>
            <label htmlFor="verification-email">{text('emailAddress')}
              <input
                id="verification-email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </label>
            <button className="button button-primary" type="submit" disabled={status === 'sending'}>
              {text(status === 'sending' ? 'sendingVerification' : 'resendVerification')}<ArrowRight size={16} aria-hidden="true" />
            </button>
          </form>
        )}
        <p className="auth-switch">
          <Link to="/login" state={{ from: next }}>{text('backToSignIn')}</Link>
        </p>
      </section>
    </main>
  );
}
