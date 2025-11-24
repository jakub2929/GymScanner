'use client';

import QrScanner from '@/components/qr-scanner';
import { Toast, useToast } from '@/components/toast';
import { apiClient } from '@/lib/apiClient';
import { useState } from 'react';

interface MembershipInfo {
  has_membership: boolean;
  package_name?: string | null;
  package_type?: string | null;
  status?: string | null;
  valid_from?: string | null;
  valid_to?: string | null;
  reason?: string | null;
  message?: string | null;
}

interface VerifyResponse {
  allowed: boolean;
  reason: string;
  credits_left?: number | null;
  cooldown_seconds_left?: number | null;
  user_name?: string | null;
  user_email?: string | null;
  message?: string | null;
  membership?: MembershipInfo | null;
}

type ShowToast = (message: string, type?: 'success' | 'error') => void;

function ScannerConsole({ showToast }: { showToast: ShowToast }) {
  const [manualToken, setManualToken] = useState('');
  const [status, setStatus] = useState<string>('Připraveno ke skenování');
  const [statusType, setStatusType] = useState<'success' | 'error' | 'info'>('info');
  const [lastResult, setLastResult] = useState<VerifyResponse | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleVerify(token: string) {
    const clean = (token || '').trim();
    if (!clean) {
      showToast('Prázdný token', 'error');
      return;
    }
    setIsSubmitting(true);
    try {
      const response = await apiClient<VerifyResponse>('/api/verify', {
        method: 'POST',
        body: JSON.stringify({ token: clean }),
      });
      setLastResult(response);
      const fallback = response.allowed ? 'Přístup povolen' : messageFromReason(response.reason);
      setStatus(response.message || response.membership?.message || fallback);
      setStatusType(response.allowed ? 'success' : response.reason === 'cooldown' ? 'info' : 'error');
      showToast(response.allowed ? 'QR ověřen' : 'Přístup zamítnut', response.allowed ? 'success' : 'error');
    } catch (error) {
      const detail = error instanceof Error ? error.message : 'Neznámá chyba';
      setStatus(detail);
      setStatusType('error');
      showToast(detail, 'error');
    } finally {
      setIsSubmitting(false);
    }
  }

  function messageFromReason(reason: string) {
    switch (reason) {
      case 'membership_required':
        return 'Je potřeba aktivní permanentka.';
      case 'membership_expired':
        return 'Permanentka vypršela.';
      case 'membership_inactive':
        return 'Permanentka je neaktivní.';
      case 'daily_limit':
        return 'Denní limit byl vyčerpán.';
      case 'sessions_limit_reached':
        return 'Vyčerpány všechny osobní tréninky.';
      case 'cooldown':
        return 'Zkus to znovu za chvíli';
      case 'invalid_token':
      case 'token_not_found':
        return 'Token není platný';
      default:
        return 'Přístup zamítnut';
    }
  }

  return (
    <section className="glass-panel rounded-3xl p-6 sm:p-10 space-y-6">
      <div>
        <h2 className="text-3xl sm:text-4xl font-semibold">Scanner</h2>
        <p className="text-slate-400 mt-2 text-sm">Skenuj QR kódy nebo vlož token ručně.</p>
      </div>
      <div className="glass-subcard rounded-2xl p-4 text-sm">
        <p className={statusType === 'success' ? 'text-emerald-300' : statusType === 'error' ? 'text-rose-300' : 'text-slate-200'}>
          {status}
        </p>
        {lastResult?.cooldown_seconds_left && lastResult.cooldown_seconds_left > 0 && (
          <p className="text-slate-400 text-xs mt-2">Cooldown: {lastResult.cooldown_seconds_left}s</p>
        )}
      </div>
      <div className="grid lg:grid-cols-2 gap-6">
        <div className="glass-subcard rounded-2xl p-4">
          <QrScanner onDecode={(text) => handleVerify(text)} />
        </div>
        <div className="space-y-4">
          <textarea
            value={manualToken}
            className="input-field min-h-[140px]"
            placeholder="Vlož PIN nebo token"
            onChange={(e) => setManualToken(e.target.value)}
          />
          <button className="accent-button w-full" onClick={() => handleVerify(manualToken)} disabled={isSubmitting}>
            {isSubmitting ? 'Ověřuji...' : 'Ověřit token'}
          </button>
          {lastResult && (
            <div className="glass-subcard rounded-2xl p-4 text-sm text-slate-300 space-y-2">
              <p>Status: {lastResult.allowed ? 'Povoleno' : 'Zamítnuto'}</p>
              <p>Důvod: {lastResult.reason}</p>
              {lastResult.message && <p>Zpráva: {lastResult.message}</p>}
              {lastResult.membership?.package_name && (
                <p>Permanentka: {lastResult.membership.package_name}</p>
              )}
              {lastResult.membership?.status && <p>Stav permanentky: {lastResult.membership.status}</p>}
              {lastResult.user_name && <p>Uživatel: {lastResult.user_name}</p>}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

export default function ScannerPageContent() {
  const { toast, showToast } = useToast();

  return (
    <>
      <div className="min-h-screen bg-gradient-to-br from-[#f8fbff] via-[#f3f6fb] to-[#ecf1f9]">
        <header className="max-w-6xl mx-auto px-6 py-10">
          <h1 className="text-3xl sm:text-4xl font-semibold text-slate-900 mt-2">Turniket Scanner</h1>
          <p className="text-slate-500 text-sm mt-2">Veřejně dostupná URL pro ověřování QR tokenů.</p>
        </header>
        <main className="px-4 sm:px-6 lg:px-8 pb-16">
          <div className="max-w-5xl mx-auto">
            <ScannerConsole showToast={showToast} />
          </div>
        </main>
      </div>
      <Toast toast={toast} />
    </>
  );
}
