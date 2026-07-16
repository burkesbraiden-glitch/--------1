import { defineStore } from 'pinia'
import * as authApi from '../api/auth.js'

export const AUTH_STORAGE_KEY = 'tonglvji_auth'
export const LEGACY_MOCK_AUTH_STORAGE_KEY = 'tonglvji_mock_auth'

const fallbackUserInfo = {
  nickname: '小小探索家',
  city: '北京',
  age: 7,
}

let restorePromise = null

function getUniStorage() {
  if (typeof uni === 'undefined') {
    return null
  }

  return uni
}

function normalizeUserInfo(userInfo = {}) {
  return {
    ...fallbackUserInfo,
    ...userInfo,
  }
}

export const useUserStore = defineStore('user', {
  state: () => ({
    isLoggedIn: false,
    isAuthReady: false,
    isRestoring: false,
    token: '',
    userInfo: {},
    authError: null,
  }),
  actions: {
    persistAuth() {
      const storage = getUniStorage()
      if (storage?.setStorageSync) {
        storage.setStorageSync(AUTH_STORAGE_KEY, {
          token: this.token,
          userInfo: this.userInfo,
        })
      }
    },
    clearLocalAuth({ keepToken = false } = {}) {
      const storage = getUniStorage()
      if (!keepToken && storage?.removeStorageSync) {
        storage.removeStorageSync(AUTH_STORAGE_KEY)
      }
      if (storage?.removeStorageSync) {
        storage.removeStorageSync(LEGACY_MOCK_AUTH_STORAGE_KEY)
      }

      if (!keepToken) {
        this.token = ''
        this.userInfo = {}
      }
      this.isLoggedIn = false
    },
    loginSuccess(token, userInfo) {
      this.token = token
      this.userInfo = normalizeUserInfo(userInfo)
      this.isLoggedIn = true
      this.isAuthReady = true
      this.authError = null
      this.persistAuth()

      const storage = getUniStorage()
      if (storage?.removeStorageSync) {
        storage.removeStorageSync(LEGACY_MOCK_AUTH_STORAGE_KEY)
      }
    },
    async loginWithPhone(phone, code) {
      const data = await authApi.login(phone, code)
      this.loginSuccess(data.accessToken, data.user)
      return data
    },
    async requestLoginCode(phone) {
      return authApi.sendCode(phone)
    },
    async loginWithWechat(mockCode = 'tonglvji-h5-dev') {
      const data = await authApi.mockWechatLogin(mockCode)
      this.loginSuccess(data.accessToken, data.user)
      return data
    },
    async fetchMe() {
      const data = await authApi.getMe()
      this.userInfo = normalizeUserInfo(data.user)
      this.isLoggedIn = true
      this.isAuthReady = true
      this.authError = null
      this.persistAuth()
      return data.user
    },
    async restoreSession() {
      if (restorePromise) {
        return restorePromise
      }

      restorePromise = this.restoreSessionOnce().finally(() => {
        restorePromise = null
      })
      return restorePromise
    },
    async restoreSessionOnce() {
      this.isRestoring = true

      const storage = getUniStorage()
      if (storage?.removeStorageSync) {
        storage.removeStorageSync(LEGACY_MOCK_AUTH_STORAGE_KEY)
      }

      const saved = storage?.getStorageSync ? storage.getStorageSync(AUTH_STORAGE_KEY) : null
      if (!saved?.token) {
        this.clearLocalAuth()
        this.isAuthReady = true
        this.isRestoring = false
        return false
      }

      this.token = saved.token
      this.userInfo = normalizeUserInfo(saved.userInfo)

      try {
        await this.fetchMe()
        return true
      } catch (error) {
        this.authError = error
        if (['UNAUTHORIZED', 'INVALID_TOKEN', 'TOKEN_EXPIRED'].includes(error?.code) || error?.statusCode === 401) {
          this.clearLocalAuth()
        } else {
          this.clearLocalAuth({ keepToken: true })
        }
        this.isAuthReady = true
        return false
      } finally {
        this.isRestoring = false
      }
    },
    async mockPhoneLogin(phone, code) {
      return this.loginWithPhone(phone, code)
    },
    async mockWechatLogin(mockCode) {
      return this.loginWithWechat(mockCode)
    },
    async restoreMockLogin() {
      return this.restoreSession()
    },
    async setMockLogin() {
      return this.loginWithWechat()
    },
    async logout() {
      try {
        if (this.token) {
          await authApi.logout()
        }
      } catch (error) {
        this.authError = error
      } finally {
        this.clearLocalAuth()
        this.isAuthReady = true
        this.isRestoring = false
      }
    },
  },
})
