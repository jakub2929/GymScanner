'use client';

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/apiClient';
import type { AdminMembershipPackage, AdminUser, AdminPresenceSession } from '@/types/admin';

function formatDate(value?: string | null) {
  if (!value) return '---';
  return new Date(value).toLocaleString('cs-CZ', { hour12: false });
}

export default function AdminOverviewPage() {
  const usersQuery = useQuery<AdminUser[]>({
    queryKey: ['admin-users', ''],
    queryFn: () => apiClient('/api/admin/users'),
  });

  const packagesQuery = useQuery<AdminMembershipPackage[]>({
    queryKey: ['admin-packages'],
    queryFn: () => apiClient('/api/admin/membership-packages?include_inactive=true'),
  });
  const presenceQuery = useQuery<AdminPresenceSession[]>({
    queryKey: ['admin-presence-active'],
    queryFn: () => apiClient('/api/admin/presence/active'),
  });

  const stats = useMemo(() => {
    const users = usersQuery.data ?? [];
    const packages = packagesQuery.data ?? [];
    const totalUsers = users.length;
    const admins = users.filter((u) => u.is_admin).length;
    const activeMembershipPackages = packages.filter((pkg) => pkg.is_active && pkg.package_type === 'membership').length;
    const activeTrainingPackages = packages.filter((pkg) => pkg.is_active && pkg.session_limit).length;
    const activePresence = presenceQuery.data?.length ?? 0;
    return { totalUsers, admins, activeMembershipPackages, activeTrainingPackages, activePresence };
  }, [usersQuery.data, packagesQuery.data, presenceQuery.data]);

  const activeMembershipPackages = useMemo(
    () => (packagesQuery.data ?? []).filter((pkg) => pkg.is_active && pkg.package_type === 'membership'),
    [packagesQuery.data]
  );
  const activeTrainingPackages = useMemo(
    () => (packagesQuery.data ?? []).filter((pkg) => pkg.is_active && pkg.package_type !== 'membership'),
    [packagesQuery.data]
  );

  const isLoading = usersQuery.isPending || packagesQuery.isPending;

  return (
    <div className="space-y-10">
      {(usersQuery.isError || packagesQuery.isError) && (
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
          <p className="text-xs uppercase tracking-[0.35em] text-slate-400">V gymu</p>
          <p className="text-4xl font-semibold mt-3">{stats.activePresence}</p>
          <p className="text-slate-400 text-sm mt-2">Aktuálně přítomných</p>
        </div>
      </section>

      <div className="grid gap-6">
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
                {(() => {
                  const meta = session.metadata as { membership_id?: number } | undefined;
                  return meta?.membership_id ? (
                    <p className="text-xs text-slate-500">Permanentka ID: {meta.membership_id}</p>
                  ) : null;
                })()}
              </div>
            ))}
            {!presenceQuery.isPending && !(presenceQuery.data?.length ?? 0) && (
              <p className="text-slate-500">Teď není uvnitř nikdo.</p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
