'use client';

import Link from 'next/link';
import { PropsWithChildren } from 'react';
import { useBranding } from './branding-context';
import { useBrandingLogo } from '@/hooks/useBrandingLogo';

interface AuthCardProps {
  title: string;
  subtitle?: string;
  navLinks?: { href: string; label: string }[];
}

export default function AuthCard({ title, subtitle, navLinks, children }: PropsWithChildren<AuthCardProps>) {
  const branding = useBranding();
  const logoSrc = useBrandingLogo();
  const links =
    navLinks ??
    [
      { href: '/login', label: 'Přihlášení' },
      { href: '/register', label: 'Registrace' },
    ];

  return (
    <div className="min-h-screen bg-[#04060f] text-white flex flex-col">
      <nav className="max-w-6xl mx-auto w-full px-6 py-6 flex items-center justify-between">
        <Link href="/" className="text-2xl font-semibold tracking-tight">
          {branding.brandName}
        </Link>
        <div className="flex items-center gap-6 text-sm text-slate-400">
          {links.map((link) => (
            <Link key={link.href} href={link.href} className="hover:text-white transition-colors">
              {link.label}
            </Link>
          ))}
        </div>
      </nav>
      <main className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="glass-auth max-w-lg w-full p-10 rounded-3xl">
          <div className="flex items-center gap-4 mb-4">
            {logoSrc && (
              <img src={logoSrc} alt={`${branding.brandName} logo`} className="h-12 w-12 rounded-2xl object-contain border border-white/5 bg-white/5 p-2" />
            )}
            <div>
              <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
            </div>
          </div>
          {subtitle && <p className="text-slate-300 text-sm">{subtitle}</p>}
          <div className="mt-8 space-y-6">{children}</div>
          {branding.supportEmail && (
            <p className="text-xs text-slate-400 mt-6">
              Potřebuješ pomoc?{' '}
              <a href={`mailto:${branding.supportEmail}`} className="text-white hover:underline">
                {branding.supportEmail}
              </a>
            </p>
          )}
        </div>
      </main>
      {branding.footerText && (
        <footer className="text-center text-xs text-slate-500 pb-6">{branding.footerText}</footer>
      )}
    </div>
  );
}
