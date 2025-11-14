'use client';

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/apiClient';
import type { AdminToken, AdminUser } from '@/types/admin';

function formatDate(value?: string | null) {
  if (!value) return '---';
  return new Date(value).toLocaleString('cs-CZ', { hour12: false });
}

export default function AdminOverviewPage() {
  const usersQuery = useQuery<AdminUser[]>({
    queryKey: ['admin-users', ''],
    queryFn: () => apiClient('/api/admin/users'),
  });

  const tokensQuery = useQuery<AdminToken[]>({
    queryKey: ['admin-tokens'],
    queryFn: () => apiClient('/api/admin/tokens'),
  });

  const stats = useMemo(() => {
    const users = usersQuery.data ?? [];
    const tokens = tokensQuery.data ?? [];
    const totalUsers = users.length;
    const admins = users.filter((u) => u.is_admin).length;
    const totalCredits = users.reduce((sum, user) => sum + (user.credits ?? 0), 0);
    const activeTokens = tokens.filter((token) => token.is_active).length;
    return { totalUsers, admins, totalCredits, activeTokens };
  }, [usersQuery.data, tokensQuery.data]);

  const recentUsers = useMemo(() => {
    const users = usersQuery.data ?? [];
    return [...users]
      .sort((a, b) => (b.created_at ? new Date(b.created_at).getTime() : 0) - (a.created_at ? new Date(a.created_at).getTime() : 0))
      .slice(0, 5);
  }, [usersQuery.data]);

  const recentTokens = useMemo(() => {
    const tokens = tokensQuery.data ?? [];
    return [...tokens]
      .sort((a, b) => (b.created_at ? new Date(b.created_at).getTime() : 0) - (a.created_at ? new Date(a.created_at).getTime() : 0))
      .slice(0, 6);
  }, [tokensQuery.data]);

  const isLoading = usersQuery.isPending || tokensQuery.isPending;

  return (
    <div className="space-y-10">
      {(usersQuery.isError || tokensQuery.isError) && (
        <div className="glass-panel rounded-3xl p-4 text-sm text-rose-200 border border-rose-500/30">
          Nepodařilo se načíst všechna data. Zkus obnovit stránku nebo zkontroluj API.
        </div>
      )}

      <section className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
        <div className="glass-panel rounded-3xl p-6">
          <p className="text-xs uppercase tracking-[0.35em] text-slate-400">Uživatelé</p>
          <p className="text-4xl font-semibold mt-3">{stats.totalUsers}</p>
          <p className="text-slate-400 text-sm mt-2">Za posledních 100 registrací</p>
        </div>
        <div className="glass-panel rounded-3xl p-6">
          <p className="text-xs uppercase tracking-[0.35em] text-slate-400">Administrátoři</p>
          <p className="text-4xl font-semibold mt-3">{stats.admins}</p>
          <p className="text-slate-400 text-sm mt-2">Mají přístup do admin portálu</p>
        </div>
        <div className="glass-panel rounded-3xl p-6">
          <p className="text-xs uppercase tracking-[0.35em] text-slate-400">Kredity v oběhu</p>
          <p className="text-4xl font-semibold mt-3">{stats.totalCredits}</p>
          <p className="text-slate-400 text-sm mt-2">Součet aktuálních zůstatků</p>
        </div>
        <div className="glass-panel rounded-3xl p-6">
          <p className="text-xs uppercase tracking-[0.35em] text-slate-400">Aktivní tokeny</p>
          <p className="text-4xl font-semibold mt-3">{stats.activeTokens}</p>
          <p className="text-slate-400 text-sm mt-2">Připravené ke skenování</p>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="glass-panel rounded-3xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-semibold">Poslední uživatelé</h2>
            <p className="text-sm text-slate-400">{isLoading ? '...' : `${recentUsers.length} položek`}</p>
          </div>
          <div className="space-y-3 text-sm">
            {recentUsers.map((user) => (
              <div key={user.id} className="glass-subcard rounded-2xl p-4 flex items-center justify-between">
                <div>
                  <p className="font-semibold">{user.name}</p>
                  <p className="text-slate-400">{user.email}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-slate-400">Kredity</p>
                  <p className="text-lg font-semibold text-emerald-300">{user.credits}</p>
                </div>
              </div>
            ))}
            {!recentUsers.length && !isLoading && <p className="text-slate-500">Žádná data k zobrazení.</p>}
          </div>
        </section>

        <section className="glass-panel rounded-3xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-2xl font-semibold">Aktivita tokenů</h2>
            <p className="text-sm text-slate-400">{isLoading ? '...' : `${recentTokens.length} položek`}</p>
          </div>
          <div className="space-y-4 text-sm">
            {recentTokens.map((token) => (
              <div key={token.id} className="glass-subcard rounded-2xl p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-mono text-xs text-slate-400">{token.token.slice(0, 16)}...</p>
                    <p className="font-semibold mt-1">{token.user_name ?? 'Neznámý uživatel'}</p>
                  </div>
                  <span
                    className={`px-3 py-1 rounded-full text-xs ${
                      token.is_active ? 'bg-emerald-500/20 text-emerald-200' : 'bg-rose-500/20 text-rose-200'
                    }`}
                  >
                    {token.is_active ? 'Aktivní' : 'Vypnuto'}
                  </span>
                </div>
                <p className="text-slate-500 text-xs mt-2">Vytvořeno: {formatDate(token.created_at)}</p>
              </div>
            ))}
            {!recentTokens.length && !isLoading && <p className="text-slate-500">Žádná data k zobrazení.</p>}
          </div>
        </section>
      </div>
    </div>
  );
}
