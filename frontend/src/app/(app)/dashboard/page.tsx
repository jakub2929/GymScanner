'use client';

import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/apiClient';
import { Toast, useToast } from '@/components/toast';
import Image from 'next/image';

interface QrResponse {
  token: string;
  qr_code_url: string;
  credits: number;
}

export default function DashboardPage() {
  const { toast, showToast } = useToast();
  const [buyModal, setBuyModal] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [selectedPackage, setSelectedPackage] = useState<{ credits: number; amount: number } | null>(null);
  const [summary, setSummary] = useState('');

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const email = sessionStorage.getItem('user_email');
    const name = sessionStorage.getItem('user_name');
    if (name || email) {
      setSummary([name, email].filter(Boolean).join(' • '));
    }
  }, []);

  const { data, isPending, refetch } = useQuery<QrResponse>({
    queryKey: ['my-qr'],
    queryFn: () => apiClient<QrResponse>('/api/my_qr'),
  });

  async function regenerate() {
    try {
      setIsRegenerating(true);
      await apiClient('/api/regenerate_qr', { method: 'POST' });
      await refetch();
      showToast('Vygenerován nový QR kód');
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Chyba při regeneraci', 'error');
    } finally {
      setIsRegenerating(false);
    }
  }

  async function download() {
    if (!data?.qr_code_url) {
      showToast('QR kód není k dispozici', 'error');
      return;
    }
    const link = document.createElement('a');
    link.href = data.qr_code_url;
    link.download = 'gym-access-qr.png';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast('QR kód stažen');
  }

  const packages = [
    { credits: 1, amount: 100 },
    { credits: 5, amount: 500 },
    { credits: 10, amount: 1000 },
  ];

  async function buyEntries(credits: number, amount: number) {
    try {
      setSelectedPackage({ credits, amount });
      setBuyModal(false);
      await apiClient('/api/buy_credits', {
        method: 'POST',
        body: JSON.stringify({ credits, amount }),
      });
      await refetch();
      showToast('Vstupy připsány');
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Chyba při nákupu', 'error');
    } finally {
      setSelectedPackage(null);
    }
  }

  return (
    <>
      <div className="space-y-12">
        <section className="surface-card p-6 sm:p-10">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.35em] text-slate-400">Gym Access</p>
              <h1 className="text-3xl sm:text-[2.5rem] font-semibold tracking-tight text-slate-900">
                Tvůj přístupový QR kód
              </h1>
              {summary && <p className="text-slate-500 mt-4 text-sm">{summary}</p>}
            </div>
          </div>

          {isPending ? (
            <p className="text-slate-400 mt-10">Načítám...</p>
          ) : (
            <div className="mt-10 flex flex-col items-center gap-6" id="qrContainer">
              <div className="inline-flex flex-col items-center gap-4 surface-subcard p-6">
                {data?.qr_code_url ? (
                  <Image
                    src={data.qr_code_url}
                    alt="QR Code"
                    width={320}
                    height={320}
                    unoptimized
                    className="w-full max-w-[320px] h-auto"
                  />
                ) : (
                  <p className="text-slate-400">Kód není dostupný.</p>
                )}
              </div>
              <div className="w-full surface-subcard p-5 text-left">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.35em] text-slate-400">Token</p>
                    <p className="text-sm font-mono break-all text-slate-800">{data?.token ?? '---'}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs uppercase tracking-[0.35em] text-slate-400">Kredity</p>
                    <p className="text-3xl font-semibold text-slate-900">{data?.credits ?? 0}</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          <div className="flex flex-col sm:flex-row gap-4 mt-8">
            <button onClick={download} className="accent-button" disabled={isPending}>
              Stáhnout QR
            </button>
            <button onClick={regenerate} className="secondary-button" disabled={isPending || isRegenerating}>
              {isRegenerating ? 'Generuji...' : 'Vygenerovat nový QR'}
            </button>
          </div>
        </section>

        <div className="grid lg:grid-cols-2 gap-6">
          <section className="surface-card p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-semibold text-slate-900">Koupit vstupy</h2>
              <span className="text-sm text-slate-500">Dostupné: {data?.credits ?? 0}</span>
            </div>
            <button onClick={() => setBuyModal(true)} className="accent-button">
              Vybrat balíček
            </button>
          </section>

          <section className="surface-card p-6 space-y-4 text-sm text-slate-600">
            <h2 className="text-2xl font-semibold text-slate-900">Rychlé akce</h2>
            <p>Vygeneruj nový QR při ztrátě nebo podezření na zneužití.</p>
            <p>Pokud se skenování nedaří, využij podporu nebo ruční ověření u obsluhy.</p>
            <p>Kontaktuj podporu v Nastavení.</p>
          </section>
        </div>
      </div>

      {buyModal && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
          <div className="surface-card text-slate-900 p-6 w-full max-w-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-2xl font-semibold text-slate-900">Vyber balíček</h3>
              <button onClick={() => setBuyModal(false)} className="text-3xl text-slate-400 hover:text-slate-900">
                &times;
              </button>
            </div>
            {packages.map((pkg) => (
              <div key={pkg.credits} className="surface-subcard p-5 flex items-center justify-between">
                <div>
                  <h4 className="text-xl font-semibold">{pkg.credits} vstup{pkg.credits > 1 ? 'ů' : ''}</h4>
                  <p className="text-slate-500">{pkg.amount} Kč</p>
                </div>
                <button onClick={() => buyEntries(pkg.credits, pkg.amount)} className="accent-button w-auto">
                  {selectedPackage?.credits === pkg.credits ? 'Zpracovávám...' : 'Koupit'}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <Toast toast={toast} />
    </>
  );
}
