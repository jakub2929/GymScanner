'use client';

import Link from 'next/link';
import { PropsWithChildren, useEffect, useState } from 'react';
import { useAtomValue } from 'jotai';
import { tokenAtom } from '@/lib/authStore';
import { useRouter, usePathname } from 'next/navigation';
import { useLogout } from '@/hooks/useLogout';
import { useBranding } from '@/components/branding-context';
import { useBrandingLogo } from '@/hooks/useBrandingLogo';
import { apiClient } from '@/lib/apiClient';

const navLinks = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/permanentky', label: 'Permanentky' },
  { href: '/treninky', label: 'Tréninky' },
  { href: '/aktivita', label: 'Aktivita' },
  { href: '/settings', label: 'Nastavení' },
];

export default function AppLayout({ children }: PropsWithChildren) {
  const token = useAtomValue(tokenAtom);
  const router = useRouter();
  const pathname = usePathname();
  const logout = useLogout();
  const [menuOpen, setMenuOpen] = useState(false);
  const [miniQr, setMiniQr] = useState<string | null>(null);
  const [miniToken, setMiniToken] = useState<string | null>(null);
  const branding = useBranding();
  const logoSrc = useBrandingLogo();

  const localToken = typeof window !== 'undefined' ? sessionStorage.getItem('access_token') : null;
  const effectiveToken = token || localToken;
  const isAdmin = typeof window !== 'undefined' && sessionStorage.getItem('is_admin') === 'true';

  useEffect(() => {
    if (!effectiveToken && typeof window !== 'undefined') {
      router.replace('/login');
    }
  }, [effectiveToken, router]);

  useEffect(() => {
    let cancelled = false;
    async function loadMiniQr() {
      if (!effectiveToken) return;
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
  }, [effectiveToken]);

  const userNavLinks = isAdmin ? [...navLinks, { href: '/admin', label: 'Admin console' }] : navLinks;
  const dashboardLink = userNavLinks.find((link) => link.href === '/dashboard');
  const otherLinks = userNavLinks.filter((link) => link.href !== '/dashboard');

  if (!effectiveToken) {
    return null;
  }

  return (
    <div className="min-h-screen bg-[#020610] text-white">
      <nav className="max-w-6xl mx-auto px-6 py-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between md:flex-nowrap">
        <div className="flex items-center justify-between">
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
                href="/dashboard"
                className="text-2xl font-semibold tracking-tight"
                onClick={() => setMenuOpen(false)}
              >
                {branding.brandName}
              </Link>
            </div>
          </div>
          <button
            className="md:hidden text-slate-200 border border-white/15 rounded-full p-2"
            onClick={() => setMenuOpen((prev) => !prev)}
            aria-label="Otevřít navigaci"
          >
            <span className="block w-5 h-0.5 bg-white mb-1" />
            <span className="block w-5 h-0.5 bg-white mb-1" />
            <span className="block w-5 h-0.5 bg-white" />
          </button>
        </div>
        <div className="hidden md:flex items-center gap-4 text-sm text-slate-400 md:flex-nowrap overflow-x-auto flex-1 justify-end">
          <div className="flex items-center gap-4">
            {otherLinks.map((link) => (
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
              setMenuOpen(false);
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
          {dashboardLink && (
            <Link
              href={dashboardLink.href}
              className="flex items-center gap-3 rounded-2xl border border-white/10 px-3 py-2 hover:border-[var(--brand-primary)] transition"
            >
              {miniQr ? (
                <img src={miniQr} alt="QR" className="h-10 w-10 rounded-lg border border-white/10 object-contain" />
              ) : (
                <div className="h-10 w-10 rounded-lg border border-dashed border-white/10 flex items-center justify-center text-[10px] text-slate-500">
                  QR
                </div>
              )}
              <div className="text-left leading-tight">
                <p className="text-[10px] uppercase tracking-[0.3em] text-slate-500">Dashboard</p>
                <p className="font-mono text-sm text-white">{miniToken ?? '---'}</p>
              </div>
            </Link>
          )}
        </div>
      </nav>
      {menuOpen && (
        <div className="md:hidden px-6 pb-4 space-y-3 text-sm text-slate-200">
          {otherLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="block rounded-2xl glass-panel p-4"
              onClick={() => setMenuOpen(false)}
            >
              {link.label}
            </Link>
          ))}
          <button
            onClick={() => {
              setMenuOpen(false);
              logout();
            }}
            className="w-full rounded-2xl border border-white/10 py-4 flex items-center justify-center"
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
          {dashboardLink && (
            <Link
              href={dashboardLink.href}
              className="block rounded-2xl glass-panel p-4"
              onClick={() => setMenuOpen(false)}
            >
              <div className="flex items-center gap-3">
                {miniQr ? (
                  <img src={miniQr} alt="QR" className="h-12 w-12 rounded-lg border border-white/10 object-contain" />
                ) : (
                  <div className="h-12 w-12 rounded-lg border border-dashed border-white/10 flex items-center justify-center text-xs text-slate-400">
                    QR
                  </div>
                )}
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Dashboard</p>
                  <p className="font-mono text-sm text-white">{miniToken ?? 'Zobrazit'}</p>
                </div>
              </div>
            </Link>
          )}
        </div>
      )}
      <main className="px-4 sm:px-6 lg:px-8 pb-10">
        <div className="max-w-6xl mx-auto w-full space-y-8">{children}</div>
      </main>
      {branding.footerText && (
        <footer className="px-6 pb-6 text-center text-xs text-slate-500">{branding.footerText}</footer>
      )}
    </div>
  );
}
