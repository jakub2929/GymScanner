'use client';

import Link from 'next/link';
import { PropsWithChildren, useEffect, useState } from 'react';
import { useAtomValue } from 'jotai';
import { tokenAtom } from '@/lib/authStore';
import { usePathname, useRouter } from 'next/navigation';
import { apiClient } from '@/lib/apiClient';
import { useLogout } from '@/hooks/useLogout';
import { useBranding } from '@/components/branding-context';

const navLinks = [
  { href: '/admin', label: 'Přehled' },
  { href: '/admin/users', label: 'Uživatelé' },
  { href: '/admin/tokens', label: 'Tokeny' },
];

export default function AdminLayout({ children }: PropsWithChildren) {
  const token = useAtomValue(tokenAtom);
  const router = useRouter();
  const pathname = usePathname();
  const logout = useLogout('/admin/login');
  const [state, setState] = useState<'checking' | 'allowed'>('checking');
  const [open, setOpen] = useState(false);
  const branding = useBranding();

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

  if (state === 'checking') {
    return (
      <div className="min-h-screen bg-[#04060f] text-white flex items-center justify-center">
        <p className="text-slate-400">Kontroluji oprávnění...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#020610] text-white">
      <nav className="max-w-6xl mx-auto flex flex-col gap-4 md:flex-row md:items-center md:justify-between px-6 py-6">
        <div className="flex w-full items-center justify-between md:block">
          <div className="flex items-center gap-3">
            {branding.logoUrl && (
              <img
                src={branding.logoUrl}
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
              <p className="text-xs uppercase tracking-[0.35em] text-slate-500 mt-1">{branding.consoleName}</p>
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
        <div className="hidden md:flex flex-wrap items-center gap-3 text-sm text-slate-400">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={pathname === link.href ? 'text-white font-medium' : 'hover:text-white transition-colors'}
            >
              {link.label}
            </Link>
          ))}
          <Link href="/dashboard" className="hover:text-white transition-colors">
            Uživatelský pohled
          </Link>
          <button
            onClick={() => {
              setOpen(false);
              logout();
            }}
            className="px-4 py-2 rounded-full border border-white/15 hover:bg-white/10 transition-colors"
          >
            Odhlásit
          </button>
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
            Uživatelský pohled
          </Link>
          <button
            onClick={() => {
              setOpen(false);
              logout();
            }}
            className="w-full rounded-2xl border border-white/20 py-3"
          >
            Odhlásit
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
