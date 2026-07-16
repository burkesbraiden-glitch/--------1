import { API_BASE_URL } from '../config/api.js'

const AUTH_STORAGE_KEY = 'tonglvji_auth'

export function buildApiUrl(path) {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE_URL}${normalizedPath}`
}

function getStoredToken() {
  if (typeof uni === 'undefined' || !uni.getStorageSync) {
    return ''
  }

  const saved = uni.getStorageSync(AUTH_STORAGE_KEY)
  return saved?.token || ''
}

export function getAuthorizationHeader() {
  const token = getStoredToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export function isAuthenticationError(error) {
  return ['UNAUTHORIZED', 'INVALID_TOKEN', 'TOKEN_EXPIRED'].includes(error?.code) || error?.statusCode === 401
}

function normalizeBackendError(response, statusCode) {
  const error = response?.error || {}
  return {
    statusCode,
    code: error.code || response?.code || 'HTTP_ERROR',
    message: error.message || response?.message || '请求失败',
    details: error.details || response?.details || {},
  }
}

function normalizeNetworkError(error) {
  return {
    statusCode: 0,
    code: 'NETWORK_ERROR',
    message: '无法连接服务器，请确认后端已启动',
    details: error?.errMsg ? { errMsg: error.errMsg } : {},
  }
}

export function request({ path, method = 'GET', data, auth = false }) {
  return new Promise((resolve, reject) => {
    const header = {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    }

    if (auth) {
      Object.assign(header, getAuthorizationHeader())
    }

    uni.request({
      url: buildApiUrl(path),
      method,
      data,
      header,
      success(response) {
        const statusCode = response.statusCode
        const body = response.data || {}

        if (statusCode >= 200 && statusCode < 300 && body.success !== false) {
          resolve(body.data || {})
          return
        }

        reject(normalizeBackendError(body, statusCode))
      },
      fail(error) {
        reject(normalizeNetworkError(error))
      },
    })
  })
}

export default request
