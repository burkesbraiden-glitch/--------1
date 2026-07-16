import { API_BASE_URL } from '../config/api.js'
import { buildApiUrl, getAuthorizationHeader } from './request.js'

export function resolveBackendResourceUrl(resourcePath, apiBaseUrl = API_BASE_URL) {
  const path = typeof resourcePath === 'string' ? resourcePath.trim() : ''
  if (/^https?:\/\//i.test(path)) {
    return path
  }

  if (path.startsWith('/api/')) {
    if (!apiBaseUrl) {
      return path
    }
    return `${new URL(apiBaseUrl).origin}${path}`
  }

  if (apiBaseUrl === API_BASE_URL) {
    return buildApiUrl(path)
  }

  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${apiBaseUrl.replace(/\/+$/, '')}${normalizedPath}`
}

function networkError(error) {
  return {
    statusCode: 0,
    code: 'NETWORK_ERROR',
    message: '无法连接服务器，请稍后重试',
    details: error?.errMsg ? { errMsg: error.errMsg } : {},
  }
}

function backendError(body, statusCode) {
  const error = body?.error || {}
  return {
    statusCode,
    code: error.code || body?.code || 'HTTP_ERROR',
    message: error.message || body?.message || '请求失败',
    details: error.details || body?.details || {},
  }
}

function parseBody(value) {
  if (!value) {
    return {}
  }
  if (typeof value === 'string') {
    try {
      return JSON.parse(value)
    } catch (error) {
      return {}
    }
  }
  return value
}

function imageHeaders() {
  return {
    Accept: 'image/png, image/jpeg, image/webp',
    ...getAuthorizationHeader(),
  }
}

function isH5Runtime() {
  return typeof window !== 'undefined'
}

export function uploadAuthenticatedFile(path, filePath, fieldName = 'image') {
  return new Promise((resolve, reject) => {
    if (!filePath) {
      reject({ code: 'IMAGE_REQUIRED', message: '请选择图片' })
      return
    }

    uni.uploadFile({
      url: buildApiUrl(path),
      filePath,
      name: fieldName,
      header: {
        Accept: 'application/json',
        ...getAuthorizationHeader(),
      },
      success(response) {
        const body = parseBody(response.data)
        if (response.statusCode >= 200 && response.statusCode < 300 && body.success !== false) {
          resolve(body.data || {})
          return
        }
        reject(backendError(body, response.statusCode))
      },
      fail(error) {
        reject(networkError(error))
      },
    })
  })
}

async function downloadForH5(path) {
  let response
  try {
    response = await fetch(resolveBackendResourceUrl(path), {
      headers: imageHeaders(),
      cache: 'no-store',
    })
  } catch (error) {
    throw networkError(error)
  }

  if (!response.ok) {
    let body = {}
    try {
      body = await response.json()
    } catch (error) {
      body = {}
    }
    throw backendError(body, response.status)
  }

  const blob = await response.blob()
  if (!blob || !blob.size || !blob.type.startsWith('image/')) {
    throw { code: 'TASK_IMAGE_NOT_FOUND', message: '暂未找到任务图片' }
  }

  const displayPath = URL.createObjectURL(blob)
  return {
    displayPath,
    cleanup() {
      URL.revokeObjectURL(displayPath)
    },
  }
}

function downloadForUni(path) {
  return new Promise((resolve, reject) => {
    uni.downloadFile({
      url: resolveBackendResourceUrl(path),
      header: imageHeaders(),
      success(response) {
        if (response.statusCode >= 200 && response.statusCode < 300 && response.tempFilePath) {
          resolve({ displayPath: response.tempFilePath, cleanup: null })
          return
        }
        reject(backendError({}, response.statusCode))
      },
      fail(error) {
        reject(networkError(error))
      },
    })
  })
}

export function downloadAuthenticatedFile(path) {
  return isH5Runtime() ? downloadForH5(path) : downloadForUni(path)
}
