'use client';

import { useRouter } from 'next/navigation';
import { useSetAtom } from 'jotai';
import { setTokenAtom } from '@/lib/authStore';
import { apiClient } from '@/lib/apiClient';

export function useLogout(defaultRedirect = '/login') {
  const router = useRouter();
  const setToken = useSetAtom(setTokenAtom);

  return async function logout(redirectTo?: string) {
    try {
      await apiClient('/api/logout', { method: 'POST' });
    } catch (error) {
      console.warn('Logout call failed', error);
    } finally {
      if (typeof window !== 'undefined') {
        sessionStorage.removeItem('user_name');
        sessionStorage.removeItem('user_email');
        sessionStorage.removeItem('is_admin');
      }
      setToken(null);
      router.push(redirectTo ?? defaultRedirect);
    }
  };
}
