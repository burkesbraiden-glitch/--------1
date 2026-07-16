import { createPinia, setActivePinia } from 'pinia'

process.env.NODE_NO_WARNINGS = '1'

globalThis.uni = {
  getStorageSync() {
    return null
  },
  setStorageSync() {},
  removeStorageSync() {},
}

setActivePinia(createPinia())

const [{ usePlanStore }, { useTaskStore }] = await Promise.all([
  import('../src/stores/plan.js'),
  import('../src/stores/task.js'),
])

function assert(condition, message) {
  if (!condition) {
    throw new Error(message)
  }
}

const planStore = usePlanStore()
const taskStore = useTaskStore()

const remoteTaskA = {
  id: 35,
  planId: 101,
  order: 1,
  title: 'A 任务',
  subtitle: 'A subtitle',
  status: 'not-started',
  ageGroup: '7-12',
  duration: '约10分钟',
  type: '观察任务',
  summary: 'A summary',
  objective: 'A objective',
  steps: ['A step'],
  questions: ['A question'],
  recordMode: '拍照记录',
  theme: 'beasts',
  record: {
    imageUrl: null,
    note: '',
  },
}

const remoteTaskB = {
  ...remoteTaskA,
  planId: 202,
  title: 'B 任务',
  status: 'completed',
  record: {
    imageUrl: '/api/v1/plans/202/tasks/35/submission/image',
    note: 'server-note',
  },
}

planStore.applyPlanList(
  [
    { id: 101, title: 'Plan A', destination: 'A', ageGroup: '7-12', duration: '3小时', taskCount: 1, status: 'ready' },
    { id: 202, title: 'Plan B', destination: 'B', ageGroup: '7-12', duration: '3小时', taskCount: 1, status: 'ready' },
  ],
  1,
)

taskStore.setTasksForPlan(101, [remoteTaskA], 1)
taskStore.setTasksForPlan(202, [remoteTaskB], 1)

planStore.selectPlanById(101, 1)
const aDisplay = taskStore.currentPlanTasks[0]
assert(aDisplay.status === 'not-started', 'Plan A display status must remain remote')
assert(aDisplay.record.note === '', 'Plan A display note must remain remote')
assert(aDisplay.record.displayImagePath === '', 'Plan A must not invent a local final image path')
assert(remoteTaskA.status === 'not-started', 'Remote Task A status must not be mutated')
assert(remoteTaskA.record.note === '', 'Remote Task A note must not be mutated')
assert(!remoteTaskA.record.displayImagePath, 'Remote Task A must not receive a display cache path')

planStore.selectPlanById(202, 1)
const bDisplay = taskStore.currentPlanTasks[0]
assert(bDisplay.status === 'completed', 'Plan B must show server completed status when no local draft exists')
assert(bDisplay.record.note === 'server-note', 'Plan B must show server note when no local draft exists')
assert(bDisplay.record.displayImagePath === '', 'Plan B must not receive Plan A display cache')
assert(bDisplay.record.imageUrl === '/api/v1/plans/202/tasks/35/submission/image', 'Plan B must preserve remote imageUrl')
assert(bDisplay.record.note !== '', 'Plan B must not receive Plan A remote note')

const routeMatch = taskStore.setCurrentTask('35')
assert(routeMatch && routeMatch.id === 35, 'route id "35" must match remote numeric task id 35')

assert(remoteTaskB.record.note === 'server-note', 'Remote Task B note must remain unchanged by image Drafts')

taskStore.resetSessionState()
assert(taskStore.currentPlanTasks.length === 0, 'resetSessionState must clear remote tasks')
assert(Object.keys(taskStore.taskImageCache).length === 0, 'resetSessionState must clear image display cache')
assert(!taskStore.currentTask, 'resetSessionState must clear currentTask')

console.log('phase4c1 task draft overlay checks passed')
