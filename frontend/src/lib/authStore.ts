'use client';

import { atom } from 'jotai';

export const tokenAtom = atom<string | null>(null);

export const setTokenAtom = atom(null, (_get, set, newToken: string | null) => {
  if (typeof window !== 'undefined') {
    if (newToken) {
      sessionStorage.setItem('access_token', newToken);
    } else {
      sessionStorage.removeItem('access_token');
    }
  }
  set(tokenAtom, newToken);
});
