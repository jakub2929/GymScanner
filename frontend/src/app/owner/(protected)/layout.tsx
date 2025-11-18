'use client';

import Link from 'next/link';
import { PropsWithChildren, useEffect, useState } from 'react';
import { useAtomValue } from 'jotai';
import { ownerTokenAtom } from '@/lib/authStore';
import { usePathname, useRouter } from 'next/navigation';
import { ownerApiClient } from '@/lib/apiClient';
import { useOwnerLogout } from '@/hooks/useOwnerLogout';
import { useBranding } from '@/components/branding-context';

const navLinks = [{ href: '/owner/branding', label: 'Branding' }];

export default function OwnerLayout({ children }: PropsWithChildren) {
  const ownerToken = useAtomValue(ownerTokenAtom);
  const router = useRouter();
  const pathname = usePathname();
  const logout = useOwnerLogout();
  const branding = useBranding();
  const [state, setState] = useState<'checking' | 'allowed'>('checking');

  useEffect(() => {
    let cancelled = false;
    async function verify() {
      const storedToken = ownerToken || (typeof window !== 'undefined' ? sessionStorage.getItem('owner_access_token') : null);
      if (!storedToken) {
        if (!cancelled) {
          setState('checking');
          router.replace('/owner/login');
        }
        return;
      }
      try {
        await ownerApiClient('/api/owner/me');
        if (!cancelled) {
          setState('allowed');
        }
      } catch {
        if (!cancelled) {
          router.replace('/owner/login');
        }
      }
    }
    verify();
    return () => {
      cancelled = true;
    };
  }, [ownerToken, router]);

  if (state === 'checking') {
    return (
      <div className="min-h-screen bg-[#04060f] text-white flex items-center justify-center">
        <p className="text-slate-400">Ověřuji přístup...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#020610] text-white">
      <nav className="max-w-5xl mx-auto px-6 py-6 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3">
          {branding.logoUrl && (
            <img
              src={branding.logoUrl}
              alt={`${branding.brandName} logo`}
              className="h-10 w-10 rounded-2xl border border-white/10 object-contain bg-white/5 p-2"
            />
          )}
          <div>
            <Link href="/owner/branding" className="text-2xl font-semibold tracking-tight">
              {branding.brandName} Owner
            </Link>
            <p className="text-xs uppercase tracking-[0.35em] text-slate-500 mt-1">{branding.consoleName}</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-sm text-slate-400">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={pathname === link.href ? 'text-white font-medium' : 'hover:text-white transition-colors'}
            >
              {link.label}
            </Link>
          ))}
          <button
            onClick={() => logout()}
            className="px-4 py-2 rounded-full border border-white/15 hover:bg-white/10 transition-colors"
          >
            Odhlásit se
          </button>
        </div>
      </nav>
      <main className="px-4 sm:px-6 lg:px-8 pb-10">
        <div className="max-w-5xl mx-auto w-full">{children}</div>
      </main>
      {branding.footerText && (
        <footer className="px-6 pb-6 text-center text-xs text-slate-500">{branding.footerText}</footer>
      )}
    </div>
  );
}
