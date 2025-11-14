'use client';

import Image from 'next/image';
import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/apiClient';
import type { AdminToken } from '@/types/admin';
import { Toast, useToast } from '@/components/toast';

export default function AdminTokensPage() {
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive'>('all');
  const { toast, showToast } = useToast();
  const queryClient = useQueryClient();

  const tokensQuery = useQuery<AdminToken[]>({
    queryKey: ['admin-tokens'],
    queryFn: () => apiClient('/api/admin/tokens'),
  });

  const toggleMutation = useMutation({
    mutationFn: async (payload: { tokenId: number; action: 'activate' | 'deactivate' }) =>
      apiClient(`/api/admin/tokens/${payload.tokenId}/${payload.action}`, {
        method: 'POST',
      }),
    onSuccess: (_, variables) => {
      showToast(variables.action === 'activate' ? 'Token aktivován' : 'Token deaktivován');
      queryClient.invalidateQueries({ queryKey: ['admin-tokens'] });
    },
    onError: (error) => {
      showToast(error instanceof Error ? error.message : 'Nepodařilo se upravit token', 'error');
    },
  });

  const filteredTokens = useMemo(() => {
    if (!tokensQuery.data) return [];
    if (statusFilter === 'all') return tokensQuery.data;
    return tokensQuery.data.filter((token) => (statusFilter === 'active' ? token.is_active : !token.is_active));
  }, [statusFilter, tokensQuery.data]);

  return (
    <>
      <div className="space-y-6">
        <section className="glass-panel rounded-3xl p-6 space-y-4">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <h1 className="text-3xl font-semibold">Tokeny</h1>
              <p className="text-slate-400 text-sm mt-2">Řiď aktivaci tokenů a sleduj poslední QR kódy.</p>
            </div>
            <div className="flex gap-2 bg-white/5 rounded-full p-1 text-xs">
              {[
                { value: 'all', label: 'Vše' },
                { value: 'active', label: 'Aktivní' },
                { value: 'inactive', label: 'Deaktivované' },
              ].map((option) => (
                <button
                  key={option.value}
                  className={`px-4 py-2 rounded-full ${
                    statusFilter === option.value ? 'bg-white text-slate-900 font-semibold' : 'text-slate-300'
                  }`}
                  onClick={() => setStatusFilter(option.value as 'all' | 'active' | 'inactive')}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-slate-400 text-left">
                  <th className="py-3">QR</th>
                  <th className="py-3">Token</th>
                  <th className="py-3">Uživatel</th>
                  <th className="py-3">Status</th>
                  <th className="py-3">Scan count</th>
                  <th className="py-3">Vytvořeno</th>
                  <th className="py-3 text-right">Akce</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {filteredTokens.map((token) => (
                  <tr key={token.id} className="text-slate-100">
                    <td className="py-4">
                      <Image
                        src={token.qr_code_url}
                        alt="QR preview"
                        width={64}
                        height={64}
                        unoptimized
                        className="w-16 h-16 rounded-xl border border-white/10 object-cover"
                      />
                    </td>
                    <td className="py-4 font-mono text-xs">{token.token}</td>
                    <td className="py-4">
                      <p className="font-medium">{token.user_name ?? 'Neznámý'}</p>
                      <p className="text-slate-400">{token.user_email ?? '---'}</p>
                    </td>
                    <td className="py-4">
                      <span
                        className={`px-3 py-1 rounded-full text-xs ${
                          token.is_active ? 'bg-emerald-500/20 text-emerald-200' : 'bg-rose-500/20 text-rose-200'
                        }`}
                      >
                        {token.is_active ? 'Aktivní' : 'Vypnuto'}
                      </span>
                    </td>
                    <td className="py-4">{token.scan_count}</td>
                    <td className="py-4 text-slate-400">
                      {token.created_at ? new Date(token.created_at).toLocaleString('cs-CZ') : '---'}
                    </td>
                    <td className="py-4 text-right">
                      <button
                        className="secondary-button"
                        disabled={toggleMutation.isPending}
                        onClick={() =>
                          toggleMutation.mutate({
                            tokenId: token.id,
                            action: token.is_active ? 'deactivate' : 'activate',
                          })
                        }
                      >
                        {token.is_active ? 'Deaktivovat' : 'Aktivovat'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {tokensQuery.isPending && <p className="text-slate-400 text-sm mt-4">Načítám tokeny...</p>}
            {tokensQuery.isError && (
              <p className="text-rose-300 text-sm mt-4">Nepodařilo se načíst tokeny. Obnov prosím stránku.</p>
            )}
            {!tokensQuery.isPending && !filteredTokens.length && (
              <p className="text-slate-400 text-sm mt-4">Žádné tokeny pro zvolený filtr.</p>
            )}
          </div>
        </section>
      </div>

      <Toast toast={toast} />
    </>
  );
}
