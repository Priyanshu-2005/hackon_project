import { defineConfig } from 'vite';

export default defineConfig({
  root: '.',
  build: {
    outDir: 'dist',
    rollupOptions: {
      output: {
        manualChunks: {
          three: ['three'],
          'three-addons': ['three/addons']
        }
      }
    }
  },
  server: {
    port: 5173,
    open: true
  }
});
