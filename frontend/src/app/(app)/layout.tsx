'use client';

import Link from 'next/link';
import { PropsWithChildren, useEffect } from 'react';
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
    <div className="min-h-screen bg-[#04060f] text-white">
      <nav className="max-w-6xl mx-auto flex items-center justify-between px-6 py-6">
        <Link href="/dashboard" className="text-2xl font-semibold tracking-tight">
          Gym Access
        </Link>
        <div className="hidden md:flex items-center gap-6 text-sm text-slate-400">
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
            onClick={logout}
            className="px-4 py-2 rounded-full border border-white/15 hover:bg-white/10 transition-colors"
          >
            Odhlásit se
          </button>
        </div>
      </nav>
      <main className="px-4 sm:px-6 lg:px-8 pb-16">{children}</main>
    </div>
  );
}
