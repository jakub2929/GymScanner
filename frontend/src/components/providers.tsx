'use client';

import { QueryClientProvider } from '@tanstack/react-query';
import { ReactNode, useEffect } from 'react';
import { getQueryClient } from '@/lib/queryClient';
import { Provider as JotaiProvider, useSetAtom } from 'jotai';
import { setTokenAtom } from '@/lib/authStore';

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

export function Providers({ children }: { children: ReactNode }) {
  const queryClient = getQueryClient();
  return (
    <JotaiProvider>
      <QueryClientProvider client={queryClient}>
        <TokenHydrator>{children}</TokenHydrator>
      </QueryClientProvider>
    </JotaiProvider>
  );
}
