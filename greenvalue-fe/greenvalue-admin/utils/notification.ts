import { notifications } from '@mantine/notifications';

interface NotificationProps {
  title?: string;
  message: string;
}

function showNotification({ color, title, message }: ShowNotificationProps): void {
  notifications.show({
    color,
    title,
    message,
  });
}

function notificationError({ title = 'Hata', message }: NotificationProps): void {
  showNotification({ color: 'red', title, message });
}

function notificationSuccess({ title = 'Başarılı', message }: NotificationProps): void {
  showNotification({ color: 'green', title, message });
}

function notificationInfo({ title = 'Bilgi', message }: NotificationProps): void {
  showNotification({ color: 'blue', title, message });
}

interface ShowNotificationProps extends NotificationProps {
  color: 'red' | 'green' | 'blue';
}

export { notificationInfo, notificationSuccess, notificationError };
