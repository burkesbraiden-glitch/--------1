import { validateApiBaseUrl } from './apiBaseUrl.js'

const viteEnv = import.meta.env || {}

export const API_BASE_URL = validateApiBaseUrl(viteEnv.VITE_API_BASE_URL, viteEnv)
