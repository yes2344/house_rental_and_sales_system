import { useEffect, useState, type FormEvent } from 'react';

import { useAuth } from '../AuthContext';
import { getErrorMessage } from '../api/client';
import type { BrokerageContact } from '../api/brokerage';
import { useBrokerageContact } from '../BrokerageContactContext';
import type { MessageKey } from '../i18n';

interface BrokerageSettingsPageProps {
  text: (key: MessageKey) => string;
}

const fields: { name: keyof BrokerageContact; label: MessageKey; type: string }[] = [
  { name: 'business_name', label: 'brokerageBusinessName', type: 'text' },
  { name: 'phone', label: 'brokeragePhone', type: 'tel' },
  { name: 'whatsapp_url', label: 'brokerageWhatsApp', type: 'url' },
  { name: 'telegram_url', label: 'brokerageTelegram', type: 'url' },
  { name: 'email', label: 'brokerageEmail', type: 'email' },
  { name: 'facebook_url', label: 'brokerageFacebook', type: 'url' },
  { name: 'instagram_url', label: 'brokerageInstagram', type: 'url' },
  { name: 'tiktok_url', label: 'brokerageTikTok', type: 'url' },
  { name: 'youtube_url', label: 'brokerageYouTube', type: 'url' },
  { name: 'linkedin_url', label: 'brokerageLinkedIn', type: 'url' },
];

export function BrokerageSettingsPage({ text }: BrokerageSettingsPageProps) {
  const { account } = useAuth();
  const { contact, loading, error, save } = useBrokerageContact();
  const [values, setValues] = useState<BrokerageContact>(contact);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');
  const [saved, setSaved] = useState(false);
  const canEdit = Boolean(
    account?.is_platform_owner || account?.management_permissions.includes('settings.manage'),
  );

  useEffect(() => setValues(contact), [contact]);

  const update = (name: keyof BrokerageContact, value: string) => {
    setValues((current) => ({ ...current, [name]: value }));
    setSaveError('');
    setSaved(false);
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setSaveError('');
    setSaved(false);
    try {
      await save(values);
      setSaved(true);
    } catch (requestError: unknown) {
      setSaveError(getErrorMessage(requestError));
    } finally {
      setSaving(false);
    }
  };

  if (!canEdit) {
    return (
      <main className="manager-page" id="main-content">
        <div className="manager-state manager-error" role="alert">
          <h1>{text('brokerageSettingsTitle')}</h1>
          <p>{text('brokerageSettingsPermission')}</p>
        </div>
      </main>
    );
  }

  return (
    <main className="manager-page" id="main-content">
      <section className="manager-heading">
        <div>
          <p className="eyebrow eyebrow-muted"><span className="eyebrow-dot" />{text('managerEyebrow')}</p>
          <h1>{text('brokerageSettingsTitle')}</h1>
          <p>{text('brokerageSettingsIntro')}</p>
        </div>
      </section>
      {loading ? (
        <div className="listing-state" role="status">{text('settingsLoading')}</div>
      ) : (
        <form className="manager-form" onSubmit={submit}>
          <section className="manager-form-section">
            <div className="brokerage-contact-fields">
              {fields.map(({ name, label, type }) => (
                <label className="manager-field" key={name}>
                  <span>{text(label)}</span>
                  <input
                    type={type}
                    maxLength={name === 'business_name' ? 160 : 300}
                    value={values[name]}
                    onChange={(event) => update(name, event.target.value)}
                  />
                </label>
              ))}
            </div>
            {error && <p className="manager-inline-error" role="status">{error}</p>}
            {saveError && <p className="manager-inline-error" role="alert">{text('brokerageSettingsError')} {saveError}</p>}
            {saved && <p className="manager-inline-success" role="status">{text('brokerageSettingsSaved')}</p>}
            <div className="manager-form-actions">
              <button className="button button-primary" type="submit" disabled={saving}>
                {saving ? text('savingBrokerageSettings') : text('saveBrokerageSettings')}
              </button>
            </div>
          </section>
        </form>
      )}
    </main>
  );
}
