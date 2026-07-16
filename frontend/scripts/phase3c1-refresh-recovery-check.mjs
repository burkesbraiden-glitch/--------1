import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { createPinia, setActivePinia } from 'pinia'

process.env.NODE_NO_WARNINGS = '1'

const root = process.cwd()
const src = join(root, 'src')
const projectRoot = join(root, '..')
const storage = new Map()
let planRequestCount = 0

const planA = {
  id: 19,
  title: 'Plan A',
  destination: 'Plan A Destination',
  ageGroup: '7-12',
  duration: '2 hours',
  taskCount: 0,
  status: 'ready',
}

const planB = {
  id: 20,
  title: 'Plan B',
  destination: 'Plan B Destination',
  ageGroup: '7-12',
  duration: '2 hours',
  taskCount: 0,
  status: 'ready',
}

globalThis.uni = {
  getStorageSync(key) {
    return storage.get(key) || null
  },
  setStorageSync(key, value) {
    storage.set(key, value)
  },
  removeStorageSync(key) {
    storage.delete(key)
  },
  request(options) {
    const url = options.url || ''
    if (url.endsWith('/auth/me')) {
      options.success({
        statusCode: 200,
        data: {
          success: true,
          data: {
            user: {
              id: 7,
              nickname: 'refresh-check-user',
              phone: 'hidden',
            },
          },
        },
      })
      return
    }

    if (url.endsWith('/plans')) {
      planRequestCount += 1
      options.success({
        statusCode: 200,
        data: {
          success: true,
          data: {
            plans: [planA, planB],
          },
        },
      })
      return
    }

    if (url.endsWith('/plans/20/tasks')) {
      options.success({
        statusCode: 200,
        data: {
          success: true,
          data: {
            tasks: [
              { id: 201, planId: 20, order: 1, title: 'Task 1', status: 'not-started', record: { imageUrl: null, note: '' } },
              { id: 202, planId: 20, order: 2, title: 'Task 2', status: 'not-started', record: { imageUrl: null, note: '' } },
              { id: 203, planId: 20, order: 3, title: 'Task 3', status: 'not-started', record: { imageUrl: null, note: '' } },
            ],
            taskCount: 3,
          },
        },
      })
      return
    }

    options.fail({ errMsg: `unexpected request: ${url}` })
  },
}

function read(relativePath) {
  return readFileSync(join(src, relativePath), 'utf8')
}

function readProject(relativePath) {
  return readFileSync(join(projectRoot, relativePath), 'utf8')
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message)
  }
}

const srcPackage = JSON.parse(readFileSync(join(src, 'package.json'), 'utf8'))
assert(Object.keys(srcPackage).length === 1 && srcPackage.type === 'module', 'frontend/src/package.json must only contain type=module')

const planPage = read('pages/plan/index.vue')
const guidePage = read('pages/guide/index.vue')
const tasksPage = read('pages/tasks/index.vue')
const recordPage = read('pages/record/index.vue')
const taskDetailPage = read('pages/task-detail/index.vue')
const planStoreSource = read('stores/plan.js')
const taskStoreSource = read('stores/task.js')
const profilePage = read('pages/profile/index.vue')

for (const [name, source] of [
  ['Plan page', planPage],
  ['Guide page', guidePage],
  ['Tasks page', tasksPage],
  ['Task detail page', taskDetailPage],
  ['Record page', recordPage],
]) {
  assert(source.includes('ensureCurrentPlanReady'), `${name} must use the shared refresh recovery helper`)
}

assert(!planPage.includes('mockPlans[0]'), 'Plan page must not use mockPlans fallback')
assert(!guidePage.includes('mockPlans[0]'), 'Guide page must not use mockPlans fallback')
assert(guidePage.includes('ensureCurrentPlanReady'), 'Guide page must still restore real currentPlan')
assert(!taskStoreSource.includes('setStorageSync') && !taskStoreSource.includes('getStorageSync'), 'task drafts must remain in memory only')
assert(planStoreSource.includes('clearInMemoryState'), 'planStore must separate in-memory clear from selection reset')
assert(planStoreSource.includes('sameUserId'), 'fetchPlans must normalize userId comparisons')
assert(profilePage.includes('plan.resetSessionState'), 'logout must still clear plan selection')
assert(profilePage.includes('task.resetSessionState'), 'logout must still clear task sessions')
assert(readProject('README.md').includes('frontend/src/package.json'), 'README must document why frontend/src/package.json exists')

setActivePinia(createPinia())

const [{ useUserStore }, { usePlanStore }, { useTaskStore }, { ensureCurrentPlanReady }] = await Promise.all([
  import('../src/stores/user.js'),
  import('../src/stores/plan.js'),
  import('../src/stores/task.js'),
  import('../src/utils/planRecovery.js'),
])

const userStore = useUserStore()
const planStore = usePlanStore()
const taskStore = useTaskStore()

storage.set('tonglvji_auth', {
  token: 'redacted-refresh-check-token',
  userInfo: { id: '7', nickname: 'cached-user' },
})
storage.set('tonglvji_current_plan_selection', {
  userId: '7',
  planId: '20',
})

await ensureCurrentPlanReady({ withTasks: true })
assert(userStore.isAuthReady === true, 'auth restore must complete before plan recovery')
assert(userStore.isLoggedIn === true, 'refresh recovery user must be logged in')
assert(String(userStore.userInfo.id) === '7', 'refresh recovery userId must be restored')
assert(String(planStore.currentPlan?.id) === '20', 'Plan B must be restored from stored selection')
assert(taskStore.currentPlanTasks.length === 3, 'Tasks refresh must rebuild 3 local tasks')
assert(taskStore.currentPlanTasks.every((task) => String(task.planId) === '20'), 'Tasks refresh must bind all tasks to Plan B')

const savedSelection = storage.get('tonglvji_current_plan_selection')
assert(String(savedSelection.userId) === '7' && String(savedSelection.planId) === '20', 'same-user refresh must keep Plan B selection')

planRequestCount = 0
planStore.loadedForUserId = '7'
planStore.isLoaded = true
planStore.plans = [planA, planB]
planStore.currentPlan = planB
await planStore.fetchPlans(7)
assert(planRequestCount === 0, 'same userId as string/number must not refetch or clear state')

storage.set('tonglvji_current_plan_selection', {
  userId: '7',
  planId: '20',
})
planStore.clearInMemoryState()
assert(storage.get('tonglvji_current_plan_selection'), 'in-memory clear must not remove current plan selection')
await planStore.fetchPlans(null)
assert(storage.get('tonglvji_current_plan_selection'), 'fetchPlans without ready user must not remove current plan selection')

planStore.resetSessionState()
assert(!storage.get('tonglvji_current_plan_selection'), 'logout/session reset must remove current plan selection')

console.log('phase3c1 refresh recovery checks passed')
