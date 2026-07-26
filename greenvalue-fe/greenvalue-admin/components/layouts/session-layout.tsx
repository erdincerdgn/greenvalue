'use client';

import { Flex, Box } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { Header } from '../header/header';
import { Navbar } from '../navbar/navbar';

const NAVBAR_WIDTH = 268;
const HEADER_HEIGHT = 70;
export default function SessionLayout({ children }: { children: any }) {
  const session = useSession();
  const router = useRouter();

  useEffect(() => {
    if (!session.data) router.push('/login');
    else router.push('/dashboard');
  }, [session]);

  //   if (status === 'loading') return <div>Loading...</div>;

  //   if (!session) return null;

  //   if (requiredRole && session.user?.role !== requiredRole) return <UnauthorizedAccess />;

  //   if (requiredRole === AuthRole.superAdmin && session.user?.role === AuthRole.superAdmin) {
  //     return <MainPageRedirect />;
  //   }
  if (session.data)
    return (
      <>
        <Notifications />
        <Flex style={{ minHeight: '100vh' }}>
          <Box
            style={{
              width: NAVBAR_WIDTH,
              position: 'fixed',
              height: '100vh',
              borderRight: '1px solid #e9ecef',
            }}
          >
            <Navbar />
          </Box>
          <Box
            style={{
              marginLeft: NAVBAR_WIDTH,
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
            }}
          >
            <Header />
            <Box
              component="main"
              style={{
                marginTop: HEADER_HEIGHT,
                backgroundColor: '#f8f9fa',
                flex: 1,
                overflow: 'auto',
              }}
            >
              {children}
            </Box>
          </Box>
        </Flex>
      </>
    );
  return <>{children}</>;
}
