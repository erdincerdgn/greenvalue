module.exports = {
    apps: [
        {
            name: 'greenvalue-admin',
            script: "node_modules/next/dist/bin/next",
            args: "start",
            cwd: "./",
            instances: "max",
            exec_mode: "cluster",
            env_test: {
                NODE_ENV: 'test',
            },
        },
    ],

//     deploy: {
//         test: {
//             user: 'worker',
//             host: ['18.159.13.159'],
//             key: '~/.ssh/id_ed25519',
//             ref: 'origin/dev',
//             repo: 'git@kordinat-admin.github.com:kordinat-com/koordinat-admin.git',
//             path: '/home/worker/kordinat-admin',
//             'pre-deploy-local': '',
//             'post-deploy': 'npm install && npm run build:test && pm2 reload ecosystem.config.js --env test',
//             'pre-setup': '',
//             env: {
//                 NEXT_PUBLIC_URL: "https://test-admin.kordinat.com/",
//                 NEXT_PUBLIC_API_URL: "https://test-be.kordinat.com/",
//                 NEXTAUTH_SECRET: "secret",
//                 PORT: 3010,
//             },
//         },
//     },
};
