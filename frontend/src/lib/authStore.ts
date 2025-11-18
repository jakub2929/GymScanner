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

export const ownerTokenAtom = atom<string | null>(null);

export const setOwnerTokenAtom = atom(null, (_get, set, newToken: string | null) => {
  if (typeof window !== 'undefined') {
    if (newToken) {
      sessionStorage.setItem('owner_access_token', newToken);
    } else {
      sessionStorage.removeItem('owner_access_token');
    }
  }
  set(ownerTokenAtom, newToken);
});
