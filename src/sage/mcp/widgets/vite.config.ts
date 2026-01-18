import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { viteSingleFile } from 'vite-plugin-singlefile';
import path from 'path';

// Get the widget to build from env
const widget = process.env.WIDGET || 'checkin';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), viteSingleFile()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: false, // Don't clear output between builds
    rollupOptions: {
      input: path.resolve(__dirname, `src/${widget}/index.html`),
      output: {
        entryFileNames: `${widget}.js`,
        assetFileNames: `${widget}.[ext]`,
      },
    },
    // Inline all assets
    assetsInlineLimit: 100000000,
    cssCodeSplit: false,
  },
});
