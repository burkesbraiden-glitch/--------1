import assert from 'node:assert/strict'
import { setActivePinia, createPinia } from 'pinia'

const storage = new Map()

globalThis.uni = {
  setStorageSync(key, value) {
    storage.set(key, value)
  },
  getStorageSync(key) {
    return storage.get(key)
  },
  removeStorageSync(key) {
    storage.delete(key)
  },
}

const { useUserStore, MOCK_AUTH_STORAGE_KEY } = await import('../src/stores/user.js')

function freshStore() {
  setActivePinia(createPinia())
  return useUserStore()
}

const user = freshStore()
assert.equal(MOCK_AUTH_STORAGE_KEY, 'tonglvji_mock_auth')

user.mockPhoneLogin('13800138000')
assert.equal(user.isLoggedIn, true)
assert.equal(user.token, 'mock-token')
assert.deepEqual(user.userInfo, {
  nickname: '小小探索家',
  city: '北京',
  age: 7,
})
assert.deepEqual(storage.get(MOCK_AUTH_STORAGE_KEY), {
  token: 'mock-token',
  userInfo: {
    nickname: '小小探索家',
    city: '北京',
    age: 7,
  },
})

const restored = freshStore()
assert.equal(restored.restoreMockLogin(), true)
assert.equal(restored.isLoggedIn, true)
assert.equal(restored.userInfo.nickname, '小小探索家')

restored.logout()
assert.equal(restored.isLoggedIn, false)
assert.equal(restored.token, '')
assert.deepEqual(restored.userInfo, {})
assert.equal(storage.has(MOCK_AUTH_STORAGE_KEY), false)

const empty = freshStore()
assert.equal(empty.restoreMockLogin(), false)
assert.equal(empty.isLoggedIn, false)

console.log('phase6 auth store tests passed')
