'use client';

import { QueryClientProvider } from '@tanstack/react-query';
import { ReactNode, useEffect } from 'react';
import { getQueryClient } from '@/lib/queryClient';
import { Provider as JotaiProvider, useSetAtom } from 'jotai';
import { setTokenAtom, setOwnerTokenAtom } from '@/lib/authStore';
import { BrandingProvider } from './branding-context';
import type { BrandingConfig } from '@/types/branding';

function TokenHydrator({ children }: { children: ReactNode }) {
  const setToken = useSetAtom(setTokenAtom);
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const stored = sessionStorage.getItem('access_token');
    if (stored) {
      setToken(stored);
    }
  }, [setToken]);
  return <>{children}</>;
}

function OwnerTokenHydrator({ children }: { children: ReactNode }) {
  const setOwnerToken = useSetAtom(setOwnerTokenAtom);
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const stored = sessionStorage.getItem('owner_access_token');
    if (stored) {
      setOwnerToken(stored);
    }
  }, [setOwnerToken]);
  return <>{children}</>;
}

export function Providers({ children, branding }: { children: ReactNode; branding: BrandingConfig }) {
  const queryClient = getQueryClient();
  return (
    <BrandingProvider value={branding}>
      <JotaiProvider>
        <QueryClientProvider client={queryClient}>
          <TokenHydrator>
            <OwnerTokenHydrator>{children}</OwnerTokenHydrator>
          </TokenHydrator>
        </QueryClientProvider>
      </JotaiProvider>
    </BrandingProvider>
  );
}
