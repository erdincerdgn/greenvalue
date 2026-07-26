interface PageTitle {
  path: string;
  title: string;
}

const pageTitles: PageTitle[] = [
  { path: '/dashboard', title: 'Sistem Genel Bakış' },
  { path: '/users', title: 'Kullanıcılar' },
  { path: '/settings', title: 'Ayarlar' },
];

export const getPageTitle = (path: string): string => {
  const page = pageTitles.find((p) => p.path === path);
  return page?.title || 'Koordinat Dashboard';
};
