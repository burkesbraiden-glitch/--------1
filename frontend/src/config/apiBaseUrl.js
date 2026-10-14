export function validateApiBaseUrl(rawBaseUrl, environment = {}) {
  const normalizedBaseUrl = typeof rawBaseUrl === 'string' ? rawBaseUrl.trim().replace(/\/+$/, '') : ''

  if (environment.PROD) {
    if (!normalizedBaseUrl) {
      throw new Error('Missing VITE_API_BASE_URL for production.')
    }

    let parsedUrl
    try {
      parsedUrl = new URL(normalizedBaseUrl)
    } catch {
      throw new Error('Production VITE_API_BASE_URL must be an absolute HTTPS URL.')
    }

    if (
      parsedUrl.protocol !== 'https:'
      || !parsedUrl.hostname
      || ['localhost', '127.0.0.1'].includes(parsedUrl.hostname.toLowerCase())
    ) {
      throw new Error('Production VITE_API_BASE_URL must be an absolute HTTPS URL.')
    }
  }

  if (!normalizedBaseUrl && environment.DEV) {
    throw new Error('Missing VITE_API_BASE_URL. Set it in frontend/.env.development.')
  }

  return normalizedBaseUrl
}
