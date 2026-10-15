import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const rootReadmePath = path.resolve(__dirname, '../README.md')

function readmePlugin() {
  return {
    name: 'vite-plugin-readme',
    resolveId(id) {
      if (id === 'virtual:readme') {
        return '\0virtual:readme'
      }
    },
    load(id) {
      if (id === '\0virtual:readme') {
        const content = fs.existsSync(rootReadmePath)
          ? fs.readFileSync(rootReadmePath, 'utf-8')
          : '# FAS WUSL Timetable Downloader & Parser\n\nREADME content unavailable.'
        return `export default ${JSON.stringify(content)};`
      }
    },
    handleHotUpdate({ file, server }) {
      if (path.resolve(file) === rootReadmePath) {
        server.ws.send({
          type: 'full-reload'
        })
      }
    }
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), readmePlugin()],
  server: {
    port: 5173,
    fs: {
      allow: ['..']
    },
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
  },
})
