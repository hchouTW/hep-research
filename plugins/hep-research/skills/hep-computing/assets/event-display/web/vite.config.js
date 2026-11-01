import { defineConfig } from 'vite';

// base './' keeps every asset path relative, so the built page works under any sub-path of a static server.
// Each panel module is imported dynamically in src/panels.js, so Vite emits one lazy chunk per chart library.
export default defineConfig({
  base: './',
  build: { outDir: 'dist', emptyOutDir: true, chunkSizeWarningLimit: 6000 },
});
