import { useState, type FormEvent } from 'react';
import { ArrowRight, KeyRound } from 'lucide-react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';

import { getErrorMessage } from '../api/client';
import { useAuth } from '../AuthContext';
import type { MessageKey } from '../i18n';

interface LoginPageProps {
  text: (key: MessageKey) => string;
}

interface LoginLocationState {
  registered?: boolean;
  invitationAccepted?: boolean;
  username?: string;
}

export function LoginPage({ text }: LoginPageProps) {
  const { account, authError, authLoading, signIn } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const state = location.state as LoginLocationState | null;
  const [username, setUsername] = useState(state?.username ?? '');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      const signedInAccount = await signIn(username.trim(), password);
      navigate(
        signedInAccount.broker_onboarding_required ? '/broker-onboarding' : '/',
        { replace: true },
      );
    } catch (requestError: unknown) {
      setError(getErrorMessage(requestError));
    } finally {
      setSubmitting(false);
    }
  };

  if (!authLoading && account) return <Navigate to="/" replace />;

  return (
    <main id="main-content" className="auth-page">
      <section className="auth-card">
        <span className="auth-icon"><KeyRound size={22} aria-hidden="true" /></span>
        <p className="eyebrow eyebrow-muted">{text('accountEyebrow')}</p>
        <h1>{text('signIn')}</h1>
        <p className="auth-intro">{text('loginIntro')}</p>
        {state?.registered && <p className="auth-success" role="status">{text('registrationSuccess')}</p>}
        {state?.invitationAccepted && <p className="auth-success" role="status">{text('invitationAccepted')}</p>}
        {authError && <p className="auth-form-error" role="alert">{text('accountStatusError')} {authError}</p>}
        {error && <p className="auth-form-error" role="alert">{error}</p>}
        <form className="auth-form" onSubmit={submit}>
          <label htmlFor="login-username">{text('username')}
            <input
              id="login-username"
              name="username"
              autoComplete="username"
              required
              value={username}
              onChange={(event) => setUsername(event.target.value)}
            />
          </label>
          <label htmlFor="login-password">{text('password')}
            <input
              id="login-password"
              name="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          <p className="auth-helper">{text('usernameLoginHint')}</p>
          <button className="button button-primary" type="submit" disabled={submitting || authLoading}>
            {submitting ? text('signingIn') : text('signIn')}<ArrowRight size={16} aria-hidden="true" />
          </button>
        </form>
        <p className="auth-switch">
          {text('noAccount')} <Link to="/register">{text('createAccount')}</Link>
        </p>
      </section>
    </main>
  );
}
