'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/apiClient';
import type { AdminMembershipPackage } from '@/types/admin';
import { Toast, useToast } from '@/components/toast';

type FormMode = 'create' | 'edit';

interface PackageFormState {
  name: string;
  slug: string;
  price_czk: number;
  duration_days: number;
  package_type: string;
  daily_entry_limit: string;
  session_limit: string;
  description: string;
}

const emptyForm: PackageFormState = {
  name: '',
  slug: '',
  price_czk: 1500,
  duration_days: 30,
  package_type: 'membership',
  daily_entry_limit: '1',
  session_limit: '',
  description: '',
};

function formatCurrency(value: number) {
  return new Intl.NumberFormat('cs-CZ', { style: 'currency', currency: 'CZK', maximumFractionDigits: 0 }).format(value);
}

export default function AdminPackagesPage() {
  const queryClient = useQueryClient();
  const { toast, showToast } = useToast();
  const [formMode, setFormMode] = useState<FormMode>('create');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [formState, setFormState] = useState<PackageFormState>(emptyForm);

  const packagesQuery = useQuery<AdminMembershipPackage[]>({
    queryKey: ['admin-packages'],
    queryFn: () => apiClient('/api/admin/membership-packages?include_inactive=true'),
  });

  const packages = packagesQuery.data ?? [];

  const createMutation = useMutation({
    mutationFn: (payload: PackageFormState) =>
      apiClient<AdminMembershipPackage>('/api/admin/membership-packages', {
        method: 'POST',
        body: JSON.stringify({
          name: payload.name,
          slug: payload.slug,
          price_czk: payload.price_czk,
          duration_days: payload.duration_days,
          package_type: payload.package_type,
          daily_entry_limit: payload.daily_entry_limit ? Number(payload.daily_entry_limit) : null,
          session_limit: payload.session_limit ? Number(payload.session_limit) : null,
          description: payload.description || null,
        }),
      }),
    onSuccess: () => {
      showToast('Balíček vytvořen');
      queryClient.invalidateQueries({ queryKey: ['admin-packages'] });
      resetForm();
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Chyba při vytvoření balíčku', 'error'),
  });

  const updateMutation = useMutation({
    mutationFn: (payload: PackageFormState & { id: number }) =>
      apiClient<AdminMembershipPackage>(`/api/admin/membership-packages/${payload.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          name: payload.name,
          slug: payload.slug,
          price_czk: payload.price_czk,
          duration_days: payload.duration_days,
          package_type: payload.package_type,
          daily_entry_limit: payload.daily_entry_limit ? Number(payload.daily_entry_limit) : null,
          session_limit: payload.session_limit ? Number(payload.session_limit) : null,
          description: payload.description || null,
        }),
      }),
    onSuccess: () => {
      showToast('Balíček upraven');
      queryClient.invalidateQueries({ queryKey: ['admin-packages'] });
      resetForm();
    },
    onError: (error) => showToast(error instanceof Error ? error.message : 'Chyba při úpravě balíčku', 'error'),
  });

  const toggleMutation = useMutation({
    mutationFn: (payload: { id: number; next: boolean }) =>
      apiClient(`/api/admin/membership-packages/${payload.id}/toggle`, {
        method: 'POST',
        body: JSON.stringify({ is_active: payload.next }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-packages'] }),
    onError: (error) => showToast(error instanceof Error ? error.message : 'Nepodařilo se změnit stav', 'error'),
  });

  function resetForm() {
    setFormMode('create');
    setEditingId(null);
    setFormState(emptyForm);
  }

  function slugify(value: string) {
    return (
      value
        .toLowerCase()
        .trim()
        .replace(/[^a-z0-9_-]+/g, '-')
        .replace(/^-+|-+$/g, '') || 'balicek'
    );
  }

function editPackage(pkg: AdminMembershipPackage) {
    setFormMode('edit');
    setEditingId(pkg.id);
    setFormState({
      name: pkg.name,
      slug: pkg.slug,
      price_czk: pkg.price_czk,
      duration_days: pkg.duration_days,
      package_type: pkg.package_type,
      daily_entry_limit: pkg.daily_entry_limit?.toString() ?? '',
      session_limit: pkg.session_limit?.toString() ?? '',
      description: pkg.description ?? '',
    });
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!formState.name.trim() || !formState.slug.trim()) {
      showToast('Název i slug jsou povinné', 'error');
      return;
    }
    if (formMode === 'create') {
      createMutation.mutate(formState);
    } else if (editingId) {
      updateMutation.mutate({ ...formState, id: editingId });
    }
  }

  const activePackages = useMemo(() => packages.filter((pkg) => pkg.is_active), [packages]);

  return (
    <>
      <div className="space-y-6">
        <section className="glass-panel rounded-3xl p-6">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div className="space-y-2">
              <h1 className="text-3xl font-semibold">Balíčky & permanentky</h1>
              <p className="text-slate-400 text-sm">
                Definuj měsíční permanentky, osobní tréninky nebo custom balíčky.
              </p>
            </div>
            <div className="text-right shrink-0">
              <p className="text-4xl font-semibold leading-tight">{activePackages.length}</p>
              <p className="text-slate-400 text-sm">Aktivních balíčků</p>
            </div>
          </div>
        </section>

        <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <section className="glass-panel rounded-3xl p-6 space-y-4">
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <div>
                <p className="text-xs uppercase tracking-[0.35em] text-slate-500">
                  {formMode === 'create' ? 'Nový balíček' : 'Upravit balíček'}
                </p>
                <h2 className="text-2xl font-semibold mt-1">
                  {formMode === 'create' ? 'Přidej balíček' : 'Úprava balíčku'}
                </h2>
              </div>
              {formMode === 'edit' && (
                <button className="text-sm text-slate-400 hover:text-white" onClick={resetForm}>
                  Zrušit úpravy
                </button>
              )}
            </div>
            <form className="space-y-4" onSubmit={handleSubmit}>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="text-sm text-slate-400 block mb-1">Název</label>
                  <input
                    className="input-field"
                    value={formState.name}
                    onChange={(event) =>
                      setFormState((prev) => ({
                        ...prev,
                        name: event.target.value,
                        slug:
                          formMode === 'create' || !prev.slug
                            ? slugify(event.target.value)
                            : prev.slug,
                      }))
                    }
                    required
                  />
                </div>
                <div>
                  <label className="text-sm text-slate-400 block mb-1">Identifikátor</label>
                  <input className="input-field" value={formState.slug} readOnly />
                </div>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="text-sm text-slate-400 block mb-1">Cena (Kč)</label>
                  <input
                    type="number"
                    className="input-field"
                    value={formState.price_czk}
                    onChange={(event) => setFormState((prev) => ({ ...prev, price_czk: Number(event.target.value) }))}
                    min={0}
                  />
                </div>
                <div>
                  <label className="text-sm text-slate-400 block mb-1">Délka (dní)</label>
                  <input
                    type="number"
                    className="input-field"
                    value={formState.duration_days}
                    onChange={(event) => setFormState((prev) => ({ ...prev, duration_days: Number(event.target.value) }))}
                    min={1}
                  />
                </div>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="text-sm text-slate-400 block mb-1">Denní limit vstupů</label>
                  <input
                    type="number"
                    className="input-field"
                    value={formState.daily_entry_limit}
                    onChange={(event) => setFormState((prev) => ({ ...prev, daily_entry_limit: event.target.value }))}
                    min={1}
                    placeholder="např. 1"
                  />
                </div>
                <div>
                  <label className="text-sm text-slate-400 block mb-1">Limit návštěv (osobní trénink)</label>
                  <input
                    type="number"
                    className="input-field"
                    value={formState.session_limit}
                    onChange={(event) => setFormState((prev) => ({ ...prev, session_limit: event.target.value }))}
                    min={1}
                    placeholder="nech prázdné"
                  />
                </div>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="text-sm text-slate-400 block mb-1">Typ balíčku</label>
                  <select
                    className="input-field"
                    value={formState.package_type}
                    onChange={(event) => setFormState((prev) => ({ ...prev, package_type: event.target.value }))}
                  >
                    <option value="membership">Permanentka</option>
                    <option value="personal_training">Osobní trénink</option>
                    <option value="custom">Vlastní</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm text-slate-400 block mb-1">Popis</label>
                  <textarea
                    className="input-field min-h-[80px]"
                    value={formState.description}
                    onChange={(event) => setFormState((prev) => ({ ...prev, description: event.target.value }))}
                    placeholder="Krátký text pro adminy / prodej"
                  />
                </div>
              </div>
              <button
                type="submit"
                className="accent-button w-full sm:w-auto"
                disabled={createMutation.isPending || updateMutation.isPending}
              >
                {formMode === 'create' ? (createMutation.isPending ? 'Vytvářím...' : 'Přidat balíček') : updateMutation.isPending ? 'Ukládám...' : 'Uložit změny'}
              </button>
            </form>
          </section>

          <section className="glass-panel rounded-3xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-semibold">Existující balíčky</h2>
              {packagesQuery.isFetching && <p className="text-sm text-slate-400">Načítám...</p>}
            </div>
            <div className="space-y-3">
              {packages.map((pkg) => (
                <div key={pkg.id} className="glass-subcard rounded-2xl p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-semibold text-lg">{pkg.name}</p>
                    </div>
                    <span
                      className={`px-3 py-1 rounded-full text-xs ${
                        pkg.is_active ? 'bg-emerald-500/20 text-emerald-200' : 'bg-white/5 text-slate-300'
                      }`}
                    >
                      {pkg.is_active ? 'Aktivní' : 'Skryto'}
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-4 text-sm text-slate-400">
                    <p>{formatCurrency(pkg.price_czk)}</p>
                    <p>{pkg.duration_days} dní</p>
                    {pkg.daily_entry_limit ? <p>Limit {pkg.daily_entry_limit} vstup/den</p> : <p>Bez denního limitu</p>}
                    {pkg.session_limit ? <p>{pkg.session_limit} návštěv</p> : null}
                    <p className="uppercase tracking-[0.2em] text-xs">{pkg.package_type}</p>
                  </div>
                  {pkg.description && <p className="text-slate-400 text-sm">{pkg.description}</p>}
                  <div className="flex gap-3 flex-wrap">
                    <button className="secondary-button" onClick={() => editPackage(pkg)}>
                      Upravit
                    </button>
                    <button
                      className={pkg.is_active ? 'text-sm text-rose-300 hover:text-rose-100' : 'text-sm text-emerald-300 hover:text-emerald-100'}
                      onClick={() => toggleMutation.mutate({ id: pkg.id, next: !pkg.is_active })}
                      disabled={toggleMutation.isPending && (toggleMutation.variables?.id === pkg.id)}
                    >
                      {pkg.is_active ? 'Deaktivovat' : 'Aktivovat'}
                    </button>
                  </div>
                </div>
              ))}
              {!packages.length && !packagesQuery.isFetching && (
                <p className="text-slate-500 text-sm">Zatím žádné balíčky. Přidej první pomocí formuláře vlevo.</p>
              )}
            </div>
          </section>
        </div>
      </div>
      <Toast toast={toast} />
    </>
  );
}
