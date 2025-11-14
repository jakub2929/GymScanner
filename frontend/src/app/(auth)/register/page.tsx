'use client';

import AuthCard from '@/components/auth-card';
import { Toast, useToast } from '@/components/toast';
import { apiClient } from '@/lib/apiClient';
import { zodResolver } from '@hookform/resolvers/zod';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

const schema = z.object({
  name: z.string().min(2, 'Jméno musí mít alespoň 2 znaky'),
  email: z.string().email('Zadejte platný e-mail'),
  password: z.string().min(6, 'Heslo musí mít alespoň 6 znaků'),
});

export default function RegisterPage() {
  const router = useRouter();
  const { toast, showToast } = useToast();
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<z.infer<typeof schema>>({ resolver: zodResolver(schema) });

  async function onSubmit(values: z.infer<typeof schema>) {
    try {
      await apiClient('/api/register', {
        method: 'POST',
        body: JSON.stringify(values),
      });
      showToast('Registrace byla úspěšná, nyní se přihlas');
      router.push('/login');
    } catch (error) {
      showToast(error instanceof Error ? error.message : 'Chyba při registraci', 'error');
    }
  }

  return (
    <>
      <AuthCard title="Registrace" subtitle="Získej přístup ke svému účtu">
        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          <div>
            <input type="text" placeholder="Jméno" className="input-field" {...register('name')} />
            {errors.name && <p className="text-sm text-rose-300 mt-1">{errors.name.message}</p>}
          </div>
          <div>
            <input type="email" placeholder="Email" className="input-field" {...register('email')} />
            {errors.email && <p className="text-sm text-rose-300 mt-1">{errors.email.message}</p>}
          </div>
          <div>
            <input type="password" placeholder="Heslo" className="input-field" {...register('password')} />
            {errors.password && <p className="text-sm text-rose-300 mt-1">{errors.password.message}</p>}
          </div>
          <button type="submit" className="accent-button" disabled={isSubmitting}>
            {isSubmitting ? 'Registruji...' : 'Registrovat'}
          </button>
        </form>
        <p className="text-sm text-slate-400 text-center">
          Už máš účet?{' '}
          <Link href="/login" className="auth-link">
            Přihlas se
          </Link>
        </p>
      </AuthCard>
      <Toast toast={toast} />
    </>
  );
}
