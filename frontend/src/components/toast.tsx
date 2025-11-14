'use client';

import { useState } from 'react';

export type ToastState = { message: string; type: 'success' | 'error' } | null;

export function useToast() {
  const [toast, setToast] = useState<ToastState>(null);

  function showToast(message: string, type: 'success' | 'error' = 'success') {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  }

  return { toast, showToast };
}

export function Toast({ toast }: { toast: ToastState }) {
  if (!toast) return null;
  const base = 'fixed bottom-6 right-6 px-6 py-3 rounded-2xl text-sm shadow-2xl backdrop-blur';
  const theme =
    toast.type === 'error'
      ? 'bg-rose-500/20 border border-rose-300/40 text-rose-50'
      : 'bg-emerald-400/30 border border-emerald-200/50 text-emerald-50';

  return <div className={`${base} ${theme}`}>{toast.message}</div>;
}
