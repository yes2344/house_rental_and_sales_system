import { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, ArrowRight } from 'lucide-react';

import { PropertyPhoto } from './PropertyPhoto';

export interface SlideshowImage {
  id: number;
  url: string | null;
  caption: string;
  is_primary: boolean;
}

interface PropertySlideshowProps {
  images: SlideshowImage[];
  fallbackImage?: string | null;
  title: string;
  fallbackLabel: string;
  previousLabel: string;
  nextLabel: string;
  photoLabel: string;
}

export function PropertySlideshow({
  images,
  fallbackImage,
  title,
  fallbackLabel,
  previousLabel,
  nextLabel,
  photoLabel,
}: PropertySlideshowProps) {
  const orderedImages = useMemo(
    () => [...images].filter((image) => image.url).sort(
      (first, second) => Number(second.is_primary) - Number(first.is_primary),
    ),
    [images],
  );
  const [currentIndex, setCurrentIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const [motionReduced, setMotionReduced] = useState(false);

  useEffect(() => setCurrentIndex(0), [orderedImages]);

  useEffect(() => {
    const mediaPreference = window.matchMedia('(prefers-reduced-motion: reduce)');
    const updateMotionPreference = () => {
      setMotionReduced(
        mediaPreference.matches || document.documentElement.dataset.reducedMotion === 'reduce',
      );
    };
    const observer = new MutationObserver(updateMotionPreference);
    mediaPreference.addEventListener('change', updateMotionPreference);
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-reduced-motion'],
    });
    updateMotionPreference();
    return () => {
      mediaPreference.removeEventListener('change', updateMotionPreference);
      observer.disconnect();
    };
  }, []);

  useEffect(() => {
    if (paused || orderedImages.length < 2 || motionReduced) {
      return undefined;
    }
    const timer = window.setInterval(() => {
      setCurrentIndex((current) => (current + 1) % orderedImages.length);
    }, 3000);
    return () => window.clearInterval(timer);
  }, [motionReduced, orderedImages.length, paused]);

  const move = (offset: number) => {
    setCurrentIndex((current) => (
      (current + offset + orderedImages.length) % orderedImages.length
    ));
  };
  const active = orderedImages[currentIndex];

  return (
    <div
      className="property-slideshow"
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocusCapture={() => setPaused(true)}
      onBlurCapture={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setPaused(false);
      }}
    >
      {active ? (
        <PropertyPhoto
          key={active.id}
          src={active.url}
          alt={`${title} — ${active.caption || photoLabel}`}
          className="listing-image"
          fallbackClassName="listing-image listing-image-placeholder"
          fallbackLabel={fallbackLabel}
        />
      ) : (
        <PropertyPhoto
          src={fallbackImage}
          alt=""
          className="listing-image"
          fallbackClassName="listing-image listing-image-placeholder"
          fallbackLabel={fallbackLabel}
        />
      )}
      {orderedImages.length > 1 && (
        <>
          <button
            className="slideshow-arrow slideshow-previous"
            type="button"
            aria-label={previousLabel}
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
              move(-1);
            }}
          >
            <ArrowLeft size={15} aria-hidden="true" />
          </button>
          <button
            className="slideshow-arrow slideshow-next"
            type="button"
            aria-label={nextLabel}
            onClick={(event) => {
              event.preventDefault();
              event.stopPropagation();
              move(1);
            }}
          >
            <ArrowRight size={15} aria-hidden="true" />
          </button>
          <div className="slideshow-dots" aria-label={`${currentIndex + 1} / ${orderedImages.length}`}>
            {orderedImages.map((image, index) => (
              <button
                className={`slideshow-dot${index === currentIndex ? ' is-active' : ''}`}
                key={image.id}
                type="button"
                aria-label={`${photoLabel} ${index + 1}`}
                aria-current={index === currentIndex ? 'true' : undefined}
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  setCurrentIndex(index);
                }}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
