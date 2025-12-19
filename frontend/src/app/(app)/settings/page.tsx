'use client';

import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/apiClient';
import { Toast, useToast } from '@/components/toast';
import { z, ZodType } from 'zod';

interface UserInfoResponse {
  user_id: number;
  email: string;
  name: string;
  first_name?: string | null;
  last_name?: string | null;
  phone_number?: string | null;
  created_at: string;
  qr_count: number;
  is_admin: boolean;
}

const profileSchema = z.object({
  first_name: z.string().trim().min(1, 'Zadejte jméno').max(60, 'Max. 60 znaků'),
  last_name: z.string().trim().min(1, 'Zadejte příjmení').max(80, 'Max. 80 znaků'),
  email: z.string().trim().email('Neplatný e-mail'),
  phone_number: z
    .string()
    .trim()
    .max(40, 'Max. 40 znaků')
    .refine((value) => value === '' || value.length >= 5, 'Zadejte platné číslo')
    .refine((value) => value === '' || /\d/.test(value), 'Telefon musí obsahovat číslice'),
});

const passwordSchema = z
  .object({
    current_password: z.string().min(6, 'Min. 6 znaků'),
    new_password: z.string().min(6, 'Min. 6 znaků'),
    confirm_password: z.string().min(6, 'Min. 6 znaků'),
  })
  .refine((values) => values.new_password === values.confirm_password, {
    message: 'Hesla se musí shodovat',
    path: ['confirm_password'],
  });

type PasswordFormValues = z.infer<typeof passwordSchema>;
type ProfileFormValues = z.infer<typeof profileSchema>;

