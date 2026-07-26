export interface LoginResponse {
  accessToken: string;
  user: {
    id: string;
    email: string;
    username: string;
    name: string | null;
    role: string;
    profilePhoto?: string | null;
  };
}
