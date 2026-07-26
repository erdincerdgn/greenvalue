import { AuthRole } from '@/types/common';
import { ICompany } from '@/types/company';
import { PublicResponse } from '@/types/api';

export interface IEditUser {
  username: string;
  name: string;
  companyId: string;
}
export interface IUser {
  id: string;
  email: string;
  name?: string;
  surname?: string;
  username: string;
  password: string;
  phoneNumber: string;
  profilePhoto: string;
  officeId: string;
  role: AuthRole;
  createdAt: Date;
  updateAt: Date;
  company?: ICompany;
  companyId?: string;
  preferedLanguageId?: string;
}

export interface ILoginUser {
  email: string;
  password: string;
}

export interface IRefreshToken {
  refreshToken: string;
}

export interface IInvitation {
  url?: string;
  name: string;
  email: string;
  companyId: string;
  validUntil: string;
  preferedLanguageId: number;
}

export interface IInvitationResponse extends PublicResponse {
  id: string;
  email: string;
  invitationCode: string;
  validUntil: string;
  createdByUserId: number;
  companyId: number;
  used: boolean;
  preferedLanguageId: number;
}

interface FetchUserParams {
  page?: number;
  limit?: number;
  searchTerm?: string;
  sortBy?: 'id' | 'name' | 'email' | 'username' | 'createdAt';
  sortDirection?: 'asc' | 'desc';
}
