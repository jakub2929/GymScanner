'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/apiClient';
import type { AdminMembershipPackage, AdminUser, AdminUserMembership } from '@/types/admin';
import { useDebounce } from '@/hooks/useDebounce';
import { Toast, useToast } from '@/components/toast';

export default function AdminUsersPage() {
  const [search, setSearch] = useState('');
  const [membershipUser, setMembershipUser] = useState<AdminUser | null>(null);
  const [selectedPackageId, setSelectedPackageId] = useState<string>('');
  const [startDate, setStartDate] = useState('');
  const [autoRenew, setAutoRenew] = useState(false);
  const [sessionNotes, setSessionNotes] = useState<Record<number, string>>({});
  const { toast, showToast } = useToast();
  const queryClient = useQueryClient();

  const debouncedSearch = useDebounce(search, 400);
  const trimmedSearch = debouncedSearch.trim();
  const effectiveSearch = trimmedSearch.length >= 2 ? trimmedSearch : '';

  const usersQuery = useQuery<AdminUser[]>({
    queryKey: ['admin-users', effectiveSearch],
    queryFn: () =>
      effectiveSearch
        ? apiClient(`/api/admin/users/search?q=${encodeURIComponent(effectiveSearch)}`)
        : apiClient('/api/admin/users'),
  });
  const users = usersQuery.data ?? [];
  const packagesQuery = useQuery<AdminMembershipPackage[]>({
    queryKey: ['admin-packages'],
    queryFn: () => apiClient('/api/admin/membership-packages?include_inactive=false'),
  });
  const membershipsQuery = useQuery<AdminUserMembership[]>({
    queryKey: ['admin-user-memberships', membershipUser?.id],
    queryFn: () => apiClient(`/api/admin/users/${membershipUser!.id}/memberships`),
    enabled: !!membershipUser,
  });

  const assignMembershipMutation = useMutation({
    mutationFn: async (payload: { userId: number; packageId: number; startDate?: string; autoRenew: boolean }) =>
      apiClient(`/api/admin/users/${payload.userId}/memberships`, {
        method: 'POST',
        body: JSON.stringify({
          package_id: payload.packageId,
          start_at: payload.startDate ? new Date(payload.startDate).toISOString() : undefined,
          auto_renew: payload.autoRenew,
        }),
      }),
    onSuccess: (_, variables) => {
      showToast('Permanentka přiřazena');
      queryClient.invalidateQueries({ queryKey: ['admin-user-memberships', variables.userId] });
      setSelectedPackageId('');
      setStartDate('');
      setAutoRenew(false);
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Nepodařilo se přiřadit permanentku', 'error'),
  });

  const membershipStatusMutation = useMutation({
    mutationFn: async (payload: { userId: number; membershipId: number; status: string }) =>
      apiClient(`/api/admin/users/${payload.userId}/memberships/${payload.membershipId}/status`, {
        method: 'POST',
        body: JSON.stringify({ status: payload.status }),
      }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['admin-user-memberships', variables.userId] });
      showToast('Stav membershipu aktualizován');
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Nepodařilo se upravit stav', 'error'),
  });

  const consumeSessionMutation = useMutation({
    mutationFn: async (payload: { userId: number; membershipId: number; note?: string }) =>
      apiClient(`/api/admin/users/${payload.userId}/memberships/${payload.membershipId}/sessions/consume`, {
        method: 'POST',
        body: JSON.stringify({ count: 1, note: payload.note?.trim() || undefined }),
      }),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['admin-user-memberships', variables.userId] });
      showToast('Trénink odečten');
      setSessionNotes((prev) => {
        const next = { ...prev };
        delete next[variables.membershipId];
        return next;
      });
    },
    onError: (error) =>
      showToast(error instanceof Error ? error.message : 'Nepodařilo se odečíst trénink', 'error'),
  });

  function openMembershipModal(user: AdminUser) {
    setMembershipUser(user);
    setSelectedPackageId('');
    setStartDate('');
    setAutoRenew(false);
  }

  const formatNotes = useMemo(
    () => (notes?: string | null) => {
      if (!notes) return [];
      return notes
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean)
        .map((line, idx) => {
          const match = line.match(/^\[(.+?)\]\s*(.*)$/);
          if (!match) {
            return { key: idx, text: line };
          }
          const [, iso, rest] = match;
          const date = new Date(iso);
          const formatted = isNaN(date.getTime())
            ? iso
            : date.toLocaleString('cs-CZ', { dateStyle: 'short', timeStyle: 'short' });
          return { key: idx, text: `${formatted} — ${rest || ''}`.trim() };
        });
    },
    []
  );

  return (
    <>
      <div className="space-y-6">
        <section className="glass-panel rounded-3xl p-6 space-y-4">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h1 className="text-3xl font-semibold">Správa uživatelů</h1>
              <p className="text-slate-400 text-sm mt-2">
                Vyhledávej podle jména nebo e-mailu (min. 2 znaky pro filtrování).
              </p>
            </div>
            <div className="w-full lg:w-1/3">
              <input
                type="text"
                placeholder="Hledat uživatele"
                className="input-field"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>
          </div>
          <div className="overflow-x-auto hidden md:block">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-slate-400 text-left">
                  <th className="py-3">Jméno</th>
                  <th className="py-3">E-mail</th>
                  <th className="py-3">Role</th>
                  <th className="py-3">Registrován</th>
                  <th className="py-3 text-right">Akce</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {users.map((user) => (
                  <tr key={user.id} className="text-slate-100">
                    <td className="py-4 font-medium">{user.name}</td>
                    <td className="py-4 text-slate-400">{user.email}</td>
                    <td className="py-4">
                      <span
                        className={`px-3 py-1 rounded-full text-xs ${
                          user.is_admin ? 'bg-emerald-500/20 text-emerald-200' : 'bg-white/5 text-slate-300'
                        }`}
                      >
                        {user.is_admin ? 'Admin' : 'Uživatel'}
                      </span>
                    </td>
                    <td className="py-4 text-slate-400">
                      {user.created_at ? new Date(user.created_at).toLocaleDateString('cs-CZ') : '---'}
                    </td>
                    <td className="py-4 text-right space-x-2">
                      <button className="secondary-button" onClick={() => openMembershipModal(user)}>
                        Permanentky
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="md:hidden space-y-3">
            {users.map((user) => (
              <div key={user.id} className="glass-subcard rounded-2xl p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold">{user.name}</p>
                    <p className="text-slate-400 text-xs">{user.email}</p>
                  </div>
                  <span
                    className={`px-3 py-1 rounded-full text-xs ${
                      user.is_admin ? 'bg-emerald-500/20 text-emerald-200' : 'bg-white/5 text-slate-300'
                    }`}
                  >
                    {user.is_admin ? 'Admin' : 'Uživatel'}
                  </span>
                </div>
                <p className="text-xs text-slate-500">
                  Registrován: {user.created_at ? new Date(user.created_at).toLocaleDateString('cs-CZ') : '---'}
                </p>
                <button className="accent-button w-full" onClick={() => openMembershipModal(user)}>
                  Permanentky
                </button>
              </div>
            ))}
          </div>
          {usersQuery.isPending && <p className="text-slate-400 text-sm mt-4">Načítám uživatele...</p>}
          {usersQuery.isError && (
            <p className="text-rose-300 text-sm mt-4">Nepodařilo se načíst uživatele. Zkus obnovit stránku.</p>
          )}
          {!usersQuery.isPending && !users.length && (
            <p className="text-slate-400 text-sm mt-4">Nic nenalezeno.</p>
          )}
        </section>
      </div>

      {membershipUser && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4">
          <div className="glass-panel rounded-3xl p-6 w-full max-w-3xl space-y-6 max-h-[90vh] overflow-y-auto text-white border border-white/10">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h3 className="text-2xl font-semibold">{membershipUser.name}</h3>
                <p className="text-slate-400 text-sm">{membershipUser.email}</p>
              </div>
              <button
                onClick={() => setMembershipUser(null)}
                className="h-10 w-10 rounded-full border border-white/10 text-slate-300 hover:text-white hover:border-white/30 flex items-center justify-center transition"
                aria-label="Zavřít"
              >
                &times;
              </button>
            </div>

            <section className="space-y-4">
              <h4 className="text-lg font-semibold">Aktivní permanentky</h4>
              {membershipsQuery.isPending && <p className="text-slate-400 text-sm">Načítám permanentky...</p>}
              {!membershipsQuery.isPending && (membershipsQuery.data ?? []).length === 0 && (
                <p className="text-slate-500 text-sm">Žádné záznamy.</p>
              )}
              {(membershipsQuery.data ?? []).map((membership) => (
                <div key={membership.id} className="glass-subcard rounded-2xl p-5 space-y-3">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="font-semibold text-lg leading-tight">{membership.package_name ?? 'Manuální permanentka'}</p>
                      <p className="text-slate-400 text-sm">
                        Platnost {membership.valid_from ? new Date(membership.valid_from).toLocaleDateString('cs-CZ') : '?'} –{' '}
                        {membership.valid_to ? new Date(membership.valid_to).toLocaleDateString('cs-CZ') : '?'}
                      </p>
                    </div>
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-semibold ${
                        membership.status === 'active'
                          ? 'bg-emerald-500/20 text-emerald-200'
                          : membership.status === 'paused'
                          ? 'bg-amber-500/20 text-amber-200'
                          : 'bg-rose-500/20 text-rose-200'
                      }`}
                    >
                      {membership.status}
                    </span>
                  </div>

                  <div className="text-sm text-slate-300 flex flex-wrap gap-4">
                    {typeof membership.price_czk === 'number' && <span className="font-medium">{membership.price_czk} Kč</span>}
                    {membership.daily_limit ? <span>Limit {membership.daily_limit} vstup/den</span> : <span>Bez denního limitu</span>}
                    {membership.sessions_total ? (
                      <span>
                        {membership.sessions_used ?? 0}/{membership.sessions_total} návštěv
                      </span>
                    ) : null}
                  </div>

                  {membership.notes && (
                    <div className="text-xs text-slate-500 space-y-1">
                      <p className="uppercase tracking-[0.2em] text-slate-600 text-[10px]">Poznámky</p>
                      {formatNotes(membership.notes).map((item) => (
                        <p key={item.key} className="whitespace-pre-line">
                          {item.text}
                        </p>
                      ))}
                    </div>
                  )}

                  <div className="flex flex-wrap gap-3">
                    {membership.status !== 'active' && (
                      <button
                        className="secondary-button px-4 py-2"
                        onClick={() =>
                          membershipStatusMutation.mutate({
                            userId: membershipUser.id,
                            membershipId: membership.id,
                            status: 'active',
                          })
                        }
                      >
                        Aktivovat
                      </button>
                    )}
                    {membership.status === 'active' && (
                      <button
                        className="secondary-button px-4 py-2"
                        onClick={() =>
                          membershipStatusMutation.mutate({
                            userId: membershipUser.id,
                            membershipId: membership.id,
                            status: 'paused',
                          })
                        }
                      >
                        Pozastavit
                      </button>
                    )}
                    <button
                      className="secondary-button px-4 py-2 text-rose-200 border-rose-400/30 hover:text-rose-50 hover:border-rose-200/70"
                      onClick={() =>
                        membershipStatusMutation.mutate({
                          userId: membershipUser.id,
                          membershipId: membership.id,
                          status: 'cancelled',
                        })
                      }
                    >
                      Ukončit
                    </button>
                    {membership.sessions_total && (membership.sessions_used ?? 0) < membership.sessions_total && (
                      <div className="flex flex-col sm:flex-row gap-3 items-stretch flex-1 min-w-[260px]">
                        <input
                          className="input-field text-sm flex-1"
                          placeholder="Poznámka k tréninku (volitelné)"
                          value={sessionNotes[membership.id] ?? ''}
                          onChange={(event) =>
                            setSessionNotes((prev) => ({
                              ...prev,
                              [membership.id]: event.target.value,
                            }))
                          }
                        />
                        <button
                          className="accent-button px-4 py-2 sm:w-auto w-full"
                          onClick={() =>
                            consumeSessionMutation.mutate({
                              userId: membershipUser.id,
                              membershipId: membership.id,
                              note: sessionNotes[membership.id],
                            })
                          }
                          disabled={consumeSessionMutation.isPending}
                        >
                          {consumeSessionMutation.isPending ? 'Odečítám...' : 'Odečíst trénink'}
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </section>

            <section className="space-y-4">
              <h4 className="text-lg font-semibold">Přiřadit balíček</h4>
              <div className="glass-subcard rounded-2xl p-5 space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="text-sm text-slate-400 block mb-1">Balíček</label>
                    <select
                      className="input-field"
                      value={selectedPackageId}
                      onChange={(event) => setSelectedPackageId(event.target.value)}
                    >
                      <option value="">Vyber balíček</option>
                      {(packagesQuery.data ?? [])
                        .filter((pkg) => pkg.is_active)
                        .map((pkg) => (
                          <option key={pkg.id} value={pkg.id}>
                            {pkg.name} ({pkg.duration_days} dní)
                          </option>
                        ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-sm text-slate-400 block mb-1">Začátek platnosti</label>
                    <input type="date" className="input-field" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
                  </div>
                </div>
                <label className="flex items-center gap-2 text-sm text-slate-400">
                  <input type="checkbox" checked={autoRenew} onChange={(event) => setAutoRenew(event.target.checked)} className="h-4 w-4" />
                  Automaticky obnovit po skončení
                </label>
                <div className="flex flex-col sm:flex-row gap-3">
                  <button className="secondary-button w-full sm:w-auto" onClick={() => setMembershipUser(null)}>
                    Zavřít
                  </button>
                  <button
                    className="accent-button w-full sm:w-auto"
                    onClick={() =>
                      membershipUser &&
                      selectedPackageId &&
                      assignMembershipMutation.mutate({
                        userId: membershipUser.id,
                        packageId: Number(selectedPackageId),
                        startDate: startDate || undefined,
                        autoRenew,
                      })
                    }
                    disabled={!selectedPackageId || assignMembershipMutation.isPending}
                  >
                    {assignMembershipMutation.isPending ? 'Přiřazuji...' : 'Přiřadit permanentku'}
                  </button>
                </div>
              </div>
            </section>
          </div>
        </div>
      )}

      <Toast toast={toast} />
    </>
  );
}
