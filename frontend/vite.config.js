import { defineConfig, loadEnv } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'
import { validateApiBaseUrl } from './src/config/apiBaseUrl.js'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const environment = loadEnv(mode, process.cwd())
  validateApiBaseUrl(environment.VITE_API_BASE_URL, {
    DEV: mode === 'development',
    PROD: mode === 'production',
  })

  return {
    plugins: [
      uni(),
    ],
  }
})
