'use client';

import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/apiClient';
import type { AdminCalcomSettings } from '@/types/admin';
import { CopyButton } from '@/components/copy-button';

export default function AdminIntegrationsPage() {
  const queryClient = useQueryClient();
  const settingsQuery = useQuery<AdminCalcomSettings>({
    queryKey: ['admin', 'calcom', 'settings'],
    queryFn: () => apiClient('/api/admin/calcom/settings'),
  });

  const [isEnabled, setIsEnabled] = useState(false);
  const [secret, setSecret] = useState('');
  const [embed, setEmbed] = useState('');

  useEffect(() => {
    if (settingsQuery.data) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setIsEnabled(settingsQuery.data.is_enabled);
      setSecret('');
      setEmbed(settingsQuery.data.embed_code ?? '');
    }
  }, [settingsQuery.data]);

  const updateMutation = useMutation({
    mutationFn: async (body: Record<string, unknown>) =>
      apiClient('/api/admin/calcom/settings', { method: 'POST', body: JSON.stringify(body) }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'calcom', 'settings'] });
      queryClient.invalidateQueries({ queryKey: ['admin', 'calcom', 'events'] });
      setSecret('');
    },
  });

  const defaultWebhookUrl = settingsQuery.data?.webhook_url ?? '';
  const adminWebhookUrl = settingsQuery.data?.admin_webhook_url ?? '';
  const webhookUrl = adminWebhookUrl || defaultWebhookUrl;

  const handleSave = () => {
    const payload: Record<string, unknown> = { is_enabled: isEnabled, embed_code: embed || null };
    if (secret.trim()) {
      payload.webhook_secret = secret.trim();
    }
    updateMutation.mutate(payload);
  };

  return (
    <div className="space-y-8">
      <div className="glass-panel rounded-3xl p-6 space-y-4">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Integrace</p>
            <h1 className="text-2xl font-semibold">Cal.com (rezervace)</h1>
            <p className="text-sm text-slate-400">
              Webhooky rezervací se zapisují do našeho systému. Aktivuj jen pokud máš licenci.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-slate-300">Cal.com webhooky</span>
            <button
              type="button"
              role="switch"
              aria-checked={isEnabled}
              aria-label="Přepnout Cal.com webhooky"
              onClick={() => setIsEnabled((prev) => !prev)}
              className={`relative inline-flex h-7 w-12 items-center rounded-full transition ${
                isEnabled ? 'bg-emerald-400/80' : 'bg-white/20'
              }`}
            >
              <span
                className={`inline-block h-5 w-5 transform rounded-full bg-white transition ${
                  isEnabled ? 'translate-x-6' : 'translate-x-1'
                }`}
              />
            </button>
          </div>
        </div>

        {!isEnabled ? (
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">
            Zapni integraci Cal.com, abys viděl a upravil Webhook URL, secret a embed.
          </div>
        ) : (
          <>
            <div className="grid gap-4 md:grid-cols-2">
              <label className="flex flex-col gap-2">
                <div className="flex items-center justify-between text-sm text-slate-300">
                  <span>Webhook URL</span>
                  <CopyButton value={webhookUrl} />
                </div>
                <input
                  readOnly
                  value={webhookUrl}
                  className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white"
                />
                <span className="text-xs text-slate-500">
                  Zkopíruj do Cal.com → Webhooks → Subscriber URL. Link je svázaný s tímto admin účtem.
                </span>
              </label>
              <label className="flex flex-col gap-2">
                <span className="text-sm text-slate-300">Secret</span>
                <input
                  type="password"
                  placeholder={settingsQuery.data?.has_secret ? '•••••••• (nastaveno)' : 'Zadej nový secret'}
                  value={secret}
                  onChange={(e) => setSecret(e.target.value)}
                  className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white"
                />
                <span className="text-xs text-slate-500">
                  Bude uložen u nás a používá se pro ověření HMAC podpisu Cal.com.
                </span>
              </label>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
              <label className="flex flex-col gap-2 md:col-span-2">
                <div className="flex items-center justify-between text-sm text-slate-300">
                  <span>Embed nebo URL z Cal.com</span>
                  <CopyButton value={embed} />
                </div>
                <input
                  value={embed}
                  onChange={(e) => setEmbed(e.target.value)}
                  placeholder="https://cal.com/tvoje-udalost nebo embed kód"
                  className="w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white"
                />
                <span className="text-xs text-slate-500">
                  Ulož embed z Cal.com nebo přímý odkaz na event (např. http://localhost:3200/admin/30min). Klientům se
                  zobrazí na stránce Rezervace.
                </span>
              </label>
            </div>

            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-end">
              <div className="flex items-center gap-3">
                <button
                  onClick={handleSave}
                  disabled={updateMutation.isPending}
                  className="secondary-button px-6 py-3 text-sm disabled:opacity-60"
                >
                  {updateMutation.isPending ? 'Ukládám...' : 'Uložit nastavení'}
                </button>
                {updateMutation.isError && (
                  <span className="text-sm text-rose-300">Uložení selhalo, zkus to prosím znovu.</span>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
