'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/apiClient';
import type { AdminUser } from '@/types/admin';
import { useDebounce } from '@/hooks/useDebounce';
import { Toast, useToast } from '@/components/toast';

export default function AdminUsersPage() {
  const [search, setSearch] = useState('');
  const [selectedUser, setSelectedUser] = useState<AdminUser | null>(null);
  const [creditsChange, setCreditsChange] = useState(0);
  const [note, setNote] = useState('');
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

  const mutation = useMutation({
    mutationFn: async (payload: { userId: number; change: number; reason: string }) =>
      apiClient(`/api/admin/users/${payload.userId}/credits`, {
        method: 'POST',
        body: JSON.stringify({ credits: payload.change, note: payload.reason }),
      }),
    onSuccess: () => {
      showToast('Kredity byly upraveny');
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      setSelectedUser(null);
      setCreditsChange(0);
      setNote('');
    },
    onError: (error) => {
      showToast(error instanceof Error ? error.message : 'Nepodařilo se upravit kredity', 'error');
    },
  });

  function openModal(user: AdminUser) {
    setSelectedUser(user);
    setCreditsChange(0);
    setNote('');
  }

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
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-slate-400 text-left">
                  <th className="py-3">Jméno</th>
                  <th className="py-3">E-mail</th>
                  <th className="py-3">Kredity</th>
                  <th className="py-3">Role</th>
                  <th className="py-3">Registrován</th>
                  <th className="py-3 text-right">Akce</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {usersQuery.data?.map((user) => (
                  <tr key={user.id} className="text-slate-100">
                    <td className="py-4 font-medium">{user.name}</td>
                    <td className="py-4 text-slate-400">{user.email}</td>
                    <td className="py-4 font-semibold">{user.credits}</td>
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
                    <td className="py-4 text-right">
                      <button className="secondary-button" onClick={() => openModal(user)}>
                        Upravit kredity
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {usersQuery.isPending && <p className="text-slate-400 text-sm mt-4">Načítám uživatele...</p>}
            {usersQuery.isError && (
              <p className="text-rose-300 text-sm mt-4">
                Nepodařilo se načíst uživatele. Zkus obnovit stránku.
              </p>
            )}
            {!usersQuery.isPending && !usersQuery.data?.length && (
              <p className="text-slate-400 text-sm mt-4">Nic nenalezeno.</p>
            )}
          </div>
        </section>
      </div>

      {selectedUser && (
        <div className="fixed inset-0 bg-black/70 z-50 flex items-center justify-center p-4">
          <div className="bg-[#050912] text-white rounded-3xl border border-white/10 p-6 w-full max-w-lg space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-2xl font-semibold">Upravit kredity</h3>
                <p className="text-slate-400 text-sm">{selectedUser.name}</p>
              </div>
              <button onClick={() => setSelectedUser(null)} className="text-3xl text-slate-500 hover:text-white">
                &times;
              </button>
            </div>
            <div>
              <label className="text-sm text-slate-400">Změna kreditů</label>
              <input
                type="number"
                className="input-field mt-2"
                value={creditsChange}
                onChange={(event) => setCreditsChange(Number(event.target.value))}
              />
              <p className="text-xs text-slate-500 mt-2">
                Použij zápornou hodnotu pro odečet. Aktuálně má {selectedUser.credits} kreditů.
              </p>
            </div>
            <div>
              <label className="text-sm text-slate-400">Poznámka (volitelné)</label>
              <textarea
                className="input-field mt-2 min-h-[100px]"
                value={note}
                onChange={(event) => setNote(event.target.value)}
                placeholder="Důvod úpravy"
              />
            </div>
            <div className="flex gap-3">
              <button onClick={() => setSelectedUser(null)} className="secondary-button w-full" disabled={mutation.isPending}>
                Zrušit
              </button>
              <button
                onClick={() => mutation.mutate({ userId: selectedUser.id, change: creditsChange, reason: note })}
                className="accent-button w-full"
                disabled={mutation.isPending || creditsChange === 0}
              >
                {mutation.isPending ? 'Upravuji...' : 'Uložit změnu'}
              </button>
            </div>
          </div>
        </div>
      )}

      <Toast toast={toast} />
    </>
  );
}
