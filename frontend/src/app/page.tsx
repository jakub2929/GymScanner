import Link from 'next/link';

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center px-6 py-16">
      <div className="max-w-3xl space-y-6 text-center">
        <p className="text-sm uppercase tracking-[0.35em] text-emerald-300/80">Gym Access Next</p>
        <h1 className="text-4xl sm:text-5xl font-semibold tracking-tight">
          Frontend se přesouvá na Next.js + TypeScript
        </h1>
        <p className="text-slate-400 text-lg">
          Tato aplikace zatím obsahuje jen výchozí stránku. Další kroky: implementace autentizace, dashboardu, skeneru a admin
          rozhraní dle plánu migrace.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link
            href="https://nextjs.org/docs"
            className="px-6 py-3 rounded-full border border-white/20 hover:bg-white/10 transition-colors"
            target="_blank"
          >
            Dokumentace Next.js
          </Link>
          <Link
            href="https://github.com/jakub2929/GymScanner/blob/main/docs/nextjs_migration_plan.md"
            className="px-6 py-3 rounded-full bg-emerald-400 text-slate-950 font-semibold"
            target="_blank"
          >
            Migrační plán
          </Link>
        </div>
      </div>
    </main>
  );
}
