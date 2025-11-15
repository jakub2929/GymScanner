'use client';

import QrScanner from '@/components/qr-scanner';
import { Toast, useToast } from '@/components/toast';
import { apiClient } from '@/lib/apiClient';
import { setTokenAtom, tokenAtom } from '@/lib/authStore';
import { zodResolver } from '@hookform/resolvers/zod';
import { useAtomValue, useSetAtom } from 'jotai';
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
type StoredUserInfo = { name: string | null; email: string | null };
type ShowToast = (message: string, type?: 'success' | 'error') => void;

export default function ScannerPage() {
  const { toast, showToast } = useToast();

  return (
    <>
      <div className="min-h-screen bg-gradient-to-br from-[#f8fbff] via-[#f3f6fb] to-[#ecf1f9]">
        <header className="max-w-6xl mx-auto px-6 py-10">
          <p className="text-xs uppercase tracking-[0.35em] text-emerald-500/70">Gym Access</p>
          <h1 className="text-3xl sm:text-4xl font-semibold text-slate-900 mt-2">Turniket Scanner</h1>
          <p className="text-slate-500 text-sm mt-2">
            URL je veřejně dostupná i bez přihlášení. Servisní login pro účet {SCANNER_EMAIL} je stále k dispozici na
            stejné stránce.
          </p>
        </header>
        <main className="px-4 sm:px-6 lg:px-8 pb-16">
          <div className="max-w-6xl mx-auto grid gap-6 lg:grid-cols-[2fr,1fr]">
            <ScannerConsole showToast={showToast} />
            <ScannerAccessPanel showToast={showToast} />
          </div>
        </main>
      </div>
      <Toast toast={toast} />
    </>
  );
}

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
  );
}

function ScannerAccessPanel({ showToast }: { showToast: ShowToast }) {
  const setToken = useSetAtom(setTokenAtom);
  const token = useAtomValue(tokenAtom);
  const [userInfo, setUserInfo] = useState(() => getStoredUserInfo());
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: SCANNER_EMAIL },
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      setUserInfo(getStoredUserInfo());
    }
  }, [token]);

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
      setUserInfo({ name: response.user_name, email: response.user_email });
      showToast('Přihlášení úspěšné');
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Chyba při přihlášení', 'error');
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleLogout() {
    try {
      await apiClient('/api/logout', { method: 'POST' });
    } catch (error) {
      console.warn('Logout call failed', error);
    } finally {
      if (typeof window !== 'undefined') {
        sessionStorage.removeItem('user_name');
        sessionStorage.removeItem('user_email');
        sessionStorage.removeItem('is_admin');
      }
      setToken(null);
      setUserInfo({ name: null, email: null });
      showToast('Odhlášení proběhlo', 'success');
    }
  }

  const isLoggedIn = Boolean(token);

  return (
    <section className="glass-panel rounded-3xl p-6 sm:p-8 space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-100">Servisní přístup</h2>
        <p className="text-slate-400 text-sm mt-1">Přihlas se speciálním účtem pro autorizovaný režim.</p>
      </div>
      <div className="glass-subcard rounded-2xl p-4 text-sm text-slate-200 space-y-1">
        <p>
          Stav:{' '}
          <span className={isLoggedIn ? 'text-emerald-300' : 'text-rose-300'}>
            {isLoggedIn ? 'Přihlášeno' : 'Nepřihlášeno'}
          </span>
        </p>
        {userInfo.email && <p>Účet: {userInfo.email}</p>}
      </div>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <label className="text-xs uppercase tracking-[0.25em] text-slate-400">E-mail</label>
          <input
            type="email"
            className="input-field mt-2 bg-[#05070f] text-white border border-white/10"
            readOnly
            {...register('email')}
          />
          <p className="text-xs text-slate-500 mt-1">Uživatel pro scanner: {SCANNER_EMAIL}</p>
          {errors.email && <p className="text-xs text-rose-300 mt-1">{errors.email.message}</p>}
        </div>
        <div>
          <label className="text-xs uppercase tracking-[0.25em] text-slate-400">Heslo</label>
          <input
            type="password"
            placeholder="Heslo"
            className="input-field mt-2 bg-[#05070f] text-white border border-white/10"
            {...register('password')}
          />
          {errors.password && <p className="text-xs text-rose-300 mt-1">{errors.password.message}</p>}
        </div>
        <button type="submit" className="accent-button w-full" disabled={isSubmitting}>
          {isSubmitting ? 'Přihlašuji...' : 'Přihlásit servisní účet'}
        </button>
        <p className="text-xs text-slate-500 text-center">
          Registrace tady není dostupná. Využij předpřipravený účet pro zařízení scanneru.
        </p>
      </form>
      {isLoggedIn && (
        <button
          type="button"
          className="surface-card w-full rounded-2xl border border-white/10 py-3 text-sm text-slate-100"
          onClick={handleLogout}
        >
          Odhlásit servisní účet
        </button>
      )}
    </section>
  );
}

function getStoredUserInfo(): StoredUserInfo {
  if (typeof window === 'undefined') {
    return { name: null, email: null };
  }
  return {
    name: sessionStorage.getItem('user_name'),
    email: sessionStorage.getItem('user_email'),
  };
}
