'use client';

import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/apiClient';
import { Toast, useToast } from '@/components/toast';
import { DATE_LOCALE, DATE_TIMEZONE } from '@/lib/datetime';

interface MembershipDetail {
  membership_id: number;
  package_name?: string | null;
  package_type?: string | null;
  membership_type?: string | null;
  status?: string | null;
  valid_from?: string | null;
  valid_to?: string | null;
  sessions_total?: number | null;
  sessions_used?: number | null;
  message?: string | null;
}

interface MembershipPackageSummary {
  id: number;
  name: string;
  slug: string;
  description?: string | null;
  price_czk: number;
  duration_days: number;
  session_limit?: number | null;
  package_type: string;
}

interface PurchaseResponse {
  payment_id: string;
  redirect_url: string;
  price_czk: number;
  status: string;
}

interface QrResponse {
  memberships: MembershipDetail[];
  packages: MembershipPackageSummary[];
}

const MS_PER_DAY = 1000 * 60 * 60 * 24;

function formatShortDate(value?: string | null) {
  if (!value) return '---';
  try {
    return new Date(value).toLocaleDateString(DATE_LOCALE, {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      timeZone: DATE_TIMEZONE,
    });
  } catch {
    return value ?? '---';
  }
}

function buildTimelineInfo(validFrom?: string | null, validTo?: string | null, nowTs?: number | null) {
  if (!validFrom || !validTo || typeof nowTs !== 'number') return null;
  const start = new Date(validFrom).getTime();
  const end = new Date(validTo).getTime();
  if (Number.isNaN(start) || Number.isNaN(end) || end <= start) return null;
  const progress = Math.min(100, Math.max(0, ((nowTs - start) / (end - start)) * 100));
  const remainingDays = Math.max(0, Math.ceil((end - nowTs) / MS_PER_DAY));
  return {
    progress,
    remainingDays,
    startLabel: formatShortDate(validFrom),
    endLabel: formatShortDate(validTo),
  };
}

