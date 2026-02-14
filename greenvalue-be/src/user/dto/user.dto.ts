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

export class UserStatsDto {
    @ApiProperty({ description: 'Total properties owned' })
    totalProperties: number;

    @ApiProperty({ description: 'Total analyses run' })
    totalAnalyses: number;

    @ApiProperty({ description: 'Completed analyses' })
    completedAnalyses: number;

    @ApiProperty({ description: 'Total reports generated' })
    totalReports: number;
}

export class AdminUpdateUserDto {
    @ApiPropertyOptional({ enum: Role })
    role?: Role;

    @ApiPropertyOptional()
    isActive?: boolean;
}
