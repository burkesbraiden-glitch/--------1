import { existsSync, readdirSync, readFileSync } from 'node:fs'
import { join } from 'node:path'

const root = process.cwd()
const src = join(root, 'src')
const projectRoot = join(root, '..')

function read(relativePath) {
  return readFileSync(join(src, relativePath), 'utf8')
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message)
  }
}

const childrenApiPath = join(src, 'api/children.js')
assert(existsSync(childrenApiPath), 'Missing src/api/children.js')

const childrenApi = read('api/children.js')
assert(childrenApi.includes("from '../utils/request'"), 'children API must reuse unified request')
for (const name of ['getChildren', 'createChild', 'getChild', 'updateChild']) {
  assert(childrenApi.includes(`function ${name}`), `children API missing ${name}`)
}
for (const path of ["path: '/children'", "path: `/children/${id}`"]) {
  assert(childrenApi.includes(path), `children API missing ${path}`)
}
assert((childrenApi.match(/auth:\s*true/g) || []).length >= 4, 'all children API calls must use auth=true')
assert(!childrenApi.includes('uni.request'), 'children API must not call uni.request directly')

const childStore = read('stores/child.js')
assert(childStore.includes("from '../api/children'"), 'childStore must import children API')
assert(childStore.includes('childrenApi.getChildren'), 'childStore must call GET /children')
assert(childStore.includes('childrenApi.createChild'), 'childStore must call POST /children')
assert(childStore.includes('childrenApi.updateChild'), 'childStore must call PATCH /children/{id}')
assert(childStore.includes('fetchPromise'), 'childStore must prevent duplicate GET /children requests')
assert(childStore.includes('loadedForUserId'), 'childStore must track loadedForUserId')
assert(childStore.includes('hasRemoteChild'), 'childStore must distinguish real child from fallback')
assert(childStore.includes('resetSessionState'), 'childStore must expose resetSessionState')
assert(!childStore.includes('childrenApi.createChild({') && !childStore.includes('createChild(DEFAULT'), 'childStore must not auto-create a default child')
assert(!childStore.includes('uni.request'), 'childStore must not call uni.request directly')

const profile = read('pages/profile/index.vue')
assert(profile.includes('fetchChildren'), 'profile must fetch real children')
assert(profile.includes('hasRemoteChild'), 'profile must distinguish no child state')
assert(profile.includes('child.error'), 'profile must distinguish loading failure')
assert(profile.includes('完善孩子档案'), 'profile must show child profile completion entry')
assert(profile.includes('saveChildProfile'), 'profile must save child profile')
assert(profile.includes('resetSessionState'), 'logout must clear childStore session state')
assert(!profile.includes("7岁 · 北京"), 'profile must not hard-code 7岁 · 北京 as real child data')
assert(!profile.includes('uni.request'), 'profile must not call uni.request directly')

for (const file of ['api/records.js', 'api/favorites.js']) {
  assert(!existsSync(join(src, file)), `phase 2C-2 must not add ${file}`)
}

const backendMigrations = join(projectRoot, 'backend/migrations/versions')
const migrationFiles = existsSync(backendMigrations) ? readdirSync(backendMigrations).filter((file) => file.endsWith('.py')) : []
assert(migrationFiles.length <= 3, 'frontend checks must not add backend migrations beyond completed backend phases')

console.log('phase2c2 children integration checks passed')
