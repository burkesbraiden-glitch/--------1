import { defineConfig } from 'vitest/config'

export default defineConfig({
  define: {
    'import.meta.env.VITE_API_BASE_URL': JSON.stringify('http://session.test/api/v1'),
  },
  test: {
    environment: 'node',
    include: ['tests/session/**/*.spec.js'],
    setupFiles: ['./tests/session/setup/uniRuntime.js'],
    clearMocks: true,
    restoreMocks: true,
    mockReset: true,
  },
})
