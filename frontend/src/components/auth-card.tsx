import Link from 'next/link';
import { PropsWithChildren } from 'react';

export default function AuthCard({ title, subtitle, children }: PropsWithChildren<{ title: string; subtitle?: string }>) {
  return (
    <div className="min-h-screen bg-[#04060f] text-white flex flex-col">
      <nav className="max-w-6xl mx-auto w-full px-6 py-6 flex items-center justify-between">
        <Link href="/" className="text-2xl font-semibold tracking-tight">
          Gym Access
        </Link>
        <div className="flex items-center gap-6 text-sm text-slate-400">
          <Link href="/login" className="hover:text-white transition-colors">
            Přihlášení
          </Link>
          <Link href="/register" className="hover:text-white transition-colors">
            Registrace
          </Link>
        </div>
      </nav>
      <main className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="glass-auth max-w-lg w-full p-10 rounded-3xl">
          <p className="text-xs uppercase tracking-[0.35em] text-emerald-200/70 mb-3">Gym access</p>
          <h1 className="text-3xl font-semibold tracking-tight">{title}</h1>
          {subtitle && <p className="text-slate-400 mt-2 text-sm">{subtitle}</p>}
          <div className="mt-8 space-y-6">{children}</div>
        </div>
      </main>
    </div>
  );
}
