import { createPinia, setActivePinia } from 'pinia'

process.env.NODE_NO_WARNINGS = '1'

const storage = new Map()
let serverTask = {
  id: 67,
  planId: 100,
  order: 1,
  title: '找屋顶上的小兽',
  status: 'not-started',
  ageGroup: '7-12',
  duration: '约10分钟',
  type: '观察任务',
  record: { imageUrl: null, note: '' },
  completedAt: null,
}
let holdPatchResponse = false
let delayedPatchResponse = null

function copyTask() {
  return {
    ...serverTask,
    record: { ...serverTask.record },
  }
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
    const respond = (task) => options.success({ statusCode: 200, data: { success: true, data: { task } } })

    if (url.endsWith('/plans/100/tasks/67/submission/start')) {
      serverTask = { ...serverTask, status: 'in-progress' }
      respond(copyTask())
      return
    }

    if (url.endsWith('/plans/100/tasks/67/submission/complete')) {
      serverTask = {
        ...serverTask,
        status: 'completed',
        completedAt: serverTask.completedAt || '2026-07-14T08:00:00Z',
        record: { ...serverTask.record, note: options.data?.note ?? serverTask.record.note },
      }
      respond(copyTask())
      return
    }

    if (url.endsWith('/plans/100/tasks/67/submission')) {
      const applyPatch = () => {
        serverTask = {
          ...serverTask,
          record: { ...serverTask.record, note: options.data?.note ?? '' },
        }
        respond(copyTask())
      }
      if (holdPatchResponse) {
        delayedPatchResponse = applyPatch
        return
      }
      setTimeout(applyPatch, 15)
      return
    }

    options.fail({ errMsg: `unexpected request: ${url}` })
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

userStore.isLoggedIn = true
userStore.isAuthReady = true
userStore.userInfo = { id: 7, nickname: 'flow-check-user' }
planStore.applyPlanList([
  { id: 100, title: 'Plan A', destination: 'A', ageGroup: '7-12', duration: '3小时', taskCount: 1, status: 'in-progress' },
  { id: 200, title: 'Plan B', destination: 'B', ageGroup: '7-12', duration: '3小时', taskCount: 1, status: 'in-progress' },
], 7)
taskStore.setTasksForPlan(100, [copyTask()], 1)
taskStore.setTasksForPlan(200, [{ ...copyTask(), planId: 200, id: 67, record: { imageUrl: null, note: 'B-server-note' } }], 1)
planStore.selectPlanById(100, 7)
taskStore.setCurrentTask('67')

const started = await taskStore.startTaskSubmission('67')
assert(started.status === 'in-progress', 'not-started Task must become remote in-progress after start')
assert(taskStore.currentTask.status === 'in-progress', 'current Task must read remote start result')

assert(taskStore.currentTask.record.displayImagePath === '', 'Task must not invent a local final image path')
assert(taskStore.currentTask.record.note === '', 'display cache must not change remote note')

const firstSave = taskStore.saveTaskNote('67', '较旧文字')
const completed = taskStore.completeTaskSubmission('67', '最新文字')
await Promise.all([firstSave, completed])
assert(taskStore.currentTask.status === 'completed', 'complete must use remote completed status')
assert(taskStore.currentTask.record.note === '最新文字', 'complete response must win over older PATCH response')
assert(taskStore.currentTask.completedAt === '2026-07-14T08:00:00Z', 'completedAt must come from backend Task')
assert(taskStore.completedCount === 1 && taskStore.progress === 100, 'progress must use remote completed status')

const completedAt = taskStore.currentTask.completedAt
await taskStore.saveTaskNote('67', '完成后修改')
assert(taskStore.currentTask.status === 'completed', 'completed note PATCH must not regress status')
assert(taskStore.currentTask.completedAt === completedAt, 'completed note PATCH must preserve completedAt')
assert(taskStore.currentTask.record.note === '完成后修改', 'completed note PATCH must update remote note')

planStore.selectPlanById(200, 7)
assert(taskStore.currentTask.record.displayImagePath === '', 'Plan A display cache must not leak into Plan B')
assert(taskStore.currentTask.record.note === 'B-server-note', 'Plan A note must not leak into Plan B')
planStore.selectPlanById(100, 7)
assert(taskStore.currentTask.record.displayImagePath === '', 'Plan A must not use a local final image path')

taskStore.resetSessionState()
assert(Object.keys(taskStore.tasksByPlanId).length === 0, 'logout reset must clear remote Tasks')
assert(Object.keys(taskStore.taskImageCache).length === 0, 'logout reset must clear image display cache')
assert(Object.keys(taskStore.submissionStates || {}).length === 0, 'logout reset must clear Submission request state')

serverTask = {
  ...serverTask,
  status: 'in-progress',
  completedAt: null,
  record: { imageUrl: null, note: '' },
}
planStore.selectPlanById(100, 7)
taskStore.setTasksForPlan(100, [copyTask()], 1)
taskStore.setCurrentTask('67')
holdPatchResponse = true
const staleSave = taskStore.saveTaskNote('67', '退出前的旧文字')
await new Promise((resolve) => setTimeout(resolve, 0))
assert(typeof delayedPatchResponse === 'function', 'PATCH must be in flight before session reset')
taskStore.resetSessionState()
delayedPatchResponse()
await staleSave
assert(Object.keys(taskStore.tasksByPlanId).length === 0, 'old PATCH response must not restore remote Tasks after logout')
assert(Object.keys(taskStore.submissionStates).length === 0, 'old PATCH response must not restore Submission state after logout')

console.log('phase4c2 task submission flow checks passed')
