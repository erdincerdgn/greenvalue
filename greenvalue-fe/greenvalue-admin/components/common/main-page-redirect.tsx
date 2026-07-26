'use client';

import { useRouter } from 'next/navigation';
import { useEffect } from 'react';

export default function MainPageRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.push('/dashboard');
  }, [router]);
  return <></>;
}
