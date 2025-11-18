'use client';

import { useEffect, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { ownerApiClient } from '@/lib/apiClient';
import { Toast, useToast } from '@/components/toast';
import { defaultBranding } from '@/types/branding';
import { useBranding } from '@/components/branding-context';

const apiSchema = z.object({
  brand_name: z.string(),
  console_name: z.string(),
  tagline: z.string().nullable(),
  support_email: z.string().nullable(),
  primary_color: z.string(),
  footer_text: z.string().nullable(),
  logo_url: z.string().nullable(),
});

type BrandingApiResponse = z.infer<typeof apiSchema>;

const formSchema = z.object({
  brandName: z.string().min(2).max(100),
  consoleName: z.string().min(2).max(100),
  tagline: z.string().max(255).optional(),
  supportEmail: z.string().email().optional(),
  primaryColor: z.string().regex(/^#[0-9a-fA-F]{6}$/, 'Zadej hex barvu ve formátu #RRGGBB'),
  footerText: z.string().max(255).optional(),
  logoUrl: z
    .string()
    .optional()
    .refine(
      (value) => !value || value.startsWith('/') || /^https?:\/\//i.test(value),
      'Logo musí být absolutní nebo relativní URL'
    ),
});

type BrandingFormValues = z.infer<typeof formSchema>;

function normalizeApi(data: BrandingApiResponse): BrandingFormValues {
  return {
    brandName: data.brand_name ?? defaultBranding.brandName,
    consoleName: data.console_name ?? defaultBranding.consoleName,
    tagline: data.tagline ?? undefined,
    supportEmail: data.support_email ?? undefined,
    primaryColor: data.primary_color ?? defaultBranding.primaryColor,
    footerText: data.footer_text ?? undefined,
    logoUrl: data.logo_url ?? undefined,
  };
}

function serializeForm(values: BrandingFormValues) {
  return {
    brand_name: values.brandName,
    console_name: values.consoleName,
    tagline: values.tagline?.trim() || null,
    support_email: values.supportEmail?.trim() || null,
    primary_color: values.primaryColor,
    footer_text: values.footerText?.trim() || null,
    logo_url: values.logoUrl?.trim() || null,
  };
}

export default function BrandingPage() {
  const { toast, showToast } = useToast();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const brandingContext = useBranding();

  const { data, isPending, refetch } = useQuery({
    queryKey: ['owner-branding'],
    queryFn: async () => {
      const response = await ownerApiClient<BrandingApiResponse>('/api/owner/branding');
      return apiSchema.parse(response);
    },
  });

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting, isDirty },
    reset,
    watch,
    setValue,
  } = useForm<BrandingFormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: normalizeApi(
      data ?? {
        brand_name: brandingContext.brandName,
        console_name: brandingContext.consoleName,
        tagline: brandingContext.tagline ?? null,
        support_email: brandingContext.supportEmail ?? null,
        primary_color: brandingContext.primaryColor,
        footer_text: brandingContext.footerText ?? null,
        logo_url: brandingContext.logoUrl ?? null,
      }
    ),
  });

  useEffect(() => {
    if (data) {
      reset(normalizeApi(data));
    }
  }, [data, reset]);

  const preview = watch();

  async function onSubmit(values: BrandingFormValues) {
    try {
      await ownerApiClient('/api/owner/branding', {
        method: 'PUT',
        body: JSON.stringify(serializeForm(values)),
      });
      showToast('Branding uložen');
      await refetch();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Chyba při ukládání', 'error');
    }
  }

  async function handleLogoUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const formData = new FormData();
      formData.append('file', file);
      const response = await ownerApiClient<{ logo_url: string; content_type: string; size_bytes: number }>('/api/owner/logo-upload', {
        method: 'POST',
        body: formData,
      });
      setValue('logoUrl', response.logo_url, { shouldDirty: true, shouldValidate: true });
      showToast('Logo nahráno');
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Chyba při nahrávání', 'error');
    } finally {
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  }

  function handleResetLogo() {
    setValue('logoUrl', undefined, { shouldDirty: true, shouldValidate: true });
    showToast('Logo odstraněno');
  }

  return (
    <>
      <div className="grid gap-8 lg:grid-cols-2">
        <section className="glass-panel rounded-3xl p-6 sm:p-10 space-y-6">
          <div>
            <p className="text-xs uppercase tracking-[0.35em] text-emerald-200/70">Global branding</p>
            <h1 className="text-3xl font-semibold tracking-tight text-white">Vzhled platformy</h1>
            <p className="text-slate-400 mt-2 text-sm">Uprav název platformy, konzole, barvy i logo.</p>
          </div>
          {isPending ? (
            <p className="text-slate-400">Načítám...</p>
          ) : (
            <form className="space-y-5" onSubmit={handleSubmit(onSubmit)}>
              <div>
                <label className="text-sm text-slate-300 block mb-1.5">Brand name</label>
                <input className="input-field" placeholder="Název značky" {...register('brandName')} />
                {errors.brandName && <p className="text-sm text-rose-300 mt-1">{errors.brandName.message}</p>}
              </div>
              <div>
                <label className="text-sm text-slate-300 block mb-1.5">Console name</label>
                <input className="input-field" placeholder="Název konzole" {...register('consoleName')} />
                {errors.consoleName && <p className="text-sm text-rose-300 mt-1">{errors.consoleName.message}</p>}
              </div>
              <div>
                <label className="text-sm text-slate-300 block mb-1.5">Tagline</label>
                <input className="input-field" placeholder="Krátký popis" {...register('tagline')} />
                {errors.tagline && <p className="text-sm text-rose-300 mt-1">{errors.tagline.message}</p>}
              </div>
              <div>
                <label className="text-sm text-slate-300 block mb-1.5">Support email</label>
                <input className="input-field" placeholder="support@example.com" {...register('supportEmail')} />
                {errors.supportEmail && <p className="text-sm text-rose-300 mt-1">{errors.supportEmail.message}</p>}
              </div>
              <div>
                <label className="text-sm text-slate-300 block mb-1.5">Primary color</label>
                <div className="flex gap-3">
                  <input className="input-field" placeholder="#0EA5E9" {...register('primaryColor')} />
                  <div
                    className="w-16 rounded-2xl border border-white/10"
                    style={{ background: preview.primaryColor || defaultBranding.primaryColor }}
                  />
                </div>
                {errors.primaryColor && <p className="text-sm text-rose-300 mt-1">{errors.primaryColor.message}</p>}
              </div>
              <div>
                <label className="text-sm text-slate-300 block mb-1.5">Footer text</label>
                <input className="input-field" placeholder="© 2025 ..." {...register('footerText')} />
                {errors.footerText && <p className="text-sm text-rose-300 mt-1">{errors.footerText.message}</p>}
              </div>
              <div className="space-y-2">
                <label className="text-sm text-slate-300 block">Logo URL</label>
                <input className="input-field" placeholder="/static/branding/logo.png" {...register('logoUrl')} />
                {errors.logoUrl && <p className="text-sm text-rose-300 mt-1">{errors.logoUrl.message}</p>}
                <div className="flex flex-wrap gap-3">
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    Nahrát logo
                  </button>
                  <button type="button" className="text-sm text-slate-400 hover:text-white" onClick={handleResetLogo}>
                    Resetovat
                  </button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/png,image/jpeg,image/svg+xml"
                    className="hidden"
                    onChange={handleLogoUpload}
                  />
                </div>
              </div>
              <button type="submit" className="accent-button w-full" disabled={isSubmitting || isPending}>
                {isSubmitting ? 'Ukládám...' : isDirty ? 'Uložit změny' : 'Uložit'}
              </button>
            </form>
          )}
        </section>
        <section className="glass-panel rounded-3xl p-6 sm:p-10 text-white space-y-6">
          <div className="flex items-center gap-4">
            {preview.logoUrl ? (
              <img src={preview.logoUrl} alt="Logo preview" className="h-14 w-14 rounded-2xl object-contain border border-white/5 bg-white/5 p-2" />
            ) : (
              <div className="h-14 w-14 rounded-2xl border border-dashed border-white/20 flex items-center justify-center text-xs text-slate-400">
                Logo
              </div>
            )}
            <div>
              <p className="text-xs uppercase tracking-[0.35em] text-emerald-200/70">{preview.consoleName || defaultBranding.consoleName}</p>
              <h2 className="text-2xl font-semibold">{preview.brandName || defaultBranding.brandName}</h2>
            </div>
          </div>
          {preview.tagline && <p className="text-slate-300">{preview.tagline}</p>}
          <div className="rounded-2xl p-6 border border-white/10" style={{ background: `${preview.primaryColor || defaultBranding.primaryColor}15` }}>
            <p className="text-sm text-slate-200">Ukázka tlačítek</p>
            <div className="flex gap-4 mt-4">
              <button className="accent-button" style={{ background: preview.primaryColor || defaultBranding.primaryColor }}>
                Primární
              </button>
              <button className="secondary-button">Sekundární</button>
            </div>
          </div>
          <div className="rounded-2xl border border-white/10 p-4 text-sm text-slate-300">
            <p>{preview.footerText || defaultBranding.footerText}</p>
            {preview.supportEmail && (
              <p className="mt-2">
                Podpora:{' '}
                <a href={`mailto:${preview.supportEmail}`} className="text-white underline">
                  {preview.supportEmail}
                </a>
              </p>
            )}
          </div>
        </section>
      </div>
      <Toast toast={toast} />
    </>
  );
}
