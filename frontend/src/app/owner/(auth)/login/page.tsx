'use client';

import AuthCard from '@/components/auth-card';
import { Toast, useToast } from '@/components/toast';
import { ownerApiClient } from '@/lib/apiClient';
import { setOwnerTokenAtom } from '@/lib/authStore';
import { zodResolver } from '@hookform/resolvers/zod';
import { useSetAtom } from 'jotai';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

const schema = z.object({
  email: z.string().email('Zadejte platný e-mail'),
  password: z.string().min(8, 'Heslo musí mít alespoň 8 znaků'),
});

type FormValues = z.infer<typeof schema>;

export default function OwnerLoginPage() {
  const setOwnerToken = useSetAtom(setOwnerTokenAtom);
  const router = useRouter();
  const { toast, showToast } = useToast();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  async function onSubmit(values: FormValues) {
    try {
      const response = await ownerApiClient<{
        access_token: string;
        owner_email: string;
        owner_name: string;
        role: string;
      }>('/api/owner/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ username: values.email, password: values.password }).toString(),
      });
      setOwnerToken(response.access_token);
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('owner_email', response.owner_email);
        sessionStorage.setItem('owner_name', response.owner_name);
        sessionStorage.setItem('owner_role', response.role ?? 'owner');
      }
      showToast('Přihlášení proběhlo úspěšně');
      router.push('/owner/branding');
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Chyba při přihlášení', 'error');
    }
  }

  return (
    <>
      <AuthCard
        title="Global branding"
        subtitle="Přístup pro majitele platformy"
        navLinks={[
          { href: '/login', label: 'Klient' },
          { href: '/admin/login', label: 'Admin' },
          { href: '/owner/login', label: 'Owner' },
        ]}
      >
        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          <div>
            <input type="email" placeholder="Owner email" className="input-field" {...register('email')} />
            {errors.email && <p className="text-sm text-rose-300 mt-1">{errors.email.message}</p>}
          </div>
          <div>
            <input type="password" placeholder="Owner heslo" className="input-field" {...register('password')} />
            {errors.password && <p className="text-sm text-rose-300 mt-1">{errors.password.message}</p>}
          </div>
          <button type="submit" className="accent-button w-full" disabled={isSubmitting}>
            {isSubmitting ? 'Přihlašuji...' : 'Přihlásit se'}
          </button>
        </form>
      </AuthCard>
      <Toast toast={toast} />
    </>
  );
}
