'use client';

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/apiClient';
import { Toast, useToast } from '@/components/toast';

interface PresenceSession {
  id: number;
  user_id: number;
  user_name?: string | null;
  user_email?: string | null;
  token_id?: number | null;
  membership_id?: number | null;
  started_at?: string | null;
  ended_at?: string | null;
  duration_seconds?: number | null;
  last_direction?: string | null;
  status: string;
  notes?: string | null;
  metadata?: Record<string, unknown> | null;
}

interface MyQrResponse {
  presence_sessions?: PresenceSession[];
}

function formatDate(value?: string | null) {
  if (!value) return '---';
  return new Date(value).toLocaleString('cs-CZ', { hour12: false });
}

function formatDuration(seconds?: number | null) {
  if (!seconds) return '---';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

export default function AktivitaPage() {
  const { toast } = useToast();
  const { data, isPending } = useQuery<MyQrResponse>({
    queryKey: ['my-qr', 'presence'],
    queryFn: () => apiClient<MyQrResponse>('/api/my_qr'),
  });

  const sessions = useMemo(() => data?.presence_sessions ?? [], [data?.presence_sessions]);

  return (
    <>
      <div className="space-y-6">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div>
            <p className="text-xs uppercase tracking-[0.35em] text-slate-500">Přítomnost</p>
            <h1 className="text-3xl font-semibold text-white mt-1">Moje aktivita</h1>
            <p className="text-slate-400 text-sm mt-2">Příchody a odchody z gymu podle skenů IN/OUT.</p>
          </div>
        </div>

        <section className="glass-panel rounded-3xl p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-white">Historie</h2>
            <p className="text-sm text-slate-400">{isPending ? 'Načítám...' : `${sessions.length} záznamů`}</p>
          </div>
          {isPending ? (
            <p className="text-slate-400 text-sm">Načítám...</p>
          ) : sessions.length === 0 ? (
            <p className="text-slate-400 text-sm">Žádné záznamy skenů.</p>
          ) : (
            <div className="space-y-3">
              {sessions.map((session) => (
                <div key={session.id} className="glass-subcard rounded-2xl p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-semibold text-lg text-white">
                        {session.last_direction === 'out' ? 'Odchod' : 'Příchod'}
                      </p>
                      <p className="text-xs uppercase tracking-[0.35em] text-slate-500">{session.status}</p>
                    </div>
                    <span
                      className={`px-3 py-1 rounded-full text-xs ${
                        session.ended_at ? 'bg-white/10 text-slate-200' : 'bg-emerald-500/20 text-emerald-200'
                      }`}
                    >
                      {session.ended_at ? 'Ukončeno' : 'Probíhá'}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-4 text-sm text-slate-300">
                    <p>Čas: {formatDate(session.started_at)}</p>
                    <p>Doba: {formatDuration(session.duration_seconds)}</p>
                  </div>
                  {session.notes && <p className="text-xs text-slate-400 whitespace-pre-line">{session.notes}</p>}
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
      <Toast toast={toast} />
    </>
  );
}
