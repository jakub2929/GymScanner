'use client';

import { useBranding } from '@/components/branding-context';
import { resolveBrandingAssetUrl } from '@/lib/branding';
import { defaultBranding } from '@/types/branding';

export function useBrandingLogo(): string | null {
  const branding = useBranding();
  return resolveBrandingAssetUrl(branding.logoUrl ?? defaultBranding.logoUrl);
}
