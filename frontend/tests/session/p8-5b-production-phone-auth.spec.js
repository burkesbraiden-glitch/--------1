import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useUserStore } from '../../src/stores/user.js'
import { getStorageSnapshot, resetUniRuntime, setRequestHandler } from './setup/uniRuntime.js'

const root = resolve(process.cwd(), '..')
const readFrontendFile = (path) => readFileSync(resolve(root, 'frontend', path), 'utf8')
const loginSource = readFrontendFile('src/pages/login/index.vue')
const developmentEnv = readFrontendFile('.env.development')

function blockSource(source, tag) {
  const match = source.match(new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`))
  expect(match).toBeTruthy()
  return match[1]
}

const templateSource = blockSource(loginSource, 'template')
const scriptSource = blockSource(loginSource, 'script')

describe('P8.5B legacy phone authentication frontend boundary', () => {
  beforeEach(() => {
    resetUniRuntime()
    setActivePinia(createPinia())
  })

  test('production explicitly disables the mock WeChat capability', () => {
    const productionEnv = readFrontendFile('.env.production')

    expect(productionEnv).toMatch(/^VITE_ENABLE_MOCK_WECHAT_LOGIN=false$/m)
  })

  test('development explicitly retains the mock WeChat capability', () => {
    expect(developmentEnv).toMatch(/^VITE_ENABLE_MOCK_WECHAT_LOGIN=true$/m)
  })

  test('the formal login template has one WeChat entry while keeping the mock capability explicit', () => {
    expect(scriptSource).toContain("import { isMockWechatLoginEnabled } from '../../config/authCapabilities.js'")
    expect(scriptSource).toContain('isMockWechatLoginEnabled')
    expect(templateSource).toContain('submitWechatLogin')
    expect(templateSource).not.toContain('login-page__phone')
    expect(templateSource).not.toContain('requestCode')
    expect(templateSource).not.toContain('submitPhoneLogin')
  })

  test('the development-only legacy phone store contract still retains the existing loginSuccess storage contract', async () => {
    setRequestHandler((options) => options.success({
      statusCode: 200,
      data: {
        success: true,
        data: {
          accessToken: 'phone-production-contract-token',
          user: { id: 951, phone: '13800138000', nickname: '童旅用户', city: null },
        },
      },
    }))

    const user = useUserStore()
    await user.loginWithPhone('13800138000', '654321')

    expect(user.isLoggedIn).toBe(true)
    expect(user.token).toBe('phone-production-contract-token')
    expect(getStorageSnapshot().tonglvji_auth).toEqual(expect.objectContaining({
      token: 'phone-production-contract-token',
      userInfo: expect.objectContaining({ id: 951 }),
    }))
  })

  test('the formal login page does not expose legacy SMS error copy', () => {
    expect(scriptSource).not.toContain('SMS_PROVIDER_UNAVAILABLE')
    expect(scriptSource).not.toContain('SMS_COOLDOWN')
    expect(scriptSource).not.toContain('VERIFICATION_CODE_EXPIRED')
    expect(scriptSource).not.toContain('VERIFICATION_CODE_ATTEMPTS_EXCEEDED')
  })
})
