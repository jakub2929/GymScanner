'use client';

import { useState } from 'react';
import QrScanner from '@/components/qr-scanner';
import { Toast, useToast } from '@/components/toast';
import { apiClient } from '@/lib/apiClient';

interface VerifyResponse {
  allowed: boolean;
  reason: string;
  credits_left: number;
  cooldown_seconds_left?: number | null;
  user_name?: string | null;
  user_email?: string | null;
}

export default function ScannerPage() {
  const { toast, showToast } = useToast();
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
      if (response.allowed) {
        setStatus('Přístup povolen');
        setStatusType('success');
      } else {
        setStatus(messageFromReason(response.reason));
        setStatusType(response.reason === 'cooldown' ? 'info' : 'error');
      }
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
      case 'no_credits':
        return 'Nedostatek vstupů';
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
    <>
      <div className="space-y-8">
        <section className="glass-panel rounded-3xl p-6 sm:p-10">
          <div className="flex flex-col gap-4">
            <div>
              <h1 className="text-3xl sm:text-4xl font-semibold">Scanner</h1>
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
          </div>

          <div className="mt-6 grid lg:grid-cols-2 gap-6">
            <div className="glass-subcard rounded-2xl p-4">
              <QrScanner onDecode={(text) => handleVerify(text)} />
            </div>
            <div className="space-y-4">
              <textarea
                value={manualToken}
                className="input-field min-h-[140px]"
                placeholder="Vlož token"
                onChange={(e) => setManualToken(e.target.value)}
              />
              <button className="accent-button" onClick={() => handleVerify(manualToken)} disabled={isSubmitting}>
                {isSubmitting ? 'Ověřuji...' : 'Ověřit token'}
              </button>
              {lastResult && (
                <div className="glass-subcard rounded-2xl p-4 text-sm text-slate-300 space-y-2">
                  <p>Status: {lastResult.allowed ? 'Povoleno' : 'Zamítnuto'}</p>
                  <p>Důvod: {lastResult.reason}</p>
                  <p>Zbývá vstupů: {lastResult.credits_left}</p>
                  {lastResult.user_name && <p>Uživatel: {lastResult.user_name}</p>}
                </div>
              )}
            </div>
          </div>
        </section>
      </div>
      <Toast toast={toast} />
    </>
  );
}
