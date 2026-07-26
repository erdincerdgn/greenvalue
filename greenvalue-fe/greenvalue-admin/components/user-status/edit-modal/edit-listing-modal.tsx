'use client';

import React, { useEffect } from 'react';
import { Button, Modal, Space, TextInput } from '@mantine/core';
import { useForm } from '@mantine/form';
import { notificationError, notificationSuccess } from '@/utils/notification';
import { IUser } from '@/types/user';

interface IModal {
  opened: boolean;
  close: () => void;
  initialValue: Partial<IUser | null>;
  isEditing: boolean;
  onSuccess: () => void;
}

function EditUserModal({ opened, close, initialValue, isEditing , onSuccess }: IModal) {
  const form = useForm({
    initialValues: {
      id: initialValue?.id || '',
      email: initialValue?.email || '',
      name: initialValue?.name || '',
      surname: initialValue?.surname || '',
      username: initialValue?.username || '',
      phoneNumber: initialValue?.phoneNumber || '',
    },
  });

  const onEditSubmit = async () => {
    if (initialValue) {
      const editUserVal: Partial<IUser> = {
          email: form.values.email,
          name: form.values.name,
          surname: form.values.surname,
          username: form.values.username,
          phoneNumber: form.values.phoneNumber,
          
      };
      try {
        // if (initialValue.id) {
        //   const res = await updateUserDetailsById(initialValue.id, editUserVal);
        //   if (res) {
        //     notificationSuccess({ message: 'Kullanıcı, başarıyla güncellendi' });
        //     onSuccess();
        //     form.reset();
        //   } else {
        //     notificationError({ message: 'Kullanıcı güncellenirken bir hata oluştu' });
        //   }
        // } else {
        //   notificationError({ message: 'Geçersiz ID, işlem gerçekleştirilemedi' });
        //   return;
        // }
      } catch (error) {
        notificationError({ message: 'Kullanıcı güncellenirken bir hata oluştu' });
      }
      close();
    }
  };
  useEffect(() => {
    if (initialValue) {
      form.setValues({
        id: initialValue.id,
        email: initialValue.email,
        name: initialValue.name,
        surname: initialValue.surname,
        username: initialValue.username,
        phoneNumber: initialValue.phoneNumber,
        
        
      });
    }
  }, [initialValue]);
  return (
    <Modal opened={opened} onClose={close} size="xl">
      <form onSubmit={form.onSubmit(() => onEditSubmit())}>
        <TextInput
          label="Kullanıcı No"
          placeholder="Kullanıcı No"
          {...form.getInputProps('id')}
          disabled
        />
        <TextInput
          label="Kullanıcı Email"
          placeholder="Kullanıcı Email"
          {...form.getInputProps('email')}
          disabled={!isEditing}
        />
        <TextInput
          label="Adı"
          placeholder="Adı"
          {...form.getInputProps('name')}
          disabled={!isEditing}
        />
        <TextInput
          label="Soyadı"
          placeholder="Soyadı"
          {...form.getInputProps('surname')}
          disabled={!isEditing}
        />
        <TextInput
          label="Kullanıcı Adı"
          placeholder="Kullanıcı Adı"
          {...form.getInputProps('username')}
          disabled={!isEditing}
        />
        <TextInput
          label="Kullanıcı Telefon No"
          placeholder="Kullanıcı Telefon No"
          {...form.getInputProps('phoneNumber')}
          disabled={!isEditing}
        />
        <Space h="md" />
        {isEditing && (
          <Button fullWidth mt="xl" type="submit">
            Düzenle
          </Button>
        )}
      </form>
    </Modal>
  );
}

export default EditUserModal;
