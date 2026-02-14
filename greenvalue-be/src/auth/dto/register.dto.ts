import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import {
    IsEmail,
    IsNotEmpty,
    IsString,
    MinLength,
    MaxLength,
    IsOptional,
    Matches,
    IsEnum,
} from 'class-validator';
import { Role } from '@prisma/client';

export class RegisterDto {
    @ApiProperty({ example: 'user@example.com' })
    @IsEmail({}, { message: 'Please provide a valid email address' })
    @IsNotEmpty({ message: 'Email is required' })
    email: string;

    @ApiProperty({ example: 'Erdinç Erdoğan' })
    @IsString()
    @IsNotEmpty({ message: 'Full name is required' })
    @MaxLength(100)
    fullName: string;

    @ApiProperty({ example: 'SecurePass123!', minLength: 8 })
    @IsString()
    @IsNotEmpty({ message: 'Password is required' })
    @MinLength(8, { message: 'Password must be at least 8 characters' })
    @Matches(/((?=.*\d)|(?=.*\W+))(?![.\n])(?=.*[A-Z])(?=.*[a-z]).*$/, {
        message: 'Password must contain at least 1 uppercase, 1 lowercase, and 1 number or special character',
    })
    password: string;

    @ApiPropertyOptional({ example: '+905359999999' })
    @IsOptional()
    @IsString()
    @Matches(/^\+?\d{10,15}$/, {
        message: 'Phone number must be between 10-15 digits',
    })
    phone?: string;

    @ApiPropertyOptional({ enum: Role, default: Role.OWNER })
    @IsOptional()
    @IsEnum(Role)
    role?: Role;
}

export class CompleteProfileDto {
    @ApiPropertyOptional()
    @IsOptional()
    @IsString()
    @MaxLength(100)
    fullName?: string;

    @ApiPropertyOptional()
    @IsOptional()
    @IsString()
    @Matches(/^\+?\d{10,15}$/)
    phone?: string;

    @ApiPropertyOptional({ description: 'Avatar URL or MinIO key' })
    @IsOptional()
    @IsString()
    avatar?: string;
}
