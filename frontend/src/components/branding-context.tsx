'use client';

import { createContext, ReactNode, useContext, useEffect } from 'react';
import type { BrandingConfig } from '@/types/branding';
import { defaultBranding } from '@/types/branding';

const BrandingContext = createContext<BrandingConfig>(defaultBranding);

function hexToRgb(hex: string) {
  const normalized = hex.replace('#', '');
  if (normalized.length !== 6) return null;
  const bigint = Number.parseInt(normalized, 16);
  if (Number.isNaN(bigint)) return null;
  const r = (bigint >> 16) & 255;
  const g = (bigint >> 8) & 255;
  const b = bigint & 255;
  return { r, g, b };
}

export function BrandingProvider({ value, children }: { value: BrandingConfig; children: ReactNode }) {
  useEffect(() => {
    if (typeof document === 'undefined') return;
    document.documentElement.style.setProperty('--brand-primary', value.primaryColor);
    const rgb = hexToRgb(value.primaryColor);
    if (rgb) {
      document.documentElement.style.setProperty('--brand-primary-rgb', `${rgb.r} ${rgb.g} ${rgb.b}`);
    }
  }, [value.primaryColor]);

  return <BrandingContext.Provider value={value}>{children}</BrandingContext.Provider>;
}

export function useBranding() {
  return useContext(BrandingContext);
}
