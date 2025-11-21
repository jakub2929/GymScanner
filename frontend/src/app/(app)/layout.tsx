'use client';

import Link from 'next/link';
import { PropsWithChildren, useEffect, useState } from 'react';
import { useAtomValue } from 'jotai';
import { tokenAtom } from '@/lib/authStore';
import { useRouter, usePathname } from 'next/navigation';
import { useLogout } from '@/hooks/useLogout';
import { useBranding } from '@/components/branding-context';
import { useBrandingLogo } from '@/hooks/useBrandingLogo';

const navLinks = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/settings', label: 'Nastavení' },
];

export default function AppLayout({ children }: PropsWithChildren) {
  const token = useAtomValue(tokenAtom);
  const router = useRouter();
  const pathname = usePathname();
  const logout = useLogout();
  const [menuOpen, setMenuOpen] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);
  const branding = useBranding();
  const logoSrc = useBrandingLogo();

  const localToken = typeof window !== 'undefined' ? sessionStorage.getItem('access_token') : null;
  const effectiveToken = token || localToken;

  useEffect(() => {
    if (typeof window !== 'undefined') {
      setIsAdmin(sessionStorage.getItem('is_admin') === 'true');
    }
  }, [effectiveToken]);

  useEffect(() => {
    if (!effectiveToken && typeof window !== 'undefined') {
      router.replace('/login');
    }
  }, [effectiveToken, router]);

  const userNavLinks = isAdmin ? [...navLinks, { href: '/admin', label: 'Admin console' }] : navLinks;

  if (!effectiveToken) {
    return null;
  }

  return (
    <div className="min-h-screen bg-[#020610] text-white">
      <nav className="max-w-5xl mx-auto px-6 py-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
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
              <p className="text-xs uppercase tracking-[0.35em] text-slate-500 mt-1">{branding.consoleName}</p>
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
        <div className="hidden md:flex flex-wrap items-center gap-4 text-sm text-slate-400">
          {userNavLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={pathname === link.href ? 'text-white font-medium' : 'hover:text-white transition-colors'}
            >
              {link.label}
            </Link>
          ))}
          <button
            onClick={() => {
              setMenuOpen(false);
              logout();
            }}
            className="px-4 py-2 rounded-full border border-white/15 hover:bg-white/10 transition-colors"
          >
            Odhlásit se
          </button>
        </div>
      </nav>
      {menuOpen && (
        <div className="md:hidden px-6 pb-4 space-y-3 text-sm text-slate-200">
          {userNavLinks.map((link) => (
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
            className="w-full rounded-2xl border border-white/15 py-3"
          >
            Odhlásit se
          </button>
        </div>
      )}
      <main className="px-4 sm:px-6 lg:px-8 pb-10">
        <div className="max-w-5xl mx-auto w-full space-y-8">{children}</div>
      </main>
      {branding.footerText && (
        <footer className="px-6 pb-6 text-center text-xs text-slate-500">{branding.footerText}</footer>
      )}
    </div>
  );
}
