const viteEnv = import.meta.env || {}
const rawBaseUrl = viteEnv.VITE_API_BASE_URL

if (!rawBaseUrl && viteEnv.DEV) {
  throw new Error('Missing VITE_API_BASE_URL. Set it in frontend/.env.development.')
}

export const API_BASE_URL = (rawBaseUrl || '').replace(/\/+$/, '')
