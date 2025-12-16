'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { apiClient } from '@/lib/apiClient';
import type { AdminApiKey } from '@/types/admin';
import { Toast, useToast } from '@/components/toast';

export default function AdminApiKeysPage() {
  const queryClient = useQueryClient();
  const { toast, showToast } = useToast();
  const [name, setName] = useState('');
  const [revealedToken, setRevealedToken] = useState<string | null>(null);

  const keysQuery = useQuery<AdminApiKey[]>({
    queryKey: ['admin-api-keys'],
    queryFn: () => apiClient('/api/admin/api-keys'),
  });

  const createMutation = useMutation({
    mutationFn: async () =>
      apiClient<AdminApiKey>('/api/admin/api-keys', {
        method: 'POST',
        body: JSON.stringify({ name: name.trim() }),
      }),
    onSuccess: (data) => {
      setRevealedToken(data.token ?? null);
      setName('');
      showToast('API klíč vytvořen');
      queryClient.invalidateQueries({ queryKey: ['admin-api-keys'] });
    },
    onError: (error) => {
      showToast(error instanceof Error ? error.message : 'Nepodařilo se vytvořit klíč', 'error');
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (keyId: number) =>
      apiClient(`/api/admin/api-keys/${keyId}/revoke`, {
        method: 'POST',
      }),
    onSuccess: () => {
      showToast('Klíč deaktivován');
      queryClient.invalidateQueries({ queryKey: ['admin-api-keys'] });
    },
    onError: (error) => {
      showToast(error instanceof Error ? error.message : 'Nepodařilo se deaktivovat klíč', 'error');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (keyId: number) =>
      apiClient(`/api/admin/api-keys/${keyId}`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      showToast('Klíč smazán');
      queryClient.invalidateQueries({ queryKey: ['admin-api-keys'] });
    },
    onError: (error) => {
      showToast(error instanceof Error ? error.message : 'Nepodařilo se smazat klíč', 'error');
    },
  });

  const activeKeys = useMemo(
    () => (keysQuery.data || []).filter((k) => k.is_active),
    [keysQuery.data],
  );

  return (
    <>
      <div className="space-y-6">
        <section className="glass-panel rounded-3xl p-6 space-y-4">
          <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div>
              <h1 className="text-3xl font-semibold">API klíče</h1>
              <p className="text-slate-400 text-sm mt-2">
                Vytvářej a spravuj serverové klíče pro integrace. Tajný klíč uvidíš jen jednou při vytvoření.
              </p>
            </div>
            <div className="text-sm text-slate-300">
              <span className="px-3 py-1 rounded-full bg-white/5 border border-white/10">
                Aktivní: {activeKeys.length}
              </span>
            </div>
          </div>

          <div className="glass-subcard rounded-2xl p-4 space-y-4">
            <h2 className="text-xl font-semibold">Vytvořit nový klíč</h2>
            <div className="grid gap-3 md:grid-cols-1">
              <label className="space-y-1">
                <span className="text-sm text-slate-300">Název</span>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Např. Zapojení partnera"
                  className="w-full rounded-xl bg-white/5 border border-white/10 px-3 py-2 text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-white/20"
                />
              </label>
            </div>
            <div className="flex items-center gap-3">
              <button
                className="accent-button"
                disabled={!name.trim() || createMutation.isPending}
                onClick={() => createMutation.mutate()}
              >
                {createMutation.isPending ? 'Vytvářím…' : 'Vytvořit klíč'}
              </button>
              <p className="text-sm text-slate-400">Klíč se ukáže jen jednou – ulož si ho bezpečně.</p>
            </div>
            {revealedToken && (
              <div className="rounded-xl bg-emerald-500/10 border border-emerald-500/30 p-4">
                <p className="text-sm text-emerald-200 mb-2">Nový API klíč (zobrazí se jen jednou):</p>
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                  <code className="font-mono text-sm break-all text-white">{revealedToken}</code>
                  <button
                    className="secondary-button"
                    onClick={() => navigator.clipboard.writeText(revealedToken)}
                  >
                    Zkopírovat
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="space-y-3">
            <h2 className="text-xl font-semibold">Existující klíče</h2>
            {keysQuery.isPending && <p className="text-slate-400 text-sm">Načítám klíče…</p>}
            {keysQuery.isError && <p className="text-rose-300 text-sm">Nepodařilo se načíst klíče.</p>}
            {!keysQuery.isPending && (keysQuery.data || []).length === 0 && (
              <p className="text-slate-400 text-sm">Zatím nemáš žádné klíče.</p>
            )}
            <div className="flex flex-col gap-3">
              {(keysQuery.data || []).map((key) => (
                <div key={key.id} className="glass-subcard rounded-2xl p-4 space-y-2 border border-white/5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="text-lg font-semibold">{key.name}</p>
                      <p className="text-xs text-slate-400">Prefix: {key.prefix}</p>
                    </div>
                    <span
                      className={`px-3 py-1 rounded-full text-xs ${
                        key.is_active ? 'bg-emerald-500/20 text-emerald-200' : 'bg-rose-500/20 text-rose-200'
                      }`}
                    >
                      {key.is_active ? 'Aktivní' : 'Deaktivováno'}
                    </span>
                  </div>
                  <div className="text-xs text-slate-400 space-y-1">
                    <p>Vytvořeno: {key.created_at ? new Date(key.created_at).toLocaleString('cs-CZ') : '---'}</p>
                  </div>
                  <div className="flex gap-2 flex-wrap">
                    <button
                      className="secondary-button"
                      disabled={!key.is_active || revokeMutation.isPending}
                      onClick={() => revokeMutation.mutate(key.id)}
                    >
                      Deaktivovat
                    </button>
                    <button
                      className="danger-button"
                      disabled={deleteMutation.isPending}
                      onClick={() => deleteMutation.mutate(key.id)}
                    >
                      Smazat
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      </div>
      <Toast toast={toast} />
    </>
  );
}
