'use client';

import React, { ReactNode } from 'react';
import { MantineProvider } from '@mantine/core';
import { SessionProvider } from 'next-auth/react';
// eslint-disable-next-line import/extensions
import 'mantine-datatable/styles.layer.css';
import '@mantine/core/styles.css';

export default function GlobalProvider({ children }: { children: ReactNode }) {
  return (
    <SessionProvider>
      <MantineProvider>{children}</MantineProvider>
    </SessionProvider>
  );
}
