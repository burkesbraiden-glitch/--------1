function createWechatAuthError(code, message) {
  const error = new Error(message)
  error.code = code
  return error
}

function isAuthorizationCancelled(error) {
  const message = String(error?.errMsg || error?.message || '').toLowerCase()
  return message.includes('cancel')
}

export function requestNativeWechatAuthorizationCode(login) {
  if (typeof login !== 'function') {
    return Promise.reject(createWechatAuthError('WECHAT_LOGIN_UNAVAILABLE', '微信登录暂不可用'))
  }

  return new Promise((resolve, reject) => {
    login({
      provider: 'weixin',
      onlyAuthorize: true,
      success(result) {
        const code = typeof result?.code === 'string' ? result.code.trim() : ''
        if (!code) {
          reject(createWechatAuthError('WECHAT_AUTHORIZATION_FAILED', '微信授权失败'))
          return
        }
        resolve(code)
      },
      fail(error) {
        reject(createWechatAuthError(
          isAuthorizationCancelled(error) ? 'WECHAT_AUTHORIZATION_CANCELLED' : 'WECHAT_AUTHORIZATION_FAILED',
          isAuthorizationCancelled(error) ? '微信授权已取消' : '微信授权失败',
        ))
      },
    })
  })
}

export function requestWechatAuthorizationCode() {
  // #ifdef APP-HARMONY
  return Promise.reject(createWechatAuthError('WECHAT_LOGIN_UNAVAILABLE', '微信登录暂不可用'))
  // #endif

  // #ifdef APP-PLUS
  return requestNativeWechatAuthorizationCode(uni.login)
  // #endif

  // #ifndef APP
  return Promise.reject(createWechatAuthError('WECHAT_LOGIN_UNAVAILABLE', '微信登录暂不可用'))
  // #endif
}
