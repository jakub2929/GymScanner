'use client';

import { useRouter } from 'next/navigation';
import { useSetAtom } from 'jotai';
import { setOwnerTokenAtom } from '@/lib/authStore';

export function useOwnerLogout(defaultRedirect = '/owner/login') {
  const router = useRouter();
  const setOwnerToken = useSetAtom(setOwnerTokenAtom);

  return async function logout(redirectTo?: string) {
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('owner_access_token');
      sessionStorage.removeItem('owner_email');
      sessionStorage.removeItem('owner_name');
    }
    setOwnerToken(null);
    router.push(redirectTo ?? defaultRedirect);
  };
}
