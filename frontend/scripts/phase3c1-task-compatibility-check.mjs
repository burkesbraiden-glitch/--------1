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

const planA = {
  id: 101,
  title: '计划 A',
  destination: '故宫博物院',
  ageGroup: '7-12',
  duration: '3小时',
  taskCount: 0,
  status: 'ready',
}
const planB = {
  id: 202,
  title: '计划 B',
  destination: '国家博物馆',
  ageGroup: '7-12',
  duration: '2小时',
  taskCount: 0,
  status: 'ready',
}

const taskA = {
  id: 35,
  planId: 101,
  order: 1,
  title: 'A 真实任务',
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

const taskB = {
  ...taskA,
  planId: 202,
  title: 'B 真实任务',
}

planStore.applyPlanList([planA, planB], 1)
taskStore.setTasksForPlan(101, [taskA], 1)
taskStore.setTasksForPlan(202, [taskB], 1)

planStore.selectPlanById(101, 1)
assert(taskStore.currentPlanTasks.length === 1, 'Plan A must use real remote tasks')
taskStore.setCurrentTask('35')

planStore.selectPlanById(202, 1)
const bTasks = taskStore.currentPlanTasks

assert(bTasks.length === 1, 'Plan B must use real remote tasks')
assert(bTasks.every((task) => task.planId === 202), 'Plan B tasks must keep real Plan B id')
assert(bTasks.every((task) => task.status === 'not-started'), 'Plan B must keep its remote status')
assert(bTasks.every((task) => task.record?.note === ''), 'Plan B must keep its remote note')
assert(bTasks.every((task) => !task.record?.displayImagePath), 'Plan B must not contain Plan A display cache')
assert(taskStore.currentTask === null || taskStore.currentTask.planId === 202, 'currentTask must not keep Plan A display task after switching to B')

taskStore.setCurrentTask(35)

planStore.selectPlanById(101, 1)
const aAgain = taskStore.currentPlanTasks

assert(aAgain[0].record.note === '', 'Plan A must keep its remote note')
assert(!aAgain[0].record.displayImagePath, 'Plan A must not invent a local image path')
assert(aAgain[0].status === 'not-started', 'Plan A must keep its remote status')
assert(aAgain.every((task) => !task.record?.displayImagePath), 'Plan A must not contain Plan B display cache')
assert(planStore.currentPlan.taskCount === 1, 'real taskCount must be synced to currentPlan')

planStore.currentPlan = null
assert(taskStore.currentPlanTasks.length === 0, 'currentPlan=null must not show default Mock tasks')

console.log('phase3c1 task compatibility checks passed')
