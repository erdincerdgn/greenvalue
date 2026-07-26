import { IconAlarm, IconAlarmFilled } from '@tabler/icons-react';

export const getNavbarList = () => [
  {
    path: '/dashboard',
    label: 'Sistem Genel Bakış',
  },
  {
    path: '/user',
    label: 'Kullanıcılar',
  },
  {
    path: '/reports',
    label: 'Raporlar',
    isNested: true,
    subItems: [
      
      { label: 'Taslaktakiler', path: `/listings` }
    ],
  },
  {
    path: '/settings',
    label: 'Ayarlar',
    activeIcon: <IconAlarmFilled size={16} />,
    inactiveIcon: <IconAlarm size={16} />,
  },
  {
    key: 'logout',
    label: 'Çıkış Yap',
  },
];
