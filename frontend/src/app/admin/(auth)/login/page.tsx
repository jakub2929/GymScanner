'use client';

import { useRouter } from 'next/navigation';

export default function AdminLoginPage() {
  const router = useRouter();
  router.replace('/login');
  return null;
}
