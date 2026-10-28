import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

const BACKEND_URL = process.env.VITE_BACKEND_URL || 'http://127.0.0.1:8001';

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    port: 5173,
    proxy: {
      '/auth': {
        target: BACKEND_URL,
        changeOrigin: true,
      },
      '/transactions': {
        target: BACKEND_URL,
        changeOrigin: true,
      },
      '/analyze': {
        target: BACKEND_URL,
        changeOrigin: true,
      },
      '/forecast': {
        target: BACKEND_URL,
        changeOrigin: true,
      },
      '/cashflow-forecast': {
        target: BACKEND_URL,
        changeOrigin: true,
      },
      '/health': {
        target: BACKEND_URL,
        changeOrigin: true,
      },
    },
  },
});
