'use client';

import { Flex, Text, Group, Avatar } from '@mantine/core';
import { usePathname } from 'next/navigation';
import { useSession } from 'next-auth/react';
import { getPageTitle } from '@/utils/page-titles';
import classes from './header.module.scss';

export function Header() {
  const pathname = usePathname();
  const { data: session } = useSession();
  const pageTitle = getPageTitle(pathname);

  return (
    <Flex className={classes.header} pos="fixed" top={0} h={70}>
      <Text className={classes.pageTitle}>{pageTitle}</Text>

      <Group>
        <Avatar
          src={session?.user?.image}
          w={45}
          h={45}
          radius="45px"
          // alt={session?.user?.username || 'Kullanıcı'}
        />
        <Flex direction="column" gap={3}>
          {/* <Text className={classes.username}>{session?.user?.username}</Text> */}
          <Text className={classes.role}>
            {/* {session?.user?.role === 'SUPER_ADMIN' ? 'Süper Admin' : 'Admin'} */}
          </Text>
        </Flex>
      </Group>
    </Flex>
  );
}
