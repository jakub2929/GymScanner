'use client';

import Link from 'next/link';
import { PropsWithChildren, useEffect, useState } from 'react';
import { useAtomValue } from 'jotai';
import { tokenAtom } from '@/lib/authStore';
import { usePathname, useRouter } from 'next/navigation';
import { apiClient } from '@/lib/apiClient';
import { useLogout } from '@/hooks/useLogout';
import { useBranding } from '@/components/branding-context';
import { useBrandingLogo } from '@/hooks/useBrandingLogo';

const navLinks = [
  { href: '/admin', label: 'Přehled' },
  { href: '/admin/users', label: 'Uživatelé' },
  { href: '/admin/packages', label: 'Balíčky' },
  { href: '/admin/tokens', label: 'Tokeny' },
];

export default function AdminLayout({ children }: PropsWithChildren) {
  const token = useAtomValue(tokenAtom);
  const router = useRouter();
  const pathname = usePathname();
  const logout = useLogout('/admin/login');
  const [state, setState] = useState<'checking' | 'allowed'>('checking');
  const [open, setOpen] = useState(false);
  const [miniQr, setMiniQr] = useState<string | null>(null);
  const [miniToken, setMiniToken] = useState<string | null>(null);
  const branding = useBranding();
  const logoSrc = useBrandingLogo();

  useEffect(() => {
    let cancelled = false;

    async function verify() {
      if (typeof window === 'undefined') return;
      const storedToken = token || sessionStorage.getItem('access_token');
      if (!storedToken) {
        if (!cancelled) {
          setState('checking');
          router.replace('/admin/login');
        }
        return;
      }

      const storedAdmin = sessionStorage.getItem('is_admin');
      if (storedAdmin === 'true') {
        if (!cancelled) {
          setState('allowed');
        }
        return;
      }

      try {
        const info = await apiClient<{ is_admin: boolean }>('/api/user/info');
        if (cancelled) {
          return;
        }
        if (info.is_admin) {
          sessionStorage.setItem('is_admin', 'true');
          setState('allowed');
        } else {
          sessionStorage.setItem('is_admin', 'false');
          router.replace('/admin/login');
        }
      } catch {
        if (!cancelled) {
          router.replace('/admin/login');
        }
      }
    }

    verify();
    return () => {
      cancelled = true;
    };
  }, [token, router]);

  useEffect(() => {
    if (state !== 'allowed') return;
    let cancelled = false;
    async function loadMiniQr() {
      try {
        const res = await apiClient<{ qr_code_url?: string; token?: string }>('/api/my_qr');
        if (cancelled) return;
        setMiniQr(res.qr_code_url ?? null);
        setMiniToken(res.token ?? null);
      } catch {
        if (!cancelled) {
          setMiniQr(null);
          setMiniToken(null);
        }
      }
    }
    loadMiniQr();
    return () => {
      cancelled = true;
    };
  }, [state]);

  if (state === 'checking') {
    return (
      <div className="min-h-screen bg-[#04060f] text-white flex items-center justify-center">
        <p className="text-slate-400">Kontroluji oprávnění...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#020610] text-white">
      <nav className="max-w-6xl mx-auto flex flex-col gap-4 md:flex-row md:items-center md:justify-between md:flex-nowrap px-6 py-6">
        <div className="flex w-full items-center justify-between md:block">
          <div className="flex items-center gap-3">
            {logoSrc && (
              <img
                src={logoSrc}
                alt={`${branding.brandName} logo`}
                className="h-10 w-10 rounded-2xl border border-white/10 object-contain bg-white/5 p-2"
              />
            )}
            <div>
              <Link
                href="/admin"
                className="text-2xl font-semibold tracking-tight"
                onClick={() => setOpen(false)}
              >
                {branding.brandName} Admin
              </Link>
            </div>
          </div>
          <button
            className="md:hidden text-slate-200 border border-white/15 rounded-full p-2"
            onClick={() => setOpen((prev) => !prev)}
            aria-label="Otevřít admin navigaci"
          >
            <span className="block w-5 h-0.5 bg-white mb-1" />
            <span className="block w-5 h-0.5 bg-white mb-1" />
            <span className="block w-5 h-0.5 bg-white" />
          </button>
        </div>
        <div className="hidden md:flex items-center gap-4 text-sm text-slate-400 md:flex-nowrap overflow-x-auto justify-end flex-1">
          <div className="flex items-center gap-4">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={
                  pathname === link.href
                    ? 'text-[var(--brand-primary)] font-semibold'
                    : 'hover:text-[var(--brand-primary)] transition-colors'
                }
              >
                {link.label}
              </Link>
            ))}
          </div>
          <button
            onClick={() => {
              setOpen(false);
              logout();
            }}
            className="flex items-center gap-3 rounded-2xl border border-white/10 px-3 py-2 hover:border-[var(--brand-primary)] transition"
            aria-label="Odhlásit se"
          >
            <div className="h-10 w-10 rounded-lg border border-white/15 flex items-center justify-center">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                className="h-5 w-5 text-white"
              >
                <path d="M10 7V5a2 2 0 0 1 2-2h7" />
                <path d="M19 21h-7a2 2 0 0 1-2-2v-2" />
                <path d="M7 16l-4-4 4-4" />
                <path d="M3 12h13" />
              </svg>
            </div>
          </button>
          <Link
            href="/dashboard"
            className="flex items-center gap-3 rounded-2xl border border-white/10 px-3 py-2 hover:border-[var(--brand-primary)] transition"
          >
            {miniQr ? (
              <img src={miniQr} alt="QR náhled" className="h-10 w-10 rounded-lg border border-white/10 object-contain" />
            ) : (
              <div className="h-10 w-10 rounded-lg border border-dashed border-white/10 flex items-center justify-center text-[10px] text-slate-500">
                QR
              </div>
            )}
            <div className="text-left leading-tight">
              <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">Uživatel</p>
              <p className="font-mono text-sm text-white">{miniToken ?? '---'}</p>
            </div>
          </Link>
        </div>
      </nav>
      {open && (
        <div className="md:hidden px-6 pb-4 space-y-2 text-sm text-slate-200">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="block rounded-2xl glass-panel p-4"
              onClick={() => setOpen(false)}
            >
              {link.label}
            </Link>
          ))}
          <Link href="/dashboard" className="block rounded-2xl glass-panel p-4" onClick={() => setOpen(false)}>
            <div className="flex items-center gap-3">
              {miniQr ? (
                <img src={miniQr} alt="QR náhled" className="h-12 w-12 rounded-lg border border-white/10 object-contain" />
              ) : (
                <div className="h-12 w-12 rounded-lg border border-dashed border-white/10 flex items-center justify-center text-xs text-slate-500">
                  QR
                </div>
              )}
              <div>
                <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Uživatel</p>
                <p className="font-mono text-sm text-white">{miniToken ?? '---'}</p>
              </div>
            </div>
          </Link>
          <button
            onClick={() => {
              setOpen(false);
              logout();
            }}
            className="w-full rounded-2xl border border-white/20 py-4 flex items-center justify-center"
            aria-label="Odhlásit se"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              className="h-6 w-6 text-white"
            >
              <path d="M10 7V5a2 2 0 0 1 2-2h7" />
              <path d="M19 21h-7a2 2 0 0 1-2-2v-2" />
              <path d="M7 16l-4-4 4-4" />
              <path d="M3 12h13" />
            </svg>
          </button>
        </div>
      )}
      <main className="px-4 sm:px-6 lg:px-8 pb-10 max-w-6xl mx-auto w-full">{children}</main>
      {branding.footerText && (
        <footer className="px-6 pb-6 text-center text-xs text-slate-500">{branding.footerText}</footer>
      )}
    </div>
  );
}
