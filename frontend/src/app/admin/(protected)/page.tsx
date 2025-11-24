'use client';

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/apiClient';
import type { AdminMembershipPackage, AdminToken, AdminUser, AdminScanLog, AdminPresenceSession } from '@/types/admin';

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
  const packagesQuery = useQuery<AdminMembershipPackage[]>({
    queryKey: ['admin-packages'],
    queryFn: () => apiClient('/api/admin/membership-packages?include_inactive=true'),
  });
  const scanLogsQuery = useQuery<AdminScanLog[]>({
    queryKey: ['admin-scan-logs'],
    queryFn: () => apiClient('/api/admin/scan-logs?limit=8'),
  });
  const presenceQuery = useQuery<AdminPresenceSession[]>({
    queryKey: ['admin-presence-active'],
    queryFn: () => apiClient('/api/admin/presence/active'),
  });

  const stats = useMemo(() => {
    const users = usersQuery.data ?? [];
    const tokens = tokensQuery.data ?? [];
    const packages = packagesQuery.data ?? [];
    const totalUsers = users.length;
    const admins = users.filter((u) => u.is_admin).length;
    const activeTokens = tokens.filter((token) => token.is_active).length;
    const activeMembershipPackages = packages.filter((pkg) => pkg.is_active && pkg.package_type === 'membership').length;
    const activeTrainingPackages = packages.filter((pkg) => pkg.is_active && pkg.session_limit).length;
    return { totalUsers, admins, activeTokens, activeMembershipPackages, activeTrainingPackages };
  }, [usersQuery.data, tokensQuery.data, packagesQuery.data]);

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

  const isLoading = usersQuery.isPending || tokensQuery.isPending || packagesQuery.isPending || scanLogsQuery.isPending;

  return (
    <div className="space-y-10">
      {(usersQuery.isError || tokensQuery.isError || scanLogsQuery.isError) && (
        <div className="glass-panel rounded-3xl p-4 text-sm text-rose-200 border border-rose-500/30">
          Nepodařilo se načíst všechna data. Zkus obnovit stránku nebo zkontroluj API.
        </div>
      )}

      <section className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
        <div className="glass-panel rounded-3xl p-6">
          <p className="text-xs uppercase tracking-[0.35em] text-slate-400">Uživatelé</p>
          <p className="text-4xl font-semibold mt-3">{stats.totalUsers}</p>
          <p className="text-slate-400 text-sm mt-2">Aktivní účty ({stats.admins} adminů)</p>
        </div>
        <div className="glass-panel rounded-3xl p-6">
          <p className="text-xs uppercase tracking-[0.35em] text-slate-400">Permanentky</p>
          <p className="text-4xl font-semibold mt-3">{stats.activeMembershipPackages}</p>
          <p className="text-slate-400 text-sm mt-2">Aktivních balíčků v prodeji</p>
        </div>
        <div className="glass-panel rounded-3xl p-6">
          <p className="text-xs uppercase tracking-[0.35em] text-slate-400">Osobní tréninky</p>
          <p className="text-4xl font-semibold mt-3">{stats.activeTrainingPackages}</p>
          <p className="text-slate-400 text-sm mt-2">Balíčků se sledováním sezení</p>
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
            <h2 className="text-2xl font-semibold">V gymu právě</h2>
            <p className="text-sm text-slate-400">
              {presenceQuery.isPending ? '...' : `${presenceQuery.data?.length ?? 0} lidí`}
            </p>
          </div>
          <div className="space-y-3 text-sm">
            {(presenceQuery.data ?? []).map((session) => (
              <div key={session.id} className="glass-subcard rounded-2xl p-4 space-y-1">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold">{session.user_name ?? 'Neznámý uživatel'}</p>
                    <p className="text-xs text-slate-400">{session.user_email ?? ''}</p>
                  </div>
                  <span className="px-3 py-1 rounded-full text-xs bg-emerald-500/20 text-emerald-200">Uvnitř</span>
                </div>
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <p>Od: {formatDate(session.started_at)}</p>
                  <p>Session ID: {session.id}</p>
                </div>
                {session.metadata?.membership_id && (
                  <p className="text-xs text-slate-500">Permanentka ID: {session.metadata.membership_id as number}</p>
                )}
              </div>
            ))}
            {!presenceQuery.isPending && !(presenceQuery.data?.length ?? 0) && (
              <p className="text-slate-500">Teď není uvnitř nikdo.</p>
            )}
          </div>
        </section>

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
                  <p className="text-xs text-slate-400">Role</p>
                  <p className="text-lg font-semibold text-emerald-300">{user.is_admin ? 'Admin' : 'Uživatel'}</p>
                  <p className="text-xs text-slate-500 mt-1">{user.created_at ? new Date(user.created_at).toLocaleDateString('cs-CZ') : '---'}</p>
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
                    <p className="font-mono text-xs text-slate-400">{token.token.slice(0, 10)}…</p>
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
                <div className="flex items-center justify-between text-xs text-slate-500 mt-2">
                  <p>Vytvořeno: {formatDate(token.created_at)}</p>
                  <p>Skenů: {token.scan_count}</p>
                </div>
              </div>
            ))}
            {!recentTokens.length && !isLoading && <p className="text-slate-500">Žádná data k zobrazení.</p>}
          </div>
        </section>
      </div>

      <section className="glass-panel rounded-3xl p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-semibold">Logy skenů</h2>
          <p className="text-sm text-slate-400">
            {scanLogsQuery.isPending ? '...' : `${scanLogsQuery.data?.length ?? 0} položek`}
          </p>
        </div>
        <div className="space-y-4 text-sm">
          {(scanLogsQuery.data ?? []).map((log) => {
            const membershipInfo =
              (log.metadata as {
                membership_id?: number;
                package_id?: number;
                package_name?: string;
                membership_status?: string;
                daily_limit_hit?: boolean;
              } | undefined) || {};
            return (
              <div key={log.id} className="glass-subcard rounded-2xl p-4 space-y-1">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="font-semibold">{log.user_name ?? 'Neznámý uživatel'}</p>
                    <p className="text-xs text-slate-400">{formatDate(log.created_at)}</p>
                  </div>
                  <span
                    className={`px-3 py-1 rounded-full text-xs ${
                      log.allowed ? 'bg-emerald-500/20 text-emerald-200' : 'bg-rose-500/20 text-rose-200'
                    }`}
                  >
                    {log.allowed ? 'Povoleno' : 'Zamítnuto'}
                  </span>
                </div>
                <p className="text-slate-300 text-sm">
                  Důvod: <span className="font-mono text-xs">{log.reason ?? '---'}</span>
                </p>
                <p className="text-slate-500 text-xs">Status: {log.status}</p>
                <div className="text-slate-400 text-xs space-y-1">
                  {(membershipInfo.membership_id || membershipInfo.package_id) && (
                    <p>
                      Permanentka ID: {membershipInfo.membership_id ?? '---'} / Balíček: {membershipInfo.package_id ?? '---'}
                    </p>
                  )}
                  {membershipInfo.membership_status && <p>Stav: {membershipInfo.membership_status}</p>}
                  {membershipInfo.daily_limit_hit && <p>Denní limit vyčerpán</p>}
                </div>
              </div>
            );
          })}
          {!scanLogsQuery.isPending && !(scanLogsQuery.data?.length ?? 0) && (
            <p className="text-slate-500 text-sm">Žádné záznamy k zobrazení.</p>
          )}
        </div>
      </section>
    </div>
  );
}
