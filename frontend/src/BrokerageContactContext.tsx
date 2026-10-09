import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import {
  emptyBrokerageContact,
  getBrokerageContact,
  updateBrokerageContact,
  type BrokerageContact,
} from './api/brokerage';
import { getErrorMessage } from './api/client';

interface BrokerageContactContextValue {
  contact: BrokerageContact;
  loading: boolean;
  error: string;
  save: (updates: Partial<BrokerageContact>) => Promise<void>;
  refresh: () => Promise<void>;
}

const BrokerageContactContext = createContext<BrokerageContactContextValue | null>(null);

export function BrokerageContactProvider({ children }: { children: ReactNode }) {
  const [contact, setContact] = useState(emptyBrokerageContact);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      setContact(await getBrokerageContact());
    } catch (requestError: unknown) {
      setError(getErrorMessage(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    getBrokerageContact(controller.signal)
      .then((value) => {
        if (!controller.signal.aborted) {
          setContact(value);
          setError('');
        }
      })
      .catch((requestError: unknown) => {
        if (!controller.signal.aborted) setError(getErrorMessage(requestError));
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  const save = useCallback(async (updates: Partial<BrokerageContact>) => {
    setError('');
    try {
      const updated = await updateBrokerageContact(updates);
      setContact(updated);
    } catch (requestError: unknown) {
      const message = getErrorMessage(requestError);
      setError(message);
      throw requestError;
    }
  }, []);

  const value = useMemo(
    () => ({ contact, loading, error, save, refresh }),
    [contact, loading, error, save, refresh],
  );
  return <BrokerageContactContext.Provider value={value}>{children}</BrokerageContactContext.Provider>;
}

export function useBrokerageContact() {
  const context = useContext(BrokerageContactContext);
  if (!context) throw new Error('useBrokerageContact must be used inside BrokerageContactProvider.');
  return context;
}
