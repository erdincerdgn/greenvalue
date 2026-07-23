'use client';

import { useEffect } from 'react';
import { TextInput, PasswordInput, Checkbox, Button, Card } from '@mantine/core';
import { useRouter } from 'next/navigation';
import { useForm } from '@mantine/form';
import { signIn } from 'next-auth/react';
import { notificationError } from '@/utils/notification';

interface ILoginForm {
  email: string;
  password: string;
  rememberMe: boolean;
}

export function LoginForm() {
  const router = useRouter();

  const form = useForm({
    initialValues: {
      email: '',
      password: '',
      rememberMe: false,
    },

    validate: {
      email: (value) => (/^\S+@\S+$/.test(value) ? null : 'Invalid email'),
      password: (value) => (value.length < 1 ? 'Password is required' : null),
    },
  });

  const onSubmit = async (val: ILoginForm) => {
    const signInData = await signIn('credentials', {
      email: val.email,
      password: val.password,
      redirect: false,
    });

    if (signInData?.error) {

      switch (signInData.error) {
        case 'INVALID_CREDENTIALS':
          notificationError({ message: 'Kullanıcı adı veya şifre yanlış' });
          break;
        case 'SERVER_ERROR':
          notificationError({ message: 'Sunucu hatası, lütfen daha sonra tekrar deneyin' });
          break;
        default:
          notificationError({
            message: 'Bu sisteme sadece SUPER_ADMIN kullanıcılar giriş yapabilir',
          });
          break;
      }
    } else {
      if (val.rememberMe) {
        localStorage.setItem('rememberedEmail', val.email);
        localStorage.setItem('rememberedPassword', val.password);
      } else {
        localStorage.removeItem('rememberedEmail');
        localStorage.removeItem('rememberedPassword');
      }

      router.refresh();
      router.push('/dashboard');
    }
  };

  useEffect(() => {
    const rememberedEmail = localStorage.getItem('rememberedEmail');
    const rememberedPassword = localStorage.getItem('rememberedPassword');

    if (rememberedEmail && rememberedPassword) {
      form.setValues({
        email: rememberedEmail,
        password: rememberedPassword,
        rememberMe: true,
      });
    }
  }, []);

  return (
    <Card withBorder shadow="md" p={30} mt={250} radius="md" w={500}>
      <form onSubmit={form.onSubmit(onSubmit)}>
        <TextInput
          label="Email"
          placeholder="test@example.com"
          required
          {...form.getInputProps('email')}
        />
        <PasswordInput
          label="Password"
          placeholder="Your password"
          required
          mt="md"
          {...form.getInputProps('password')}
        />
        <Checkbox
          mt="lg"
          label="Remember me"
          checked={form.values.rememberMe}
          onChange={(event) => form.setFieldValue('rememberMe', event.currentTarget.checked)}
        />
        <Button type="submit" fullWidth mt="xl">
          Sign In
        </Button>
      </form>
    </Card>
  );
}
