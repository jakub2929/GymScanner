'use client';

import { useRouter } from 'next/navigation';
import { useSetAtom } from 'jotai';
import { setTokenAtom } from '@/lib/authStore';
import { apiClient } from '@/lib/apiClient';

export function useLogout() {
  const router = useRouter();
  const setToken = useSetAtom(setTokenAtom);

  return async function logout() {
    try {
      await apiClient('/api/logout', { method: 'POST' });
    } catch (error) {
      console.warn('Logout call failed', error);
    } finally {
      setToken(null);
      router.push('/login');
    }
  };
}
