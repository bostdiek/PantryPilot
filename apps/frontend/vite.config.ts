/// <reference types="vitest" />
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';
import svgr from 'vite-plugin-svgr';

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const plugins: any[] = [svgr(), react(), tailwindcss()];

  if (mode === 'test') {
    // Pre-plugin to mock any SVG imports as a no-op React component
    plugins.unshift({
      name: 'svg-mock-for-tests',
      enforce: 'pre',
      resolveId(source: string) {
        if (/\.svg(\?react)?$/.test(source)) {
          return '\0virtual:svg-mock';
        }
        return null;
      },
      load(id: string) {
        if (id === '\0virtual:svg-mock') {
          return "import React from 'react'; export default function SvgMock(){ return null }";
        }
        return null;
      },
    });
  }

  return {
    plugins,
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            react: ['react', 'react-dom'],
            state: ['zustand'],
          },
        },
      },
      chunkSizeWarningLimit: 800,
    },
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: './src/test/setup.ts',
      css: true,
      coverage: {
        provider: 'v8',
        reporter: ['text', 'json', 'html', 'lcov'],
        exclude: [
          'node_modules/',
          'src/test/',
          '**/*.d.ts',
          '**/*.config.*',
          'dist/',
        ],
      },
    },
  };
});
