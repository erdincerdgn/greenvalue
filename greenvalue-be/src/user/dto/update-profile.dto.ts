import { ApiPropertyOptional } from '@nestjs/swagger';
import { IsOptional, IsString, IsEmail, MaxLength, Matches } from 'class-validator';

export class UpdateUserProfileDto {
    @ApiPropertyOptional({ example: 'user@example.com' })
    @IsOptional()
    @IsEmail({}, { message: 'Please provide a valid email address' })
    email?: string;

    @ApiPropertyOptional({ example: 'Erdinç Erdoğan' })
    @IsOptional()
    @IsString()
    @MaxLength(100)
    fullName?: string;

    @ApiPropertyOptional({ example: '+905359999999' })
    @IsOptional()
    @IsString()
    @Matches(/^\+?\d{10,15}$/, {
        message: 'Phone number must be between 10-15 digits',
    })
    phone?: string;

    @ApiPropertyOptional({ description: 'Avatar URL or MinIO key' })
    @IsOptional()
    @IsString()
    avatar?: string;
}
