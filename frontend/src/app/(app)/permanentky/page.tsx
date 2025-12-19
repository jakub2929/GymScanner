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
  daily_limit?: number | null;
  daily_usage_count?: number | null;
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
  daily_entry_limit?: number | null;
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

function formatDate(date?: string | null) {
  if (!date) return null;
  try {
    return new Date(date).toLocaleDateString(DATE_LOCALE, {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      timeZone: DATE_TIMEZONE,
    });
  } catch {
    return null;
  }
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

function buildDailyUsage(dailyLimit?: number | null, used?: number | null) {
  if (!dailyLimit) return null;
  const safeLimit = Math.max(dailyLimit, 0);
  const safeUsed = Math.max(0, Math.min(used ?? 0, safeLimit));
  const percent = safeLimit > 0 ? Math.min(100, (safeUsed / safeLimit) * 100) : 0;
  return {
    limit: safeLimit,
    used: safeUsed,
    remaining: Math.max(0, safeLimit - safeUsed),
    percent,
  };
}

export default function PermanentkyPage() {
  const { toast, showToast } = useToast();
  const [selectedPackageId, setSelectedPackageId] = useState<number | null>(null);
  const [nowTs, setNowTs] = useState<number | null>(null);

  useEffect(() => {
    setNowTs(Date.now());
  }, []);

  const { data, isPending } = useQuery<QrResponse>({
    queryKey: ['my-qr', 'permanentky'],
    queryFn: () => apiClient<QrResponse>('/api/my_qr'),
  });

  const membershipCards =
    data?.memberships.filter(
      (card) => (card.package_type ?? card.membership_type) === 'membership' || !card.sessions_total
    ) ?? [];
  const availablePackages =
    data?.packages.filter((pkg) => pkg.package_type === 'membership' || !pkg.session_limit) ?? [];

  async function buyMembershipPackage(pkg: MembershipPackageSummary) {
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
          <p className="text-xs uppercase tracking-[0.35em] text-slate-500">Členství</p>
          <h1 className="text-3xl font-semibold text-white mt-1">Permanentky</h1>
          <p className="text-slate-400 text-sm mt-2">
            Jasný přehled platnosti a denních limitů s nabídkou nových balíčků.
          </p>
        </div>
        <section className="glass-panel rounded-3xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-semibold text-white">Moje permanentky</h2>
              <p className="text-slate-400 text-sm">Zde vidíš platnost, denní limity i stav každé permice.</p>
            </div>
            <p className="text-sm text-slate-400">{isPending ? '...' : `${membershipCards.length} aktivních`}</p>
          </div>
          {isPending ? (
            <p className="text-slate-400 text-sm">Načítám...</p>
          ) : membershipCards.length === 0 ? (
            <div className="space-y-3">
              <p className="text-slate-400 text-sm">Zatím nemáš žádnou aktivní permanentku.</p>
              <a href="#packages" className="accent-button w-full sm:w-auto">
                Vybrat permanentku
              </a>
            </div>
          ) : (
            <div className="space-y-4">
              {membershipCards.map((card) => {
                const timeline = buildTimelineInfo(card.valid_from, card.valid_to, nowTs);
                const daily = buildDailyUsage(card.daily_limit, card.daily_usage_count);
                return (
                  <div key={card.membership_id} className="glass-subcard rounded-2xl p-5 space-y-4">
                    <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                      <div>
                        <p className="font-semibold text-lg text-white">{card.package_name ?? 'Permanentka'}</p>
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
                        {card.valid_to && (
                          <p className="text-xs text-slate-400 mt-1">Platnost do {formatDate(card.valid_to) ?? card.valid_to}</p>
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
                            className="h-full bg-gradient-to-r from-amber-400 via-rose-400 to-pink-500"
                            style={{ width: `${timeline.progress}%` }}
                          />
                        </div>
                        <div className="flex items-center justify-between text-xs text-slate-500">
                          <span>Začátek</span>
                          <span>{timeline.endLabel}</span>
                        </div>
                      </div>
                    )}

                    {daily && (
                      <div className="space-y-1">
                        <div className="flex items-center justify-between text-xs text-slate-500">
                          <span>Dnes {daily.used}/{daily.limit} vstupů</span>
                          <span>Zbývá {daily.remaining}</span>
                        </div>
                        <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                          <div className="h-full bg-rose-400" style={{ width: `${daily.percent}%` }} />
                        </div>
                      </div>
                    )}

                    <div className="text-sm text-slate-300 flex flex-wrap gap-4">
                      {card.valid_from && <p>Od {formatDate(card.valid_from) ?? card.valid_from}</p>}
                      {card.valid_to && <p>Do {formatDate(card.valid_to) ?? card.valid_to}</p>}
                      {card.daily_limit && <p>Denní limit {card.daily_limit} vstupů</p>}
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
              <h2 className="text-2xl font-semibold text-white">Dostupné balíčky</h2>
              <p className="text-slate-400 text-sm mt-1">Vyber si délku, která ti sedí.</p>
            </div>
            <div className="text-right">
              <p className="text-xs uppercase tracking-[0.35em] text-slate-500">Dostupných</p>
              <p className="text-3xl font-semibold text-white">{availablePackages.length}</p>
            </div>
          </div>
          {availablePackages.length === 0 ? (
            <p className="text-slate-300 text-sm">Momentálně nejsou k dispozici žádné permanentky.</p>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {availablePackages.map((pkg) => (
                <div key={pkg.id} className="glass-subcard rounded-2xl p-5 flex flex-col justify-between space-y-4">
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="text-xl font-semibold text-white">{pkg.name}</h3>
                        <p className="text-slate-400 text-sm">{pkg.description ?? 'Bez popisu'}</p>
                      </div>
                      <p className="text-white text-2xl font-semibold">{pkg.price_czk.toLocaleString('cs-CZ')} Kč</p>
                    </div>
                    <div className="flex flex-wrap gap-2 text-xs text-slate-400">
                      <span className="px-3 py-1 rounded-full bg-white/5">
                        Platnost {pkg.duration_days} dnů
                      </span>
                      {pkg.daily_entry_limit && (
                        <span className="px-3 py-1 rounded-full bg-white/5">
                          Denní limit {pkg.daily_entry_limit} vstupů
                        </span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => buyMembershipPackage(pkg)}
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
