// EXPO_PUBLIC_* variables are inlined at build time. For a phone on the same Wi-Fi, set
// EXPO_PUBLIC_API_URL=http://<computer-LAN-IP>:8000 in app/.env.local (localhost is the phone itself).
export const API_URL = (process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000').replace(/\/$/, '');
