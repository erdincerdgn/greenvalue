// module.exports = {
//     apps: [
//         {
//             name: 'koordinat-fe',
//             script: "node_modules/next/dist/bin/next",
//             args: "start",
//             cwd: "./",
//             instances: "max",
//             exec_mode: "cluster",
//             env_test: {
//                 NODE_ENV: 'test',
//             },
//         },
//     ],

//     deploy: {
//         test: {
//             user: 'worker',
//             host: ['18.159.13.159'],
//             key: '~/.ssh/id_ed25519',
//             ref: 'origin/dev',
//             repo: 'git@kordinat-fe.github.com:kordinat-com/koordinat-fe.git',
//             path: '/home/worker/kordinat-fe',
//             'pre-deploy-local': '',
//             'post-deploy': 'npm install && npm run build:test && pm2 reload ecosystem.config.js --env test',
//             'pre-setup': '',
//             env: {
//                 NEXTAUTH_URL:"https://test-fe.kordinat.com",
//                 GOOGLE_MAPS_API_KEY:"AIzaSyB4S0kGdXx_ug8be9dxkyUyHUXqdFyr84o",
//                 NEXT_PUBLIC_URL:"https://test-fe.kordinat.com/",
//                 NEXT_PUBLIC_API_URL:"https://test-be.kordinat.com/",
//                 NEXTAUTH_SECRET: "super-secret",
//                 PORT:3001,
//                 NODE_ENV: 'test',
//             },
//         },
//     },
// };
