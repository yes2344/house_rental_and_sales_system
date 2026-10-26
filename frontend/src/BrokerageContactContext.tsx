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
  updateSiteBranding,
  updateBrokerageContact,
  type BrokerageContact,
} from './api/brokerage';
import { getErrorMessage } from './api/client';

interface BrokerageContactContextValue {
  contact: BrokerageContact;
  loading: boolean;
  error: string;
  save: (updates: Partial<BrokerageContact>) => Promise<void>;
  saveBranding: (updates: {
    site_name: string;
    site_logo?: File;
    clear_site_logo?: boolean;
    homepage_hero_image?: File;
    clear_homepage_hero_image?: boolean;
  }) => Promise<void>;
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

  useEffect(() => {
    let active = true;
    let favicon = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
    if (!favicon) {
      favicon = document.createElement('link');
      favicon.rel = 'icon';
      document.head.append(favicon);
    }

    const useDefaultFavicon = () => {
      if (!favicon) return;
      favicon.href = '/favicon.svg';
      favicon.type = 'image/svg+xml';
      favicon.sizes = 'any';
    };

    if (!contact.site_logo) {
      useDefaultFavicon();
      return () => {
        active = false;
      };
    }

    const logoUrl = new URL(contact.site_logo, document.baseURI);
    useDefaultFavicon();

    const image = new Image();
    image.crossOrigin = 'anonymous';
    image.src = logoUrl.href;
    image.decode().then(() => {
      if (!active || !favicon) return;
      const size = 64;
      const imageSize = 54;
      const imageOffset = (size - imageSize) / 2;
      const cropSize = Math.min(image.naturalWidth, image.naturalHeight);
      const sourceX = (image.naturalWidth - cropSize) / 2;
      const sourceY = (image.naturalHeight - cropSize) / 2;
      const canvas = document.createElement('canvas');
      canvas.width = size;
      canvas.height = size;
      const context = canvas.getContext('2d');
      if (!context) throw new Error('A 2D canvas context is not available.');

      context.beginPath();
      context.arc(size / 2, size / 2, size / 2 - 1, 0, Math.PI * 2);
      context.fillStyle = '#f2c46d';
      context.fill();
      context.save();
      context.beginPath();
      context.arc(size / 2, size / 2, imageSize / 2, 0, Math.PI * 2);
      context.clip();
      context.drawImage(
        image,
        sourceX,
        sourceY,
        cropSize,
        cropSize,
        imageOffset,
        imageOffset,
        imageSize,
        imageSize,
      );
      context.restore();

      favicon.href = canvas.toDataURL('image/png');
      favicon.type = 'image/png';
      favicon.sizes = `${size}x${size}`;
    }).catch((renderError: unknown) => {
      if (active) {
        console.error('Could not render the site logo as a circular favicon.', renderError);
        useDefaultFavicon();
      }
    });

    return () => {
      active = false;
    };
  }, [contact.site_logo]);

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

  const saveBranding = useCallback(async (updates: {
    site_name: string;
    site_logo?: File;
    clear_site_logo?: boolean;
    homepage_hero_image?: File;
    clear_homepage_hero_image?: boolean;
  }) => {
    setError('');
    try {
      setContact(await updateSiteBranding(updates));
    } catch (requestError: unknown) {
      const message = getErrorMessage(requestError);
      setError(message);
      throw requestError;
    }
  }, []);

  const value = useMemo(
    () => ({ contact, loading, error, save, saveBranding, refresh }),
    [contact, loading, error, save, saveBranding, refresh],
  );
  return <BrokerageContactContext.Provider value={value}>{children}</BrokerageContactContext.Provider>;
}

export function useBrokerageContact() {
  const context = useContext(BrokerageContactContext);
  if (!context) throw new Error('useBrokerageContact must be used inside BrokerageContactProvider.');
  return context;
}
