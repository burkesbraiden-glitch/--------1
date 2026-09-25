import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useUserStore } from '../../src/stores/user.js'
import { getStorageSnapshot, resetUniRuntime, setRequestHandler } from './setup/uniRuntime.js'

const root = resolve(process.cwd(), '..')
const readFrontendFile = (path) => readFileSync(resolve(root, 'frontend', path), 'utf8')
const loginSource = readFrontendFile('src/pages/login/index.vue')
const authApiSource = readFrontendFile('src/api/auth.js')
const userStoreSource = readFrontendFile('src/stores/user.js')
const manifestSource = readFrontendFile('src/manifest.json')

function blockSource(source, tag) {
  const match = source.match(new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`))
  expect(match).toBeTruthy()
  return match[1]
}

const templateSource = blockSource(loginSource, 'template')
const scriptSource = blockSource(loginSource, 'script')

describe('P8.5C real WeChat-only authentication frontend contract', () => {
  beforeEach(() => {
    resetUniRuntime()
    setActivePinia(createPinia())
  })

  test('renders a single WeChat entry with no phone or verification-code controls', () => {
    expect(templateSource).toContain('@click="submitWechatLogin"')
    expect(templateSource).toContain('微信登录')
    expect(templateSource).not.toContain('手机号码')
    expect(templateSource).not.toContain('验证码')
    expect(templateSource).not.toContain('获取验证码')
    expect(templateSource).not.toContain('手机号登录')
    expect(templateSource).not.toContain('v-model="phone"')
    expect(templateSource).not.toContain('v-model="code"')
  })

  test('contains no phone-login handlers or countdown state in the formal login page', () => {
    for (const forbiddenMarker of [
      'requestCode()', 'submitPhoneLogin()', 'validatePhoneOnly()', 'validatePhoneLogin()',
      'requestLoginCode', 'loginWithPhone', 'countdownTimer', 'isSendingCode', 'isPhoneLoggingIn',
    ]) {
      expect(scriptSource).not.toContain(forbiddenMarker)
    }
  })

  test('calls the real WeChat API rather than the mock endpoint for formal login', () => {
    expect(authApiSource).toContain("path: '/auth/wechat-login'")
    expect(userStoreSource).toContain('authApi.wechatLogin(code)')
    expect(userStoreSource).toContain('authApi.mockWechatLogin(mockCode)')
    expect(userStoreSource).not.toContain("authApi.mockWechatLogin('tonglvji-h5-dev')")
  })

  test('uses the native WeChat provider with code-only authorization on Android and iOS', () => {
    const providerSource = readFrontendFile('src/services/wechatAuth.js')

    expect(providerSource).toContain("provider: 'weixin'")
    expect(providerSource).toContain('onlyAuthorize: true')
    expect(providerSource).toContain('// #ifdef APP-PLUS')
    expect(providerSource).toContain('// #ifdef APP-HARMONY')
    expect(providerSource).not.toContain('openid:')
    expect(providerSource).not.toContain('access_token')
  })

  test('keeps the production mock capability disabled and the development helper explicit', () => {
    expect(readFrontendFile('.env.production')).toMatch(/^VITE_ENABLE_MOCK_WECHAT_LOGIN=false$/m)
    expect(readFrontendFile('.env.development')).toMatch(/^VITE_ENABLE_MOCK_WECHAT_LOGIN=true$/m)
    expect(scriptSource).toContain('isMockWechatLoginEnabled')
    expect(scriptSource).toContain('loginWithMockWechat')
  })

  test('does not place an AppSecret in the frontend manifest or auth sources', () => {
    expect(manifestSource).not.toMatch(/appsecret/i)
    expect(loginSource).not.toMatch(/WECHAT_APP_SECRET|appsecret/i)
    expect(authApiSource).not.toMatch(/WECHAT_APP_SECRET|appsecret/i)
  })

  test('a successful real WeChat login reuses the existing persisted session contract', async () => {
    setRequestHandler((options) => {
      expect(options.url).toMatch(/\/auth\/wechat-login$/)
      expect(options.data).toEqual({ code: 'temporary-wechat-code' })
      options.success({
        statusCode: 200,
        data: {
          success: true,
          data: {
            accessToken: 'wechat-session-token',
            user: { id: 952, phone: null, nickname: null, city: null },
          },
        },
      })
    })

    const user = useUserStore()
    await user.loginWithWechat('temporary-wechat-code')

    expect(user.isLoggedIn).toBe(true)
    expect(user.token).toBe('wechat-session-token')
    expect(getStorageSnapshot().tonglvji_auth).toEqual(expect.objectContaining({
      token: 'wechat-session-token',
      userInfo: expect.objectContaining({ id: 952, nickname: null }),
    }))
  })

  test('a cancelled native authorization never sends a request or establishes a session', async () => {
    const provider = await import('../../src/services/wechatAuth.js')
    const user = useUserStore()
    const login = vi.fn((options) => options.fail({ errMsg: 'login:fail cancel' }))

    await expect(provider.requestNativeWechatAuthorizationCode(login)).rejects.toMatchObject({
      code: 'WECHAT_AUTHORIZATION_CANCELLED',
    })
    expect(user.isLoggedIn).toBe(false)
  })

  test('maps real WeChat errors without introducing a fake-user fallback', () => {
    expect(scriptSource).toContain("WECHAT_LOGIN_UNAVAILABLE: '微信登录暂不可用'")
    expect(scriptSource).toContain("WECHAT_AUTHORIZATION_FAILED: '微信授权已失效，请重新登录'")
    expect(scriptSource).toContain("WECHAT_PROVIDER_UNAVAILABLE: '微信登录服务暂不可用，请稍后重试'")
    expect(scriptSource).not.toContain('微信探索者')
    expect(userStoreSource).not.toContain("mockCode = 'tonglvji-h5-dev'")
    expect(userStoreSource).not.toContain('fallbackUserInfo')
    expect(userStoreSource).not.toContain("nickname: '小小探索家'")
  })
})
