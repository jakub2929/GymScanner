'use client';

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/apiClient';
import { Toast, useToast } from '@/components/toast';
import { z } from 'zod';

interface UserInfoResponse {
  user_id: number;
  email: string;
  name: string;
  created_at: string;
  qr_count: number;
  is_admin: boolean;
}

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

export default function SettingsPage() {
  const { toast, showToast } = useToast();
  const { data, isPending } = useQuery<UserInfoResponse>({
    queryKey: ['user-info'],
    queryFn: () => apiClient('/api/user/info'),
  });

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset,
  } = useForm<PasswordFormValues>({ resolver: zodResolver(passwordSchema) });

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
      reset();
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Chyba při změně hesla', 'error');
    }
  }

  return (
    <>
      <div className="grid lg:grid-cols-2 gap-6">
        <section className="surface-card p-6 space-y-4">
          <h2 className="text-2xl font-semibold text-slate-900">Informace o účtu</h2>
          {isPending ? (
            <p className="text-slate-500">Načítám...</p>
          ) : (
            <div className="text-sm text-slate-600 space-y-3">
              <p>
                <span className="text-slate-400">Jméno:</span> {data?.name}
              </p>
              <p>
                <span className="text-slate-400">Email:</span> {data?.email}
              </p>
              <p>
                <span className="text-slate-400">Uživatel ID:</span> {data?.user_id}
              </p>
              <p>
                <span className="text-slate-400">Vytvořeno:</span>{' '}
                {data?.created_at ? new Date(data.created_at).toLocaleString('cs-CZ') : '---'}
              </p>
              <p>
                <span className="text-slate-400">Počet QR:</span> {data?.qr_count ?? 0}
              </p>
            </div>
          )}
        </section>

        <section className="surface-card p-6 space-y-4">
          <h2 className="text-2xl font-semibold text-slate-900">Změna hesla</h2>
          <form className="space-y-4" onSubmit={handleSubmit(onChangePassword)}>
            <div>
              <input type="password" placeholder="Aktuální heslo" className="input-field" {...register('current_password')} />
              {errors.current_password && (
                <p className="text-sm text-rose-300 mt-1">{errors.current_password.message}</p>
              )}
            </div>
            <div>
              <input type="password" placeholder="Nové heslo" className="input-field" {...register('new_password')} />
              {errors.new_password && <p className="text-sm text-rose-300 mt-1">{errors.new_password.message}</p>}
            </div>
            <div>
              <input type="password" placeholder="Potvrď nové heslo" className="input-field" {...register('confirm_password')} />
              {errors.confirm_password && (
                <p className="text-sm text-rose-300 mt-1">{errors.confirm_password.message}</p>
              )}
            </div>
            <button type="submit" className="accent-button w-full" disabled={isSubmitting}>
              {isSubmitting ? 'Ukládám...' : 'Uložit heslo'}
            </button>
          </form>
        </section>
      </div>
      <Toast toast={toast} />
    </>
  );
}
