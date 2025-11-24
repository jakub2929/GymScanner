'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/apiClient';
import { Toast, useToast } from '@/components/toast';

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
    return new Date(date).toLocaleDateString('cs-CZ', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  } catch {
    return null;
  }
}

export default function PermanentkyPage() {
  const { toast, showToast } = useToast();
  const [selectedPackageId, setSelectedPackageId] = useState<number | null>(null);

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
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.35em] text-slate-500">Členství</p>
            <h1 className="text-3xl font-semibold text-white mt-1">Permanentky</h1>
            <p className="text-slate-400 text-sm mt-2">Aktivní předplatné a nabídka nových balíčků.</p>
          </div>
          <Link href="/treninky" className="secondary-button">
            Přepnout na tréninky
          </Link>
        </div>
        <section className="glass-panel rounded-3xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-white">Moje permanentky</h2>
            <p className="text-sm text-slate-400">{isPending ? '...' : `${membershipCards.length} položek`}</p>
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
            <div className="space-y-3">
              {membershipCards.map((card) => (
                <div key={card.membership_id} className="glass-subcard rounded-2xl p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-semibold text-lg text-white">{card.package_name ?? 'Permanentka'}</p>
                      <p className="text-xs uppercase tracking-[0.35em] text-slate-500">
                        {card.package_type ?? card.membership_type}
                      </p>
                    </div>
                    <span
                      className={`px-3 py-1 rounded-full text-xs ${
                        card.status === 'active' ? 'bg-emerald-500/20 text-emerald-200' : 'bg-white/10 text-slate-200'
                      }`}
                    >
                      {card.status}
                    </span>
                  </div>
                  <div className="text-sm text-slate-300 flex flex-wrap gap-4">
                    {card.valid_from && <p>Od {formatDate(card.valid_from) ?? card.valid_from}</p>}
                    {card.valid_to && <p>Do {formatDate(card.valid_to) ?? card.valid_to}</p>}
                    {card.daily_limit && <p>Limit {card.daily_limit} vstup/den</p>}
                  </div>
                  {card.message && <p className="text-xs text-slate-400">{card.message}</p>}
                </div>
              ))}
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
                  <div className="space-y-2">
                    <h3 className="text-xl font-semibold text-white">{pkg.name}</h3>
                    <p className="text-slate-400 text-sm">{pkg.description ?? 'Bez popisu'}</p>
                    <p className="text-white text-2xl font-semibold">{pkg.price_czk.toLocaleString('cs-CZ')} Kč</p>
                    <p className="text-slate-400 text-sm">Platnost {pkg.duration_days} dnů</p>
                    {pkg.daily_entry_limit && (
                      <p className="text-slate-400 text-sm">Denní limit: {pkg.daily_entry_limit} vstup/den</p>
                    )}
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
