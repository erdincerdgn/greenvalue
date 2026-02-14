import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { Role } from '@prisma/client';

export class UserDto {
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

    @ApiProperty()
    updatedAt: Date;
}

export class UserMinimalDto {
    @ApiProperty()
    id: string;

    @ApiProperty()
    email: string;

    @ApiPropertyOptional()
    fullName: string | null;

    @ApiPropertyOptional()
    avatar: string | null;
}

export class CurrentUserDto {
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

    @ApiPropertyOptional({ description: 'Number of properties owned' })
    propertyCount?: number;

    @ApiPropertyOptional({ description: 'Number of analyses run' })
    analysisCount?: number;
}