export default function TreninkyPage() {
  const { toast, showToast } = useToast();
  const [selectedPackageId, setSelectedPackageId] = useState<number | null>(null);
  const [nowTs, setNowTs] = useState<number | null>(null);

  useEffect(() => {
    setNowTs(Date.now());
  }, []);

  const { data, isPending } = useQuery<QrResponse>({
    queryKey: ['my-qr', 'treninky'],
    queryFn: () => apiClient<QrResponse>('/api/my_qr'),
  });

  const trainingCards =
    data?.memberships.filter(
      (card) => (card.package_type ?? card.membership_type) === 'personal_training' || (card.sessions_total ?? 0) > 0
    ) ?? [];
  const availablePackages =
    data?.packages.filter((pkg) => pkg.package_type === 'personal_training' || (pkg.session_limit ?? 0) > 0) ?? [];

  async function buyTrainingPackage(pkg: MembershipPackageSummary) {
    try {
      setSelectedPackageId(pkg.id);
      const response = await apiClient<PurchaseResponse>('/api/payments/create', {
        method: 'POST',
        body: JSON.stringify({ package_id: pkg.id }),
      });
      if (response.redirect_url) {
        showToast('Přesměrovávám na Comgate…');
        window.location.href = response.redirect_url;
      } else {
        showToast('Brána nevrátila platnou redirect URL', 'error');
      }
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Chyba při nákupu', 'error');
    } finally {
      setSelectedPackageId(null);
    }
  }

  return (
    <>
      <div className="space-y-10">
        <div>
          <p className="text-xs uppercase tracking-[0.35em] text-slate-500">Služby</p>
          <h1 className="text-3xl font-semibold text-white mt-1">Osobní tréninky</h1>
          <p className="text-slate-400 text-sm mt-2">
            Přehled zakoupených tréninkových balíčků a rychlá možnost dokoupit další.
          </p>
        </div>
        <section className="glass-panel rounded-3xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-white">Moje tréninky</h2>
              <p className="text-slate-400 text-sm">Vizualizace čerpání i platnosti každého balíčku.</p>
            </div>
            <p className="text-sm text-slate-400">{isPending ? '...' : `${trainingCards.length} aktivních`}</p>
          </div>
          {isPending ? (
            <p className="text-slate-400 text-sm">Načítám...</p>
          ) : trainingCards.length === 0 ? (
            <div className="space-y-3">
              <p className="text-slate-400 text-sm">Zatím nemáš žádný balíček tréninků.</p>
              <a href="#packages" className="accent-button w-full sm:w-auto">
                Koupit tréninky
              </a>
            </div>
          ) : (
            <div className="space-y-4">
              {trainingCards.map((card) => {
                const totalSessions = card.sessions_total ?? 0;
                const usedSessions = card.sessions_used ?? 0;
                const remaining = totalSessions ? Math.max(0, totalSessions - usedSessions) : null;
                const sessionsProgress =
                  totalSessions > 0 ? Math.min(100, Math.max(0, (usedSessions / totalSessions) * 100)) : usedSessions ? 100 : 0;
                const timeline = buildTimelineInfo(card.valid_from, card.valid_to, nowTs);

                return (
                  <div key={card.membership_id} className="glass-subcard rounded-2xl p-5 space-y-4">
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div>
                        <p className="font-semibold text-lg text-white">{card.package_name ?? 'Balíček tréninků'}</p>
                        <p className="text-xs uppercase tracking-[0.35em] text-slate-500">
                          {card.package_type ?? card.membership_type}
                        </p>
                      </div>
                      <div className="text-right">
                        <span
                          className={`px-3 py-1 rounded-full text-xs ${
                            card.status === 'active' ? 'bg-emerald-500/20 text-emerald-200' : 'bg-white/10 text-slate-200'
                          }`}
                        >
                          {card.status}
                        </span>
                        {remaining !== null && (
                          <p className="text-xs text-slate-400 mt-1">Zbývá {remaining} / {totalSessions} tréninků</p>
                        )}
                      </div>
                    </div>

                    {timeline && (
                      <div className="space-y-1">
                        <div className="flex items-center justify-between text-xs text-slate-500">
                          <span>{timeline.startLabel}</span>
                          <span>{timeline.remainingDays} dnů zbývá</span>
                        </div>
                        <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-gradient-to-r from-emerald-400 to-cyan-500"
                            style={{ width: `${timeline.progress}%` }}
                          />
                        </div>
                        <div className="flex items-center justify-between text-xs text-slate-500">
                          <span>Začátek</span>
                          <span>{timeline.endLabel}</span>
                        </div>
                      </div>
                    )}

                    <div className="space-y-1">
                      <div className="flex items-center justify-between text-xs text-slate-500">
                        <span>
                          Čerpáno {usedSessions}
                          {totalSessions ? ` / ${totalSessions}` : ''} tréninků
                        </span>
                        <span>{remaining !== null ? `Zbývá ${remaining}` : 'Bez limitu'}</span>
                      </div>
                      <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                        <div className="h-full bg-emerald-400" style={{ width: `${sessionsProgress}%` }} />
                      </div>
                    </div>

                    {card.message && <p className="text-xs text-slate-400">{card.message}</p>}
                  </div>
                );
              })}
            </div>
          )}
        </section>

        <section id="packages" className="glass-panel rounded-3xl p-6 space-y-6">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <h2 className="text-2xl font-semibold text-white">Dostupné balíčky tréninků</h2>
              <p className="text-slate-400 text-sm mt-1">Vyber si počet tréninků.</p>
            </div>
            <div className="text-right">
              <p className="text-xs uppercase tracking-[0.35em] text-slate-500">Dostupných</p>
              <p className="text-3xl font-semibold text-white">{availablePackages.length}</p>
            </div>
          </div>
          {availablePackages.length === 0 ? (
            <p className="text-slate-300 text-sm">Momentálně nejsou k dispozici žádné balíčky.</p>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {availablePackages.map((pkg) => (
                <div key={pkg.id} className="glass-subcard rounded-2xl p-5 flex flex-col justify-between space-y-4">
                  <div className="space-y-3">
                    <div className="flex flex-col gap-2">
                      <h3 className="text-xl font-semibold text-white">{pkg.name}</h3>
                      <p className="text-slate-400 text-sm">{pkg.description ?? 'Bez popisu'}</p>
                    </div>
                    <div className="text-white text-2xl font-semibold">
                      {pkg.price_czk.toLocaleString('cs-CZ')} Kč
                    </div>
                    <div className="flex flex-wrap gap-2 text-xs text-slate-400">
                      <span className="px-3 py-1 rounded-full bg-white/5">
                        Platnost {pkg.duration_days} dnů
                      </span>
                      <span className="px-3 py-1 rounded-full bg-white/5">
                        {pkg.session_limit ?? 0} tréninků
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={() => buyTrainingPackage(pkg)}
                    className="accent-button w-full"
                    disabled={selectedPackageId === pkg.id}
                  >
                    {selectedPackageId === pkg.id ? 'Otevírám bránu...' : 'Zakoupit'}
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
      <Toast toast={toast} />
    </>
  );
}
