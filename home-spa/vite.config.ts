import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

export default defineConfig({
  plugins: [svelte()],
  base: '', // relative asset paths so it loads under /local/home-spa/
  build: {
    outDir: '../www/home-spa',
    emptyOutDir: true,
  },
  test: {
    environment: 'jsdom',
    globals: true,
  },
})
