'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useBranding } from '@/components/branding-context';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/apiClient';
import { Toast, useToast } from '@/components/toast';
import type { AdminCalcomBooking } from '@/types/admin';
import { CopyJson } from '@/components/copy-json';
import { getCalApi } from '@calcom/embed-react';

type PublicProvider = {
  admin_id: number;
  name: string;
  email: string;
  embed_code?: string | null;
  embed_is_url?: boolean;
  embed_origin?: string | null;
  embed_path?: string | null;
};

function formatBookingRange(start?: string | null, end?: string | null) {
  const s = start ? new Date(start) : null;
  const e = end ? new Date(end) : null;
  if (!s || Number.isNaN(s.getTime())) return '—';
  const startLabel = s.toLocaleString('cs-CZ', {
    hour: '2-digit',
    minute: '2-digit',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
  if (!e || Number.isNaN(e.getTime())) return startLabel;
  const sameDay = s.toDateString() === e.toDateString();
  const endLabel = e.toLocaleString('cs-CZ', {
    hour: '2-digit',
    minute: '2-digit',
    ...(sameDay ? {} : { day: '2-digit', month: '2-digit', year: 'numeric' }),
  });
  return sameDay ? `${startLabel} – ${endLabel}` : `${startLabel} → ${endLabel}`;
}

function bookingStatusClass(status?: string | null) {
  const s = (status || '').toLowerCase();
  if (s.includes('cancel')) return 'bg-rose-500/20 text-rose-100';
  if (s.includes('resched')) return 'bg-amber-500/20 text-amber-100';
  if (s.includes('created')) return 'bg-emerald-500/20 text-emerald-100';
  return 'bg-slate-500/20 text-slate-100';
}

function relativeStartLabel(start?: string | null) {
  if (!start) return '—';
  const d = new Date(start);
  if (Number.isNaN(d.getTime())) return '—';
  const now = new Date();
  const diffMs = d.getTime() - now.getTime();
  const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return 'Dnes';
  if (diffDays === 1) return 'Zítra';
  if (diffDays > 1) return `Za ${diffDays} dny`;
  if (diffDays === -1) return 'Včera';
  return `Před ${Math.abs(diffDays)} dny`;
}

function bookingOpenClosed(status?: string | null, start?: string | null, end?: string | null) {
  const s = (status || '').toLowerCase();
  const isCancelled = s.includes('cancel');
  const now = Date.now();
  const endMs = end ? new Date(end).getTime() : NaN;
  const startMs = start ? new Date(start).getTime() : NaN;
  const reference = Number.isNaN(endMs) ? startMs : endMs;
  const inPast = Number.isNaN(reference) ? false : reference < now;
  const isOpen = !isCancelled && !inPast;
  return {
    label: isOpen ? 'open' : 'closed',
    className: isOpen ? 'bg-emerald-500/15 text-emerald-100' : 'bg-slate-500/30 text-slate-100',
    isOpen,
  };
}

export default function RezervacePage() {
  const branding = useBranding();
  const router = useRouter();
  const { toast, showToast } = useToast();
  const [isAdmin, setIsAdmin] = useState(false);
  const [hasToken, setHasToken] = useState(false);
  const [authReady, setAuthReady] = useState(false);
  const [showAdminOpenOnly, setShowAdminOpenOnly] = useState(true);
  const [showUserOpenOnly, setShowUserOpenOnly] = useState(true);

  const publicCalcom = useQuery({
    queryKey: ['calcom-public'],
    queryFn: () =>
      apiClient<{ is_enabled: boolean; embed_code?: string | null; providers?: PublicProvider[] }>(
        '/api/calcom/public'
      ),
  });

  const providers: PublicProvider[] = useMemo(() => publicCalcom.data?.providers ?? [], [publicCalcom.data]);
  const embedEnabled = Boolean(publicCalcom.data?.is_enabled);
  const availableProviders = providers.filter((p) => (p.embed_code ?? '').trim().length > 0);

  const [selectedProviderId, setSelectedProviderId] = useState<number | null>(
    availableProviders.length ? availableProviders[0].admin_id : null
  );

  const selectedProvider =
    availableProviders.find((p) => p.admin_id === selectedProviderId) || availableProviders[0] || null;
  const canReserve = embedEnabled && availableProviders.length > 0;

  const embedInfo = useMemo(() => {
    if (!selectedProvider) return null;
    const raw = (selectedProvider.embed_code || '').trim();
    if (!raw) return null;
    const origin = selectedProvider.embed_origin || (raw.startsWith('http') ? new URL(raw).origin : null);
    const path =
      selectedProvider.embed_path || (raw.startsWith('http') ? new URL(raw).pathname.replace(/^\//, '') : raw);
    if (!origin || !path) return null;
    return { origin, path };
  }, [selectedProvider]);

  const calNamespace = useMemo(
    () => (selectedProvider ? `cal-provider-${selectedProvider.admin_id}` : 'cal-provider'),
    [selectedProvider]
  );
  const calRef = useRef<any>(null);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    setIsAdmin(sessionStorage.getItem('is_admin') === 'true');
    setHasToken(Boolean(sessionStorage.getItem('access_token')));
    setAuthReady(true);
  }, []);

  useEffect(() => {
    if (!authReady) return;
    if (!branding.reservationsEnabled && !isAdmin) {
      router.replace('/dashboard');
    }
  }, [authReady, branding.reservationsEnabled, router, isAdmin]);

  const adminBookingsQuery = useQuery<AdminCalcomBooking[]>({
    queryKey: ['admin', 'calcom', 'bookings', 'rezervace'],
    queryFn: () => apiClient('/api/admin/calcom/bookings'),
    enabled: authReady && isAdmin,
  });

  const myBookingsQuery = useQuery<AdminCalcomBooking[]>({
    queryKey: ['calcom', 'my-bookings'],
    queryFn: () => apiClient('/api/calcom/my-bookings'),
    enabled: authReady && !isAdmin && hasToken,
  });

  useEffect(() => {
    if (!embedInfo) return;
    let cancelled = false;
    (async () => {
      try {
        const cal = await getCalApi({ namespace: calNamespace, embedJsUrl: `${embedInfo.origin}/embed/embed.js` });
        if (cancelled) return;
        calRef.current = cal;
        cal('ui', { layout: 'month_view' });
      } catch (err) {
        console.error('Cal embed init failed', err);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [embedInfo, calNamespace]);

  const filteredAdminBookings = (adminBookingsQuery.data ?? []).filter((booking) => {
    if (!showAdminOpenOnly) return true;
    return bookingOpenClosed(booking.status, booking.start_time, booking.end_time).isOpen;
  });
  const filteredUserBookings = (myBookingsQuery.data ?? []).filter((booking) => {
    if (!showUserOpenOnly) return true;
    return bookingOpenClosed(booking.status, booking.start_time, booking.end_time).isOpen;
  });

  const sortByStartAscending = (list: AdminCalcomBooking[]) =>
    list.slice().sort((a, b) => {
      const ta = a.start_time ? new Date(a.start_time).getTime() : Infinity;
      const tb = b.start_time ? new Date(b.start_time).getTime() : Infinity;
      if (Number.isNaN(ta) && Number.isNaN(tb)) return 0;
      if (Number.isNaN(ta)) return 1;
      if (Number.isNaN(tb)) return -1;
      return ta - tb;
    });

  const sortedAdminBookings = sortByStartAscending(filteredAdminBookings);
  const sortedUserBookings = sortByStartAscending(filteredUserBookings);

  const handleReserve = () => {
    if (!selectedProvider || !embedInfo) {
      showToast('Tento trenér nemá uložený platný Cal.com odkaz.', 'error');
      return;
    }
    // Cal.com embed umí automaticky otevřít pop-up na prvek s data-cal-*.
    // Pokud embed ještě není inicializovaný, spadneme na fallback nové karty.
    if (!calRef.current) {
      window.open(`${embedInfo.origin}/${embedInfo.path}`, '_blank', 'noopener,noreferrer');
    }
  };

  if (!authReady) {
    return null;
  }
  if (!branding.reservationsEnabled && !isAdmin) {
    return null;
  }

  return (
    <div className="glass-panel rounded-3xl p-6 sm:p-10 text-white space-y-6">
      <div>
        <p className="text-xs uppercase tracking-[0.35em] text-emerald-200/70">Rezervace</p>
        <h1 className="text-3xl font-semibold tracking-tight">Kalendář a rezervace</h1>
        <p className="text-slate-300 mt-2 text-sm">
          Tady najdeš přehled svých rezervací tréninků. Po připojení Cal.com se zde objeví dostupné termíny a potvrzení.
          {isAdmin && !branding.reservationsEnabled && ' (zatím vypnuto – povol v owner konzoli)'}
        </p>
      </div>

      <div className="rounded-2xl border border-white/10 bg-white/5 p-6 text-slate-200 space-y-4">
        {!embedEnabled && !branding.reservationsEnabled && (
          <>
            <p className="font-semibold">Rezervační systém není aktivní</p>
            <p className="text-sm text-slate-400">Po zapnutí uvidíš kalendář a své rezervace.</p>
          </>
        )}

        {canReserve ? (
          <>
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div className="flex flex-col gap-2 md:flex-row md:items-center md:gap-3 flex-1">
                <label className="text-sm text-slate-300">Vyber trenéra</label>
                <select
                  value={selectedProviderId ?? ''}
                  onChange={(e) => setSelectedProviderId(Number(e.target.value))}
                  className="rounded-2xl border border-white/10 bg-white/5 px-3 py-2 text-sm text-white"
                >
                  {availableProviders.map((p) => (
                    <option key={p.admin_id} value={p.admin_id}>
                      {p.name} ({p.email})
                    </option>
                  ))}
                </select>
              </div>
              <button
                className="secondary-button px-4 py-2 text-sm disabled:opacity-60"
                onClick={handleReserve}
                disabled={!selectedProvider || !embedInfo}
                data-cal-namespace={calNamespace}
                data-cal-link={embedInfo?.path ?? ''}
                data-cal-origin={embedInfo?.origin ?? ''}
                data-cal-config='{"layout":"month_view"}'
              >
                Rezervovat
              </button>
            </div>
            <p className="text-sm text-slate-400">Po kliknutí se otevře pop-up s kalendářem vybraného trenéra.</p>
          </>
        ) : (
          <>
            <p className="font-semibold">Zatím není k dispozici žádný kalendář.</p>
            <p className="text-sm text-slate-400">
              Po zapnutí rezervačního systému v konzoli správce se zde objeví tvé termíny a nové rezervace. Administrátoři
              vidí tuto stránku vždy, aby mohli ověřit stav integrace.
            </p>
          </>
        )}
      </div>

      {isAdmin && (
        <div className="rounded-2xl border border-white/10 bg-white/5 p-6 text-slate-200 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-white">Rezervace (admin)</h3>
            <button
              type="button"
              role="switch"
              aria-checked={showAdminOpenOnly}
              onClick={() => setShowAdminOpenOnly((v) => !v)}
              className={`relative inline-flex h-7 w-14 items-center rounded-full transition ${
                showAdminOpenOnly ? 'bg-emerald-400/80' : 'bg-white/20'
              }`}
            >
              <span
                className={`inline-block h-5 w-5 transform rounded-full bg-white transition ${
                  showAdminOpenOnly ? 'translate-x-7' : 'translate-x-2'
                }`}
              />
              <span className="absolute left-2 text-[11px] uppercase tracking-wide text-slate-900/70">
                {showAdminOpenOnly ? 'open' : ''}
              </span>
            </button>
          </div>
          {adminBookingsQuery.isPending && <p className="text-sm text-slate-400">Načítám rezervace...</p>}
          {!adminBookingsQuery.isPending && sortedAdminBookings.length === 0 && (
            <p className="text-sm text-slate-400">Zatím žádné rezervace z webhooks.</p>
          )}
          <div className="space-y-2">
            {sortedAdminBookings.map((booking) => (
              <div key={`${booking.id}-${booking.booking_id ?? booking.uid ?? 'none'}`} className="glass-subcard rounded-2xl p-4 text-sm space-y-1">
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1">
                    <p className="font-semibold text-white">{booking.title || 'Rezervace'}</p>
                    <p className="text-xs text-slate-400">{formatBookingRange(booking.start_time, booking.end_time)}</p>
                    {booking.location && <p className="text-xs text-slate-300">Místo: {booking.location}</p>}
                    <p className="text-xs text-slate-300">
                      Klient: {booking.attendee_name || '---'} {booking.attendee_email ? `(${booking.attendee_email})` : ''}
                      {booking.attendee_phone ? ` · ${booking.attendee_phone}` : ''}
                    </p>
                  </div>
                  <div className="text-right text-xs text-slate-400 space-y-1">
                    <div className="flex items-center justify-end gap-2">
                      {(() => {
                        const state = bookingOpenClosed(booking.status, booking.start_time, booking.end_time);
                        return (
                          <span className={`px-2 py-1 rounded-full ${state.className}`}>
                            {state.label}
                          </span>
                        );
                      })()}
                    </div>
                    <p className="text-[11px] text-slate-400">{relativeStartLabel(booking.start_time)}</p>
                    <div>
                      <p>{booking.organizer_name || 'Organizátor neznámý'}</p>
                      <p className="text-[11px] text-slate-500">{booking.organizer_email || ''}</p>
                    </div>
                  </div>
                </div>
                {booking.history && booking.history.length > 0 && (
                  <div className="pt-1 space-y-1 text-[11px] text-slate-400">
                    {booking.history
                      .slice()
                      .sort((a, b) => (b.received_at || '').localeCompare(a.received_at || ''))
                      .map((h, idx) => (
                        <div key={idx} className="flex flex-wrap items-center gap-2">
                          <span className={`px-2 py-0.5 rounded-full ${bookingStatusClass(h.status)}`}>
                            {h.status || h.event_type || 'stav'}
                          </span>
                          <span>{h.received_at ? new Date(h.received_at).toLocaleString('cs-CZ') : ''}</span>
                          {(() => {
                            const statusText = (h.status || h.event_type || '').toLowerCase();
                            let detail: string | null = null;
                            if (statusText.includes('cancel')) {
                              detail = h.cancel_reason || h.notes || null;
                            } else if (statusText.includes('resched')) {
                              detail = h.reschedule_reason || h.notes || null;
                            } else if (statusText.includes('create')) {
                              detail = h.notes || null;
                            } else {
                              detail = h.notes || h.reschedule_reason || h.cancel_reason || null;
                            }
                            return detail ? <span className="text-slate-300">{detail}</span> : null;
                          })()}
                          {h.raw_payload && <CopyJson value={h.raw_payload} label="JSON" />}
                        </div>
                      ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {!isAdmin && hasToken && (
        <div className="rounded-2xl border border-white/10 bg-white/5 p-6 text-slate-200 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-white">Moje rezervace</h3>
            <button
              type="button"
              role="switch"
              aria-checked={showUserOpenOnly}
              onClick={() => setShowUserOpenOnly((v) => !v)}
              className={`relative inline-flex h-7 w-14 items-center rounded-full transition ${
                showUserOpenOnly ? 'bg-emerald-400/80' : 'bg-white/20'
              }`}
            >
              <span
                className={`inline-block h-5 w-5 transform rounded-full bg-white transition ${
                  showUserOpenOnly ? 'translate-x-7' : 'translate-x-2'
                }`}
              />
              <span className="absolute left-2 text-[11px] uppercase tracking-wide text-slate-900/70">
                {showUserOpenOnly ? 'open' : ''}
              </span>
            </button>
          </div>
          {myBookingsQuery.isPending && <p className="text-sm text-slate-400">Načítám rezervace...</p>}
          {!myBookingsQuery.isPending && sortedUserBookings.length === 0 && (
            <p className="text-sm text-slate-400">
              Nemáš zatím žádné rezervace z Cal.com. Po vytvoření se tady zobrazí termín a trenér.
            </p>
          )}
          <div className="space-y-2">
            {sortedUserBookings.map((booking) => (
              <div key={`${booking.id}-${booking.booking_id ?? booking.uid ?? 'none'}`} className="glass-subcard rounded-2xl p-4 text-sm space-y-1">
                <div className="flex items-start justify-between gap-3">
                  <div className="space-y-1">
                    <p className="font-semibold text-white">
                      {booking.title || 'Rezervace'}
                    </p>
                    <p className="text-xs text-slate-400">{formatBookingRange(booking.start_time, booking.end_time)}</p>
                    {booking.location && <p className="text-xs text-slate-300">Místo: {booking.location}</p>}
                  </div>
                  <div className="text-right text-xs text-slate-400 space-y-1">
                    <div className="flex items-center justify-end gap-2">
                      {(() => {
                        const state = bookingOpenClosed(booking.status, booking.start_time, booking.end_time);
                        return (
                          <span className={`px-2 py-1 rounded-full ${state.className}`}>
                            {state.label}
                          </span>
                        );
                      })()}
                    </div>
                    <p className="text-[11px] text-slate-400">{relativeStartLabel(booking.start_time)}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <Toast toast={toast} />
    </div>
  );
}
