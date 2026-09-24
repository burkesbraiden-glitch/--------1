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

function pageMethod(source, name) {
  const match = source.match(new RegExp(`async ${name}\\(([^)]*)\\) \\{[\\s\\S]*?\\n    \\},`))
  if (!match) throw new Error(`Missing ${name} method`)
  const functionSource = match[0]
    .replace(`async ${name}(`, `async function ${name}(`)
    .replace(/,\s*$/, '')
  return Function(`return (${functionSource})`)()
}

const templateSource = blockSource(loginSource, 'template')
const scriptSource = blockSource(loginSource, 'script')
const requestCode = pageMethod(scriptSource, 'requestCode')

describe('P8.5B production phone authentication frontend contract', () => {
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

  test('the login template renders WeChat only behind the explicit capability flag', () => {
    expect(scriptSource).toContain("import { isMockWechatLoginEnabled } from '../../config/authCapabilities.js'")
    expect(scriptSource).toContain('isMockWechatLoginEnabled')
    expect(templateSource).toContain('v-if="isMockWechatLoginEnabled"')
  })

  test('a successful send-code response starts the backend-provided countdown', async () => {
    const context = {
      countdown: 0,
      countdownTimer: null,
      isSendingCode: false,
      phone: '13800138000',
      validatePhoneOnly: vi.fn(() => true),
      clearCountdown: vi.fn(),
      user: { requestLoginCode: vi.fn().mockResolvedValue({ cooldownSeconds: 45 }) },
    }
    const showToast = vi.fn()
    uni.showToast = showToast

    await requestCode.call(context)

    expect(context.countdown).toBe(45)
    expect(context.clearCountdown).toHaveBeenCalledTimes(1)
    expect(showToast).toHaveBeenCalledWith({ title: '验证码已发送', icon: 'none' })
    clearInterval(context.countdownTimer)
  })

  test('a failed send-code request never starts a countdown', async () => {
    const context = {
      countdown: 0,
      countdownTimer: null,
      isSendingCode: false,
      phone: '13800138000',
      validatePhoneOnly: vi.fn(() => true),
      clearCountdown: vi.fn(),
      mapAuthError: vi.fn(() => '短信服务暂不可用'),
      user: { requestLoginCode: vi.fn().mockRejectedValue({ code: 'SMS_PROVIDER_UNAVAILABLE' }) },
    }
    const showToast = vi.fn()
    uni.showToast = showToast

    await requestCode.call(context)

    expect(context.countdown).toBe(0)
    expect(context.countdownTimer).toBeNull()
    expect(context.clearCountdown).not.toHaveBeenCalled()
    expect(showToast).toHaveBeenCalledWith({ title: '短信服务暂不可用', icon: 'none' })
  })

  test('a successful phone login retains the existing loginSuccess storage contract', async () => {
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

  test('the login page maps production SMS errors to actionable copy', () => {
    expect(scriptSource).toContain("SMS_PROVIDER_UNAVAILABLE: '短信服务暂不可用，请稍后重试'")
    expect(scriptSource).toContain("SMS_COOLDOWN: '请求过于频繁，请稍后再试'")
    expect(scriptSource).toContain("VERIFICATION_CODE_EXPIRED: '验证码已过期，请重新获取'")
    expect(scriptSource).toContain("VERIFICATION_CODE_ATTEMPTS_EXCEEDED: '验证码尝试次数过多，请重新获取'")
  })
})
