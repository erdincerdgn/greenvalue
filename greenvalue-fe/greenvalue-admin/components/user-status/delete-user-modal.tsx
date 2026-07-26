import { Flex, Modal, Button , Text } from '@mantine/core';
import React from 'react';
import { notificationError, notificationSuccess } from '@/utils/notification';

interface IModal {
  opened: boolean;
  close: () => void;
  userid: string;
  onSuccess: () => void;
}

function DeleteUserModel({ opened, close, userid , onSuccess }: IModal) {
  const deleteUser = async (id: string) => {
    try {
      // Delete
      notificationSuccess({ message: 'Kullanıcı başarıyla silindi' });
      onSuccess();
    } catch (error) {
      notificationError({ message: 'Kullanıcı silinirken bir hata oluştu' });
    }
    close();
  };

  return (
    <Modal
      opened={opened}
      onClose={close}
      title="Kullanıcıyı Sil"
      transitionProps={{ transition: 'fade', duration: 400, timingFunction: 'linear' }}
    >
      <Flex gap={10} mt={20}>
          <Text>Bu Kullanıcıyı silmek istediğinize emin misiniz?</Text>
        <Button w={100} onClick={() => console.log('...')}>Evet</Button>
        <Button w={100} variant="outline" onClick={close}>
          Hayır
        </Button>
      </Flex>
    </Modal>
  );
}

export default DeleteUserModel;

// deleteUser(userid) to 33th line