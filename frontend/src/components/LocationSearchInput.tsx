import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { MapPin } from 'lucide-react';

import { getErrorMessage } from '../api/client';
import { searchLocations, type PropertyLocationSuggestion } from '../api/properties';
import type { Locale } from '../i18n';

interface LocationSearchInputProps {
  id: string;
  value: string;
  locale: Locale;
  placeholder: string;
  onChange: (value: string) => void;
  onSelect: (location: PropertyLocationSuggestion) => void;
}

export function LocationSearchInput({
  id,
  value,
  locale,
  placeholder,
  onChange,
  onSelect,
}: LocationSearchInputProps) {
  const [suggestions, setSuggestions] = useState<PropertyLocationSuggestion[]>([]);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [error, setError] = useState('');
  const [open, setOpen] = useState(false);
  const listboxId = `${id}-suggestions`;
  const requestRef = useRef<AbortController | null>(null);

  useEffect(() => {
    requestRef.current?.abort();
    if (value.trim().length < 2) {
      setSuggestions([]);
      setOpen(false);
      setError('');
      return;
    }

    const controller = new AbortController();
    requestRef.current = controller;
    const timer = window.setTimeout(() => {
      void searchLocations(value.trim(), controller.signal)
        .then((results) => {
          setSuggestions(results);
          setActiveIndex(-1);
          setError('');
          setOpen(results.length > 0);
        })
        .catch((requestError: unknown) => {
          if (controller.signal.aborted) return;
          setSuggestions([]);
          setOpen(false);
          setError(getErrorMessage(requestError));
        });
    }, 250);

    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [value]);

  const choose = (location: PropertyLocationSuggestion) => {
    onSelect(location);
    setSuggestions([]);
    setOpen(false);
    setActiveIndex(-1);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'ArrowDown' && suggestions.length) {
      event.preventDefault();
      setOpen(true);
      setActiveIndex((index) => (index + 1) % suggestions.length);
    } else if (event.key === 'ArrowUp' && suggestions.length) {
      event.preventDefault();
      setOpen(true);
      setActiveIndex((index) => (index <= 0 ? suggestions.length - 1 : index - 1));
    } else if (event.key === 'Enter' && open && activeIndex >= 0) {
      event.preventDefault();
      choose(suggestions[activeIndex]);
    } else if (event.key === 'Escape') {
      setOpen(false);
      setActiveIndex(-1);
    }
  };

  return (
    <div className="location-search-control">
      <span className="search-input-wrap">
        <MapPin size={17} aria-hidden="true" />
        <input
          id={id}
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={open}
          aria-controls={listboxId}
          aria-activedescendant={activeIndex >= 0 ? `${listboxId}-${suggestions[activeIndex].id}` : undefined}
          autoComplete="off"
          placeholder={placeholder}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => suggestions.length > 0 && setOpen(true)}
          onBlur={() => window.setTimeout(() => setOpen(false), 100)}
        />
      </span>
      {error && <span className="location-search-error" role="status">{error}</span>}
      {open && suggestions.length > 0 && (
        <ul className="location-search-suggestions" id={listboxId} role="listbox">
          {suggestions.map((location, index) => (
            <li
              id={`${listboxId}-${location.id}`}
              key={location.id}
              role="option"
              aria-selected={index === activeIndex}
            >
              <div
                className="location-search-option"
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => choose(location)}
              >
                <span>{locale === 'am' && location.name_am ? location.name_am : location.name}</span>
                {locale === 'am' && location.name_am && <small>{location.name}</small>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
