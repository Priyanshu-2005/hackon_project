import { defineConfig } from 'vite';

export default defineConfig({
  root: '.',
  build: {
    outDir: 'dist',
  },
  server: {
    port: 5173,
    open: true
  },
  test: {
    // Property-based tests (fast-check) construct the DOM hundreds of times
    // per case, so allow more than the 5s default to avoid flaky timeouts.
    testTimeout: 20000,
  },
});