export default function SettingsPage() {
  const { toast, showToast } = useToast();
  const queryClient = useQueryClient();
  const { data, isPending } = useQuery<UserInfoResponse>({
    queryKey: ['user-info'],
    queryFn: () => apiClient('/api/user/info'),
  });

  const {
    register: registerPassword,
    handleSubmit: handlePasswordSubmit,
    formState: { errors: passwordErrors, isSubmitting: isPasswordSubmitting },
    reset: resetPasswordForm,
  } = useForm<PasswordFormValues>({ resolver: zodResolver(passwordSchema) });

  const {
    register: registerProfile,
    handleSubmit: handleProfileSubmit,
    formState: { errors: profileErrors, isSubmitting: isProfileSubmitting },
    reset: resetProfileForm,
  } = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
  });

  useEffect(() => {
    if (!data) return;
    const [first, ...rest] = data.name?.split(' ') ?? [''];
    resetProfileForm({
      first_name: data.first_name ?? first ?? '',
      last_name: data.last_name ?? rest.join(' ') ?? '',
      email: data.email,
      phone_number: data.phone_number ?? '',
    });
  }, [data, resetProfileForm]);

  async function onChangePassword(values: PasswordFormValues) {
    try {
      await apiClient('/api/user/change-password', {
        method: 'POST',
        body: JSON.stringify({
          current_password: values.current_password,
          new_password: values.new_password,
        }),
      });
      showToast('Heslo bylo změněno');
      resetPasswordForm();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Chyba při změně hesla', 'error');
    }
  }

  async function onUpdateProfile(values: ProfileFormValues) {
    const normalizedPhone = values.phone_number.trim();
    try {
      await apiClient('/api/user/profile', {
        method: 'PUT',
        body: JSON.stringify({
          ...values,
          phone_number: normalizedPhone ? normalizedPhone : null,
        }),
      });
      showToast('Profil byl uložen');
      await queryClient.invalidateQueries({ queryKey: ['user-info'] });
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Chyba při uložení profilu', 'error');
    }
  }

  return (
    <>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
        <section className="glass-panel rounded-3xl p-6 space-y-6 shadow-xl shadow-black/20">
          <header className="space-y-1">
            <p className="text-xs uppercase tracking-[0.35em] text-slate-500">Profil</p>
            <h2 className="text-2xl font-semibold text-white">Osobní údaje</h2>
            <p className="text-slate-400 text-sm">Aktualizuj údaje, které se propisují do celé aplikace.</p>
          </header>
          {isPending && !data ? (
            <p className="text-slate-500 text-sm">Načítám údaje...</p>
          ) : (
            <form className="space-y-5" onSubmit={handleProfileSubmit(onUpdateProfile)}>
              <div className="grid gap-5 md:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-[11px] uppercase tracking-[0.25em] text-slate-500">Jméno</label>
                  <input
                    type="text"
                    className="input-field bg-slate-900 text-white border border-white/10 h-12"
                    placeholder="Jméno"
                    {...registerProfile('first_name')}
                    disabled={isPending}
                  />
                  {profileErrors.first_name && (
                    <p className="text-sm text-rose-300">{profileErrors.first_name.message}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <label className="text-[11px] uppercase tracking-[0.25em] text-slate-500">Příjmení</label>
                  <input
                    type="text"
                    className="input-field bg-slate-900 text-white border border-white/10 h-12"
                    placeholder="Příjmení"
                    {...registerProfile('last_name')}
                    disabled={isPending}
                  />
                  {profileErrors.last_name && (
                    <p className="text-sm text-rose-300">{profileErrors.last_name.message}</p>
                  )}
                </div>
              </div>
              <div className="grid gap-5 md:grid-cols-2">
                <div className="space-y-2">
                  <label className="text-[11px] uppercase tracking-[0.25em] text-slate-500">Primární email</label>
                  <input
                    type="email"
                    className="input-field bg-slate-900 text-white border border-white/10 h-12"
                    placeholder="např. osoba@example.com"
                    {...registerProfile('email')}
                    disabled={isPending}
                  />
                  {profileErrors.email && (
                    <p className="text-sm text-rose-300">{profileErrors.email.message}</p>
                  )}
                </div>
                <div className="space-y-2">
                  <label className="text-[11px] uppercase tracking-[0.25em] text-slate-500">Telefon</label>
                  <input
                    type="tel"
                    className="input-field bg-slate-900 text-white border border-white/10 h-12"
                    placeholder="+420 123 456 789"
                    {...registerProfile('phone_number')}
                    disabled={isPending}
                  />
                  {profileErrors.phone_number && (
                    <p className="text-sm text-rose-300">{profileErrors.phone_number.message}</p>
                  )}
                </div>
              </div>
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pt-2 border-t border-white/5">
                <p className="text-xs text-slate-500">
                  Údaje používáme pro komunikaci, fakturaci a identifikaci při návštěvách.
                </p>
                <button type="submit" className="accent-button px-10 w-full sm:w-auto" disabled={isProfileSubmitting || isPending}>
                  {isProfileSubmitting ? 'Ukládám...' : 'Uložit profil'}
                </button>
              </div>
            </form>
          )}
        </section>

        <section className="glass-panel rounded-3xl p-6 space-y-6 shadow-xl shadow-black/20">
          <header className="space-y-1">
            <p className="text-xs uppercase tracking-[0.35em] text-slate-500">Bezpečnost</p>
            <h2 className="text-2xl font-semibold text-white">Změna hesla</h2>
            <p className="text-slate-400 text-sm">Udržuj svůj účet v bezpečí pravidelnou změnou hesla.</p>
          </header>
          <form className="space-y-4" onSubmit={handlePasswordSubmit(onChangePassword)}>
            <div className="space-y-2">
              <label className="text-[11px] uppercase tracking-[0.25em] text-slate-500">Aktuální heslo</label>
              <input
                type="password"
                placeholder="Aktuální heslo"
                className="input-field bg-slate-900 text-white border border-white/10 h-12"
                {...registerPassword('current_password')}
              />
              {passwordErrors.current_password && (
                <p className="text-sm text-rose-300">{passwordErrors.current_password.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <label className="text-[11px] uppercase tracking-[0.25em] text-slate-500">Nové heslo</label>
              <input
                type="password"
                placeholder="Nové heslo"
                className="input-field bg-slate-900 text-white border border-white/10 h-12"
                {...registerPassword('new_password')}
              />
              {passwordErrors.new_password && (
                <p className="text-sm text-rose-300">{passwordErrors.new_password.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <label className="text-[11px] uppercase tracking-[0.25em] text-slate-500">Potvrzení</label>
              <input
                type="password"
                placeholder="Potvrď nové heslo"
                className="input-field bg-slate-900 text-white border border-white/10 h-12"
                {...registerPassword('confirm_password')}
              />
              {passwordErrors.confirm_password && (
                <p className="text-sm text-rose-300">{passwordErrors.confirm_password.message}</p>
              )}
            </div>
            <div className="pt-2 border-t border-white/5">
              <button type="submit" className="accent-button px-10 w-full sm:w-auto" disabled={isPasswordSubmitting}>
                {isPasswordSubmitting ? 'Ukládám...' : 'Uložit heslo'}
              </button>
            </div>
          </form>
        </section>
      </div>
      <Toast toast={toast} />
    </>
  );
}
