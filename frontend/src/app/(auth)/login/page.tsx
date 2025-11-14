'use client';

import AuthCard from '@/components/auth-card';
import { Toast, useToast } from '@/components/toast';
import { apiClient } from '@/lib/apiClient';
import { setTokenAtom } from '@/lib/authStore';
import { zodResolver } from '@hookform/resolvers/zod';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useSetAtom } from 'jotai';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

const schema = z.object({
  email: z.string().email('Zadejte platný e-mail'),
  password: z.string().min(6, 'Heslo musí mít alespoň 6 znaků'),
});

export default function LoginPage() {
  const router = useRouter();
  const setToken = useSetAtom(setTokenAtom);
  const { toast, showToast } = useToast();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema) });

  async function onSubmit(values: z.infer<typeof schema>) {
    try {
      const response = await apiClient<{
        access_token: string;
        user_name: string;
        user_email: string;
        is_admin: boolean;
      }>('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ username: values.email, password: values.password }).toString(),
      });
      setToken(response.access_token);
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('user_name', response.user_name);
        sessionStorage.setItem('user_email', response.user_email);
        sessionStorage.setItem('is_admin', response.is_admin ? 'true' : 'false');
      }
      showToast('Přihlášení proběhlo úspěšně');
      router.push('/dashboard');
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Chyba při přihlášení', 'error');
    }
  }

  return (
    <>
      <AuthCard title="Přihlášení" subtitle="Vstup do dashboardu">
        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          <div>
            <input type="email" placeholder="Email" className="input-field" {...register('email')} />
            {errors.email && <p className="text-sm text-rose-300 mt-1">{errors.email.message}</p>}
          </div>
          <div>
            <input type="password" placeholder="Heslo" className="input-field" {...register('password')} />
            {errors.password && <p className="text-sm text-rose-300 mt-1">{errors.password.message}</p>}
          </div>
          <button type="submit" className="accent-button w-full" disabled={isSubmitting}>
            {isSubmitting ? 'Přihlašuji...' : 'Přihlásit se'}
          </button>
        </form>
        <p className="text-sm text-slate-400 text-center">
          Nemáš účet?{' '}
          <Link href="/register" className="auth-link">
            Registruj se
          </Link>
        </p>
      </AuthCard>
      <Toast toast={toast} />
    </>
  );
}
