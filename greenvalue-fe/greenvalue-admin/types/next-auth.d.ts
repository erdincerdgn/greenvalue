// eslint-disable-next-line @typescript-eslint/no-unused-vars
import 'next-auth';

declare module 'next-auth' {
  interface User {
    username: string;
    role: string;
    accessToken: string;
  }

  interface Session {
    user: User & {
      id: string;
      access: string;
    };
    accessToken: string;
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    username: string;
    role: string;
    accessToken: string;
  }
}
