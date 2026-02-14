import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { Role } from '@prisma/client';

export class UserResponseDto {
    @ApiProperty()
    id: string;

    @ApiProperty()
    email: string;

    @ApiPropertyOptional()
    fullName: string | null;

    @ApiPropertyOptional()
    phone: string | null;

    @ApiPropertyOptional()
    avatar: string | null;

    @ApiProperty({ enum: Role })
    role: Role;

    @ApiProperty()
    isActive: boolean;

    @ApiPropertyOptional()
    lastLogin: Date | null;

    @ApiProperty()
    createdAt: Date;
}

export class AuthResponseDto {
    @ApiProperty()
    accessToken: string;

    @ApiPropertyOptional()
    refreshToken?: string;

    @ApiProperty()
    expiresIn: number;

    @ApiProperty({ type: UserResponseDto })
    user: UserResponseDto;
}

export class TokenPayloadDto {
    @ApiProperty()
    sub: string;

    @ApiProperty()
    email: string;

    @ApiProperty({ enum: Role })
    role: Role;

    @ApiPropertyOptional()
    iat?: number;

    @ApiPropertyOptional()
    exp?: number;
}
