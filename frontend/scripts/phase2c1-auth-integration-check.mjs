import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'

const root = process.cwd()
const src = join(root, 'src')

function read(relativePath) {
  return readFileSync(join(src, relativePath), 'utf8')
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message)
  }
}

const requiredFiles = [
  'config/api.js',
  'utils/request.js',
  'api/auth.js',
  'stores/user.js',
  'stores/child.js',
  'pages/login/index.vue',
]

for (const file of requiredFiles) {
  assert(existsSync(join(src, file)), `Missing ${file}`)
}

const apiConfig = read('config/api.js')
assert(apiConfig.includes('VITE_API_BASE_URL'), 'api config must read VITE_API_BASE_URL')
assert(apiConfig.includes('API_BASE_URL'), 'api config must export API_BASE_URL')
assert(/replace\(\s*\/\\\/\+\$\/\s*,\s*['"]{2}\s*\)/.test(apiConfig), 'api config must trim trailing slashes')

const requestLayer = read('utils/request.js')
assert(requestLayer.includes('uni.request'), 'request layer must use uni.request')
assert(requestLayer.includes('API_BASE_URL'), 'request layer must use API_BASE_URL')
assert(requestLayer.includes('Authorization'), 'request layer must attach Authorization when auth is true')
assert(requestLayer.includes('Bearer'), 'request layer must use Bearer token')
assert(requestLayer.includes('NETWORK_ERROR'), 'request layer must normalize network errors')
assert(!requestLayer.includes('useUserStore'), 'request layer must not import userStore')

const authApi = read('api/auth.js')
for (const endpoint of [
  '/auth/send-code',
  '/auth/login',
  '/auth/mock-wechat-login',
  '/auth/me',
  '/auth/logout',
]) {
  assert(authApi.includes(endpoint), `auth API missing ${endpoint}`)
}
for (const exportName of ['sendCode', 'login', 'mockWechatLogin', 'getMe', 'logout']) {
  assert(authApi.includes(`function ${exportName}`) || authApi.includes(`const ${exportName}`), `auth API missing ${exportName}`)
}

const userStore = read('stores/user.js')
assert(userStore.includes('tonglvji_auth'), 'userStore must use tonglvji_auth')
assert(userStore.includes('removeStorageSync(LEGACY_MOCK_AUTH_STORAGE_KEY)'), 'legacy mock auth key may only be removed')
assert(!userStore.includes("token = 'mock-token'") && !userStore.includes("'mock-token'"), 'userStore must not generate mock-token')
assert(userStore.includes('restorePromise'), 'userStore must prevent duplicate restoreSession calls')
assert(userStore.includes('authApi.logout'), 'logout must call real backend auth API')
assert(userStore.includes('finally'), 'logout must clear local auth in finally')
assert(userStore.includes('loginWithPhone'), 'userStore must expose loginWithPhone')
assert(userStore.includes('loginWithWechat'), 'userStore must expose loginWithWechat')
assert(userStore.includes('restoreSession'), 'userStore must expose restoreSession')

const loginPage = read('pages/login/index.vue')
assert(!/code\s*[!=]={2,3}\s*['"]123456['"]/.test(loginPage), 'login page must not compare code with 123456')
assert(!loginPage.includes('Mock 验证码 123456'), 'login page must not show fixed mock code')
assert(!loginPage.includes('uni.request'), 'login page must not call uni.request directly')
assert(loginPage.includes('loginWithPhone'), 'login page must use userStore.loginWithPhone')
assert(loginPage.includes('loginWithWechat'), 'login page must use userStore.loginWithWechat')

console.log('phase2c1 auth integration checks passed')
