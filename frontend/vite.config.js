import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Telefon/tunnel gibi harici cihazlarin erisebilmesi icin tum arayuzleri dinle.
    host: true,
    // Cloudflare quick tunnel her calismada rastgele bir *.trycloudflare.com
    // adresi uretir; Vite'in Host kontrolunu bu alan adi icin acik tutuyoruz.
    allowedHosts: ['.trycloudflare.com'],
    // Tek tunnel yetsin diye backend'i ayni origin altindan servis ediyoruz.
    // Boylece VITE_API_URL=/api/chat gibi goreli bir adres kullanilabiliyor.
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: path => path.replace(/^\/api/, ''),
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          unicorn: ['unicornstudio-react'],
          react: ['react', 'react-dom'],
        },
      },
    },
  },
})
