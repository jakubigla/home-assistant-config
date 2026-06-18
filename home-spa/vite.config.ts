import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

const isTest = process.env.NODE_ENV === 'test' || !!process.env.VITEST

export default defineConfig({
  plugins: [svelte({ preprocess: isTest ? [] : undefined })],
  base: '', // relative asset paths so it loads under /local/home-spa/
  build: {
    outDir: '../www/home-spa',
    emptyOutDir: true,
  },
  // Svelte 5's package exports resolve to the server entry by default under
  // vitest; the 'browser' condition forces the client entry so components
  // mount in jsdom. Test-only, applied via the VITEST guard — the production
  // build resolves through the svelte() plugin and is unaffected. Portable —
  // no absolute paths.
  resolve: isTest ? { conditions: ['browser'] } : {},
  test: {
    environment: 'jsdom',
    globals: true,
  },
})
