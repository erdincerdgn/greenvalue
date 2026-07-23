import { ListingStatus } from '@/utils/enums/listing';
import { IconAlarm, IconAlarmFilled } from '@tabler/icons-react';

export const getNavbarList = () => [
  {
    path: '/dashboard',
    label: 'Sistem Genel Bakış',
  },
  {
    path: '/listings',
    label: 'İlanlar',
    isNested: true,
    subItems: [
      { label: 'Taslaktakiler', path: `/listings?status=${ListingStatus.DRAFT}` },
      { label: 'Onay Bekleyenler', path: `/listings?status=${ListingStatus.PENDING_APPROVAL}` },
      { label: 'Red/Revizyon Bekleyen', path: `/listings?status=${ListingStatus.REVISION}` },
      { label: 'Yayındakiler', path: `/listings?status=${ListingStatus.ACTIVE}` },
      { label: 'Yayından Kaldırılanlar', path: `/listings?status=${ListingStatus.INACTIVE}` },
      { label: 'Satılanlar', path: `/listings?status=${ListingStatus.SOLD}` },
    ],
  },
  {
    path: '/inquiries',
    label: 'Gelen Talepler',
  },
  {
    path: '/user',
    label: 'Kullanıcılar',
  },
  {
    path: '/offers',
    label: 'Teklifler',
  },
  {
    path: '/real-estate',
    label: 'Emlak Ofisleri',
    isNested: true,
    subItems: [
      { label: 'Emlak Ofisi', path: '/real-estate/offices' },
      { label: 'Emlak Çalışanı', path: '/real-estate/employees' },
    ],
    activeIcon: <IconAlarmFilled size={16} />,
    inactiveIcon: <IconAlarm size={16} />,
  },
  {
    path: '/settings',
    label: 'Ayarlar',
  },
  {
    key: 'logout',
    label: 'Çıkış Yap',
  },
];
