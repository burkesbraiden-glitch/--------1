import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const src = join(root, 'src')
const projectRoot = join(root, '..')

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

const tasksApiPath = join(src, 'api/tasks.js')
assert(existsSync(tasksApiPath), 'Missing src/api/tasks.js')

const tasksApi = read('api/tasks.js')
assert(
  tasksApi.includes("from '../utils/request'") || tasksApi.includes("from '../utils/request.js'"),
  'tasks API must reuse unified request',
)
for (const name of ['getTasks', 'generateTasks', 'getTask']) {
  assert(tasksApi.includes(`function ${name}`), `tasks API missing ${name}`)
}
for (const path of [
  'path: `/plans/${planId}/tasks`',
  'path: `/plans/${planId}/tasks/generate`',
  'path: `/plans/${planId}/tasks/${taskId}`',
]) {
  assert(tasksApi.includes(path), `tasks API missing ${path}`)
}
assert((tasksApi.match(/auth:\s*true/g) || []).length >= 3, 'Task query APIs must keep auth=true after later phases')
assert(tasksApi.includes('authenticatedFile'), 'Task image endpoints must reuse the unified authenticated file utility')
assert(!tasksApi.includes('uni.request'), 'tasks API must not call uni.request directly')

const taskStore = read('stores/task.js')
assert(
  taskStore.includes("from '../api/tasks'") || taskStore.includes("from '../api/tasks.js'"),
  'taskStore must import real tasks API',
)
assert(!taskStore.includes("from '../mock/tasks"), 'taskStore must not import mockTasks as business data')
assert(!taskStore.includes('localTaskSessions'), 'localTaskSessions must not remain as task business state in 4C-1')
assert(!taskStore.includes('ensureLocalTaskSession'), 'ensureLocalTaskSession must be removed in 4C-1')
assert(taskStore.includes('tasksByPlanId'), 'taskStore must store real tasksByPlanId')
assert(taskStore.includes('taskImageCache'), 'taskStore must store authenticated image display cache')
assert(taskStore.includes('ensureTasks'), 'taskStore must expose ensureTasks')
assert(taskStore.includes('ensurePromises'), 'taskStore must share same-plan ensureTasks requests')
assert(taskStore.includes('tasksApi.getTasks'), 'taskStore must use real getTasks')
assert(taskStore.includes('tasksApi.generateTasks'), 'taskStore must use real generateTasks')
assert(taskStore.includes('tasksApi.getTask'), 'taskStore must use real getTask detail fallback')
assert(taskStore.includes("status === 'ready'") && taskStore.includes("status === 'in-progress'"), 'ensureTasks must auto-generate only for ready/in-progress plans')
assert(taskStore.includes("status === 'draft'") || taskStore.includes("status === 'completed'"), 'ensureTasks must avoid generate for draft/completed plans')
assert(taskStore.includes('tasks.length') && taskStore.includes('generateTasks'), 'ensureTasks must generate only when GET returns an empty task list')
assert(taskStore.includes('String('), 'taskStore must normalize id comparisons with String(id)')
assert(!taskStore.includes('localTaskDrafts'), '4C-3 must remove localTaskDrafts')
assert(taskStore.includes('displayImagePath'), 'display Task merge must expose image cache displayImagePath')
assert(!/task\.status\s*=(?!=)/.test(taskStore), 'taskStore must not directly mutate remote task.status')
assert(!/task\.record\.note\s*=(?!=)/.test(taskStore), 'taskStore must not directly mutate remote task.record.note')
assert(!/task\.record\.imagePath\s*=(?!=)/.test(taskStore), 'taskStore must not directly mutate remote task.record.imagePath')
assert(!taskStore.includes('serverTaskCount') && !taskStore.includes('localTaskCount') && !taskStore.includes('availableTaskCount'), 'old taskCount compatibility getters must be removed')
assert(taskStore.includes('syncTaskCount'), 'taskStore must sync real taskCount through planStore action')

const planStore = read('stores/plan.js')
assert(planStore.includes('syncTaskCount'), 'planStore must expose syncTaskCount(planId, taskCount)')
assert(planStore.includes('samePlanId'), 'planStore taskCount sync must use normalized plan id comparison')

const home = read('pages/home/index.vue')
assert(!home.includes('ensureLocalTaskSession'), 'Home must not create local Mock task sessions after plan creation')

const planRecovery = read('utils/planRecovery.js')
assert(!planRecovery.includes('ensureLocalTaskSession'), 'planRecovery must not create local Mock task sessions')
assert(planRecovery.includes('ensureTasks'), 'planRecovery must ensure real tasks when withTasks=true')

const planPage = read('pages/plan/index.vue')
assert(planPage.includes('ensureTasks'), 'Plan page must prepare real tasks')
assert(!planPage.includes('availableTaskCount'), 'Plan page must not show old availableTaskCount compatibility value')
assert(!planPage.includes('ensureLocalTaskSession'), 'Plan page must not create local Mock task sessions')

const tasksPage = read('pages/tasks/index.vue')
assert(tasksPage.includes('ensureTasks'), 'Tasks page must load real tasks')
assert(tasksPage.includes('isLoading') && tasksPage.includes('isGenerating') && tasksPage.includes('error'), 'Tasks page must distinguish loading/generating/error states')
assert(tasksPage.includes('任务加载失败，请重试'), 'Tasks page must show Chinese network error copy')
assert(tasksPage.includes('任务准备异常，请稍后重试'), 'Tasks page must show Chinese incomplete task set copy')

const detailPage = read('pages/task-detail/index.vue')
assert(detailPage.includes('routeTaskId'), 'Task Detail must keep route task id')
assert(detailPage.includes('ensureCurrentTask'), 'Task Detail must recover current task')
assert(detailPage.includes('fetchTaskDetail'), 'Task Detail must have detail API refresh fallback')
assert(detailPage.includes('String('), 'Task Detail must support numeric task ids from string route params')
assert(detailPage.includes('completeTaskSubmission'), 'Task Detail must use the later Store Submission action')

const recordPage = read('pages/record/index.vue')
assert(recordPage.includes('currentPlanTasks'), 'Record page must keep using merged display tasks')
assert(!recordPage.includes('tasksByPlanId'), 'Record page must not read raw remote tasks')

const recordJourney = read('stores/recordJourney.mjs')
assert(recordJourney.includes('String('), 'recordJourney must normalize sourceTaskId/task.id for Map and Set dedupe')

const profile = read('pages/profile/index.vue')
assert(!profile.includes('task.tasks.filter'), 'Profile must not depend on old flat local session tasks array')
assert(profile.includes('completedCount'), 'Profile must use merged completedCount or equivalent display count')

for (const token of ['uploadTaskImage', 'downloadTaskImage']) {
  assert(tasksApi.includes(token), `4C-3 must expose ${token} in the Task API module`)
}

for (const file of [
  'backend/app/api/v1/tasks.py',
  'backend/app/services/tasks.py',
  'backend/app/services/task_submissions.py',
  'backend/app/services/task_images.py',
]) {
  assert(existsSync(join(projectRoot, file)), `Missing backend contract file ${file}`)
}

assert(readProject('README.md').includes('第 4C-1 阶段记录'), 'README must document 4C-1')
assert(readProject('docs/backend-design.md').includes('第 4C-1 前端联调记录'), 'backend-design must document 4C-1 frontend integration')

console.log('phase4c1 tasks integration checks passed')
