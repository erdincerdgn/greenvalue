'use client';
import { Flex, Paper, TextInput } from '@mantine/core';
import { useState, useEffect } from 'react';
import styles from './settings.module.scss';
import { signOut } from 'next-auth/react';
export default function Settings() {
    return (
        <Paper
            style={{
                width: '100%',
                backgroundColor: 'white',
            }}
        >
        <Flex direction="column">
            <Flex className={styles.header}>
                <button 
                    type='button'
                    onClick={() => {
                            signOut({
                                callbackUrl: `${process.env.NEXT_PUBLIC_URL}/login`,
                            });
                            
                        }
                    }
                >
                    Logout
                </button>
            
            </Flex>

        </Flex>
    </Paper>
    )
}