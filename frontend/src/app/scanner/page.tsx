'use client';

import AuthCard from '@/components/auth-card';
import QrScanner from '@/components/qr-scanner';
import { Toast, useToast } from '@/components/toast';
import { useLogout } from '@/hooks/useLogout';
import { apiClient } from '@/lib/apiClient';
import { setTokenAtom, tokenAtom } from '@/lib/authStore';
import { zodResolver } from '@hookform/resolvers/zod';
import { useSetAtom, useAtomValue } from 'jotai';
import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

const loginSchema = z.object({
  email: z.string().email('Zadejte platný e-mail'),
  password: z.string().min(6, 'Heslo musí mít alespoň 6 znaků'),
});

const SCANNER_EMAIL = 'scanner@scanner.cz';

interface LoginResponse {
  access_token: string;
  user_name: string;
  user_email: string;
  is_admin: boolean;
}

interface VerifyResponse {
  allowed: boolean;
  reason: string;
  credits_left: number;
  cooldown_seconds_left?: number | null;
  user_name?: string | null;
  user_email?: string | null;
}

type LoginValues = z.infer<typeof loginSchema>;

export default function ScannerPage() {
  const token = useAtomValue(tokenAtom);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    // We intentionally flip the mounted flag after hydration to safely access sessionStorage.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true);
  }, []);

  if (!mounted) {
    return null;
  }

  const sessionToken = typeof window !== 'undefined' ? sessionStorage.getItem('access_token') : null;
  const effectiveToken = token || sessionToken;

  return effectiveToken ? <ScannerConsole /> : <ScannerLoginForm />;
}

function ScannerLoginForm() {
  const { toast, showToast } = useToast();
  const setToken = useSetAtom(setTokenAtom);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: SCANNER_EMAIL },
  });

  async function onSubmit(values: LoginValues) {
    setIsSubmitting(true);
    try {
      const response = await apiClient<LoginResponse>('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ username: values.email, password: values.password }).toString(),
      });
      setToken(response.access_token);
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('user_name', response.user_name);
        sessionStorage.setItem('user_email', response.user_email);
        sessionStorage.setItem('is_admin', response.is_admin ? 'true' : 'false');
      }
      showToast('Přihlášení úspěšné', 'success');
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Chyba při přihlášení', 'error');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <>
      <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4 py-12">
        <AuthCard title="Scanner Login" subtitle="Přihlaš se dedikovaným účtem">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <input
                type="email"
                className="input-field bg-slate-900 text-slate-100 border border-slate-800"
                {...register('email')}
                readOnly
              />
              {errors.email && <p className="text-xs text-rose-300 mt-1">{errors.email.message}</p>}
              <p className="text-xs text-slate-400 mt-1">Účet: {SCANNER_EMAIL}</p>
            </div>
            <div>
              <input
                type="password"
                placeholder="Heslo"
                className="input-field bg-slate-900 text-slate-100 border border-slate-800"
                {...register('password')}
              />
              {errors.password && <p className="text-xs text-rose-300 mt-1">{errors.password.message}</p>}
            </div>
            <button type="submit" className="accent-button w-full" disabled={isSubmitting}>
              {isSubmitting ? 'Přihlašuji...' : 'Přihlásit se'}
            </button>
            <p className="text-xs text-center text-slate-500">
              Registrace zde není dostupná. Přístup je jen pro servisní účet skeneru.
            </p>
          </form>
        </AuthCard>
      </div>
      <Toast toast={toast} />
    </>
  );
}

function ScannerConsole() {
  const { toast, showToast } = useToast();
  const logout = useLogout('/scanner');
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
      <div className="min-h-screen bg-gradient-to-br from-[#f8fbff] via-[#f3f6fb] to-[#ecf1f9]">
        <header className="max-w-5xl mx-auto flex items-center justify-between px-6 py-6">
          <div>
            <p className="text-xs uppercase tracking-[0.35em] text-emerald-500/80">Gym Access</p>
            <h1 className="text-2xl font-semibold text-slate-900">Turniket Scanner</h1>
          </div>
          <button
            onClick={() => logout('/scanner')}
            className="px-4 py-2 rounded-full border border-slate-200 bg-white text-sm text-slate-700 hover:bg-slate-50 transition-colors"
          >
            Odhlásit se
          </button>
        </header>
        <main className="px-4 sm:px-6 lg:px-8 pb-16">
          <div className="max-w-5xl mx-auto w-full space-y-8">
            <section className="glass-panel rounded-3xl p-6 sm:p-10">
              <div className="flex flex-col gap-4">
                <div>
                  <h2 className="text-3xl sm:text-4xl font-semibold">Scanner</h2>
                  <p className="text-slate-400 mt-2 text-sm">Skenuj QR kódy nebo vlož token ručně.</p>
                </div>
                <div className="glass-subcard rounded-2xl p-4 text-sm">
                  <p
                    className={
                      statusType === 'success'
                        ? 'text-emerald-300'
                        : statusType === 'error'
                          ? 'text-rose-300'
                          : 'text-slate-200'
                    }
                  >
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
                  <button className="accent-button w-full" onClick={() => handleVerify(manualToken)} disabled={isSubmitting}>
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
        </main>
      </div>
      <Toast toast={toast} />
    </>
  );
}
