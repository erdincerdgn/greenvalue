'use client';

import { ReactNode } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { AuthStatus } from '@/types/common';

interface Props {
  children: ReactNode;
}

export default function LoginLayout({ children }: Props) {
  const { status } = useSession();
  const route = useRouter();

  if (status === AuthStatus.Authenticated) {
    return route.replace('/dashboard');
  }

  return (
    <div
      style={{
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#fff',
      }}
    >
      {children}
    </div>
  );
}
