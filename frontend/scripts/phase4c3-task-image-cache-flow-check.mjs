import { createPinia, setActivePinia } from 'pinia'

process.env.NODE_NO_WARNINGS = '1'

const storage = new Map()
const revoked = []
let objectUrlCount = 0
let fetchCount = 0
let serverTask = {
  id: 67,
  planId: 100,
  order: 1,
  title: '找屋顶上的小兽',
  status: 'completed',
  ageGroup: '7-12',
  duration: '约20分钟',
  type: '观察任务',
  record: { imageUrl: null, note: 'aaa' },
  completedAt: '2026-07-15T01:21:46Z',
}
let holdFetch = false
const pendingFetches = []

function copyTask() {
  return { ...serverTask, record: { ...serverTask.record } }
}

function imageResponse(label) {
  return {
    ok: true,
    status: 200,
    blob: async () => new Blob([label], { type: 'image/png' }),
  }
}

globalThis.window = {}
globalThis.URL = {
  createObjectURL() {
    objectUrlCount += 1
    return `blob:task-image-${objectUrlCount}`
  },
  revokeObjectURL(url) {
    revoked.push(url)
  },
}

globalThis.fetch = (url, options) => {
  fetchCount += 1
  if (!options?.headers?.Authorization || options.cache !== 'no-store') {
    return Promise.reject(new Error('authenticated no-store download required'))
  }
  if (!holdFetch) {
    return Promise.resolve(imageResponse(`image-${fetchCount}`))
  }
  return new Promise((resolve) => pendingFetches.push(() => resolve(imageResponse(`image-${fetchCount}`))))
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
  uploadFile(options) {
    if (options.name !== 'image' || options.header?.Authorization !== 'Bearer flow-token') {
      options.fail({ errMsg: 'invalid upload request' })
      return
    }
    serverTask = {
      ...serverTask,
      record: {
        ...serverTask.record,
        imageUrl: '/api/v1/plans/100/tasks/67/submission/image',
      },
    }
    options.success({ statusCode: 200, data: JSON.stringify({ success: true, data: { task: copyTask() } }) })
  },
  downloadFile() {
    throw new Error('H5 flow check must use fetch')
  },
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message)
  }
}

setActivePinia(createPinia())

const [{ useUserStore }, { usePlanStore }, { useTaskStore }] = await Promise.all([
  import('../src/stores/user.js'),
  import('../src/stores/plan.js'),
  import('../src/stores/task.js'),
])

const userStore = useUserStore()
const planStore = usePlanStore()
const taskStore = useTaskStore()

storage.set('tonglvji_auth', { token: 'flow-token' })
userStore.isLoggedIn = true
userStore.isAuthReady = true
userStore.userInfo = { id: 7, nickname: 'flow-check-user' }
planStore.applyPlanList([
  { id: 100, title: 'Plan A', destination: 'A', ageGroup: '7-12', duration: '3小时', taskCount: 1, status: 'in-progress' },
  { id: 200, title: 'Plan B', destination: 'B', ageGroup: '7-12', duration: '3小时', taskCount: 1, status: 'in-progress' },
], 7)
taskStore.setTasksForPlan(100, [copyTask()], 1)
taskStore.setTasksForPlan(200, [{ ...copyTask(), planId: 200, record: { imageUrl: null, note: 'B-note' } }], 1)
planStore.selectPlanById(100, 7)
taskStore.setCurrentTask(67)

const uploaded = await taskStore.uploadTaskImage(67, 'temp://first.png')
assert(uploaded.status === 'completed', 'completed Task must stay completed after image upload')
assert(uploaded.record.note === 'aaa', 'upload must keep remote note')
assert(uploaded.completedAt === '2026-07-15T01:21:46Z', 'upload must keep remote completedAt')
assert(taskStore.currentTask.record.imageUrl.endsWith('/submission/image'), 'Remote Task must keep only backend imageUrl')
assert(taskStore.currentTask.record.displayImagePath.startsWith('blob:'), 'H5 download must expose a Blob display path')
assert(!taskStore.tasksByPlanId['100'][0].record.displayImagePath, 'Blob URL must not be written to the Remote Task')

const firstDisplay = taskStore.currentTask.record.displayImagePath
const beforeSharedEnsure = fetchCount
await Promise.all([taskStore.ensureTaskImageDisplay(67), taskStore.ensureTaskImageDisplay(67)])
assert(fetchCount === beforeSharedEnsure, 'same Task must reuse a cached display result')

holdFetch = true
const staleEnsure = taskStore.ensureTaskImageDisplay(67, { force: true })
await new Promise((resolve) => setTimeout(resolve, 0))
const replacement = taskStore.uploadTaskImage(67, 'temp://second.png')
holdFetch = false
while (pendingFetches.length) {
  pendingFetches.shift()()
}
await Promise.all([staleEnsure, replacement])
const replacementDisplay = taskStore.currentTask.record.displayImagePath
assert(replacementDisplay !== firstDisplay, 'replacement must display a newly downloaded image')
assert(revoked.includes(firstDisplay), 'replacement must revoke the old Blob URL')
assert(revoked.some((url) => url !== firstDisplay), 'stale download Blob URL must be revoked')

planStore.selectPlanById(200, 7)
taskStore.setCurrentTask(67)
assert(!taskStore.currentTask.record.displayImagePath, 'Plan A image must not leak into Plan B')
planStore.selectPlanById(100, 7)
taskStore.setCurrentTask(67)

holdFetch = true
const staleAfterLogout = taskStore.ensureTaskImageDisplay(67, { force: true })
await new Promise((resolve) => setTimeout(resolve, 0))
taskStore.resetSessionState()
holdFetch = false
while (pendingFetches.length) {
  pendingFetches.shift()()
}
await staleAfterLogout
assert(Object.keys(taskStore.taskImageCache).length === 0, 'logout reset must clear the image cache')
assert(revoked.includes(replacementDisplay), 'logout reset must revoke current Blob URLs')

console.log('phase4c3 task image cache flow checks passed')
