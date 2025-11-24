'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
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
  const [isRegenerating, setIsRegenerating] = useState(false);
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

  return (
    <>
      <div className="space-y-12">
        <section className="glass-panel rounded-3xl p-6 sm:p-10">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h1 className="text-3xl sm:text-[2.5rem] font-semibold tracking-tight text-white">
                Tvůj přístupový QR kód
              </h1>
              {summary && <p className="text-slate-300 mt-4 text-sm">{summary}</p>}
            </div>
          </div>

          {isPending ? (
            <p className="text-slate-400 mt-10">Načítám...</p>
          ) : (
            <div className="mt-10 flex flex-col items-center gap-6" id="qrContainer">
              <div className="inline-flex flex-col items-center gap-4 glass-subcard rounded-2xl p-6">
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
              <div className="w-full glass-subcard rounded-2xl p-5 text-left">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-6">
                  <div className="flex flex-col sm:flex-row gap-3">
                    <button onClick={download} className="accent-button w-full sm:w-auto" disabled={isPending}>
                      Stáhnout QR
                    </button>
                    <button
                      onClick={regenerate}
                      className="secondary-button w-full sm:w-auto"
                      disabled={isPending || isRegenerating}
                    >
                      {isRegenerating ? 'Generuji...' : 'Vygenerovat nový PIN'}
                    </button>
                  </div>
                  <div className="text-right sm:min-w-[200px]">
                    <p className="text-xs uppercase tracking-[0.35em] text-slate-400">Tvůj PIN</p>
                    <p className="text-4xl font-semibold text-white tracking-[0.35em]">
                      {data?.token ?? '---'}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </section>
        <section className="glass-panel rounded-3xl p-6 space-y-4">
          <h2 className="text-2xl font-semibold text-white">Další akce</h2>
          <p className="text-slate-400 text-sm">Spravuj své permanentky a osobní tréninky na samostatných stránkách.</p>
          <div className="flex flex-col sm:flex-row gap-3">
            <Link href="/permanentky" className="accent-button text-center">
              Přehled permanentek
            </Link>
            <Link href="/treninky" className="secondary-button text-center">
              Přehled tréninků
            </Link>
          </div>
        </section>
      </div>

      <Toast toast={toast} />
    </>
  );
}
