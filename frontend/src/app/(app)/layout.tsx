'use client';

import Link from 'next/link';
import { PropsWithChildren, useEffect, useState } from 'react';
import { useAtomValue } from 'jotai';
import { tokenAtom } from '@/lib/authStore';
import { useRouter, usePathname } from 'next/navigation';
import { useLogout } from '@/hooks/useLogout';

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

  const localToken = typeof window !== 'undefined' ? sessionStorage.getItem('access_token') : null;
  const effectiveToken = token || localToken;

  useEffect(() => {
    if (!effectiveToken && typeof window !== 'undefined') {
      router.replace('/login');
    }
  }, [effectiveToken, router]);

  if (!effectiveToken) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-[#f8fbff] via-[#f3f6fb] to-[#ecf1f9] text-slate-900">
      <nav className="max-w-5xl mx-auto flex items-center justify-between px-6 py-6">
        <Link
          href="/dashboard"
          className="text-2xl font-semibold tracking-tight text-slate-900"
          onClick={() => setMenuOpen(false)}
        >
          Gym Access
        </Link>
        <div className="hidden md:flex items-center gap-6 text-sm text-slate-500">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={
                pathname === link.href
                  ? 'text-slate-900 font-medium'
                  : 'hover:text-slate-900 transition-colors'
              }
            >
              {link.label}
            </Link>
          ))}
          <button
            onClick={() => {
              setMenuOpen(false);
              logout();
            }}
            className="px-4 py-2 rounded-full border border-slate-200 hover:bg-white transition-colors"
          >
            Odhlásit se
          </button>
        </div>
        <button
          className="md:hidden text-slate-600 border border-slate-200 rounded-full p-2"
          onClick={() => setMenuOpen((prev) => !prev)}
          aria-label="Otevřít navigaci"
        >
          <span className="block w-5 h-0.5 bg-slate-800 mb-1" />
          <span className="block w-5 h-0.5 bg-slate-800 mb-1" />
          <span className="block w-5 h-0.5 bg-slate-800" />
        </button>
      </nav>
      {menuOpen && (
        <div className="md:hidden px-6 pb-4 text-sm text-slate-700 space-y-2">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="block rounded-2xl surface-card p-4"
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
            className="w-full rounded-2xl border border-slate-200 bg-white py-3"
          >
            Odhlásit se
          </button>
        </div>
      )}
      <main className="px-4 sm:px-6 lg:px-8 pb-16">
        <div className="max-w-5xl mx-auto w-full">{children}</div>
      </main>
    </div>
  );
}
