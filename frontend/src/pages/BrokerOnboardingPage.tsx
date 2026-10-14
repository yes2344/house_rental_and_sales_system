import { useState, type FormEvent } from 'react';
import { ArrowRight, KeyRound } from 'lucide-react';
import { Navigate } from 'react-router-dom';

import { getApiFieldErrors, getErrorMessage } from '../api/client';
import { useAuth } from '../AuthContext';
import type { MessageKey } from '../i18n';

interface BrokerOnboardingPageProps {
  text: (key: MessageKey) => string;
}

export function BrokerOnboardingPage({ text }: BrokerOnboardingPageProps) {
  const { account, changeBrokerInitialPassword, completeBrokerInitialProfile } = useAuth();
  const [step, setStep] = useState<'password' | 'profile'>(
    account?.broker_password_changed ? 'profile' : 'password',
  );
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [firstName, setFirstName] = useState(account?.first_name ?? '');
  const [lastName, setLastName] = useState(account?.last_name ?? '');
  const [email, setEmail] = useState(account?.email ?? '');
  const [phone, setPhone] = useState(account?.phone ?? '');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (!account) return <Navigate to="/login" replace />;
  if (account.role !== 'broker' || !account.broker_onboarding_required) {
    return <Navigate to={account.role === 'broker' || account.role === 'administrator' ? '/dashboard' : '/'} replace />;
  }

  const changePassword = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    setFieldErrors({});
    if (password !== confirmation) {
      setError(text('passwordMismatch'));
      return;
    }
    setSubmitting(true);
    try {
      await changeBrokerInitialPassword({
        ...(username.trim() ? { username: username.trim() } : {}),
        new_password: password,
      });
      setPassword('');
      setConfirmation('');
      setStep('profile');
    } catch (requestError: unknown) {
      setError(getErrorMessage(requestError));
      setFieldErrors(getApiFieldErrors(requestError));
    } finally {
      setSubmitting(false);
    }
  };

  const completeProfile = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    setFieldErrors({});
    setSubmitting(true);
    try {
      await completeBrokerInitialProfile({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        email: email.trim(),
        phone: phone.trim(),
      });
    } catch (requestError: unknown) {
      setError(getErrorMessage(requestError));
      setFieldErrors(getApiFieldErrors(requestError));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main id="main-content" className="auth-page">
      <section className="auth-card">
        <span className="auth-icon"><KeyRound size={22} aria-hidden="true" /></span>
        <p className="eyebrow eyebrow-muted">{text('accountEyebrow')}</p>
        <h1>{text('brokerFirstLoginTitle')}</h1>
        {step === 'password' ? (
          <>
            <h2>{text('brokerPasswordStepTitle')}</h2>
            <p className="auth-intro">{text('brokerPasswordStepIntro')}</p>
            {error && <p className="auth-form-error" role="alert">{error}</p>}
            <form className="auth-form" onSubmit={(event) => void changePassword(event)}>
              <label htmlFor="broker-new-username">{text('optionalBrokerUsername')}
                <input
                  id="broker-new-username"
                  autoComplete="username"
                  maxLength={150}
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                />
                {fieldErrors.username && <small role="alert">{fieldErrors.username}</small>}
              </label>
              <label htmlFor="broker-new-password">{text('newPassword')}
                <input
                  id="broker-new-password"
                  type="password"
                  autoComplete="new-password"
                  minLength={8}
                  required
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
                {fieldErrors.new_password && <small role="alert">{fieldErrors.new_password}</small>}
              </label>
              <label htmlFor="broker-password-confirmation">{text('confirmPassword')}
                <input
                  id="broker-password-confirmation"
                  type="password"
                  autoComplete="new-password"
                  minLength={8}
                  required
                  value={confirmation}
                  onChange={(event) => setConfirmation(event.target.value)}
                />
              </label>
              <p className="auth-helper">{text('passwordHint')}</p>
              <button className="button button-primary" type="submit" disabled={submitting}>
                {submitting ? text('brokerSetupSaving') : text('continueToBrokerProfile')}
                <ArrowRight size={16} aria-hidden="true" />
              </button>
            </form>
          </>
        ) : (
          <>
            <h2>{text('brokerProfileStepTitle')}</h2>
            <p className="auth-intro">{text('brokerProfileStepIntro')}</p>
            {error && <p className="auth-form-error" role="alert">{error}</p>}
            <form className="auth-form" onSubmit={(event) => void completeProfile(event)}>
              <label htmlFor="broker-first-name">{text('brokerFirstName')}
                <input
                  id="broker-first-name"
                  autoComplete="given-name"
                  maxLength={150}
                  required
                  value={firstName}
                  onChange={(event) => setFirstName(event.target.value)}
                />
                {fieldErrors.first_name && <small role="alert">{fieldErrors.first_name}</small>}
              </label>
              <label htmlFor="broker-last-name">{text('brokerLastName')}
                <input
                  id="broker-last-name"
                  autoComplete="family-name"
                  maxLength={150}
                  required
                  value={lastName}
                  onChange={(event) => setLastName(event.target.value)}
                />
                {fieldErrors.last_name && <small role="alert">{fieldErrors.last_name}</small>}
              </label>
              <label htmlFor="broker-email">{text('brokerEmail')}
                <input
                  id="broker-email"
                  type="email"
                  autoComplete="email"
                  maxLength={254}
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
                {fieldErrors.email && <small role="alert">{fieldErrors.email}</small>}
              </label>
              <label htmlFor="broker-phone">{text('brokerPhone')}
                <input
                  id="broker-phone"
                  type="tel"
                  autoComplete="tel"
                  maxLength={50}
                  required
                  value={phone}
                  onChange={(event) => setPhone(event.target.value)}
                />
                {fieldErrors.phone && <small role="alert">{fieldErrors.phone}</small>}
              </label>
              <button className="button button-primary" type="submit" disabled={submitting}>
                {submitting ? text('brokerSetupSaving') : text('completeBrokerSetup')}
                <ArrowRight size={16} aria-hidden="true" />
              </button>
            </form>
          </>
        )}
      </section>
    </main>
  );
}
