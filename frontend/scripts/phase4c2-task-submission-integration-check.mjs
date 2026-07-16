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
for (const name of ['getTasks', 'generateTasks', 'getTask', 'startTaskSubmission', 'updateTaskSubmission', 'completeTaskSubmission']) {
  assert(tasksApi.includes(`function ${name}`), `tasks API missing ${name}`)
}
for (const path of [
  'path: `/plans/${planId}/tasks/${taskId}/submission/start`',
  'path: `/plans/${planId}/tasks/${taskId}/submission`',
  'path: `/plans/${planId}/tasks/${taskId}/submission/complete`',
]) {
  assert(tasksApi.includes(path), `tasks API missing ${path}`)
}
assert((tasksApi.match(/auth:\s*true/g) || []).length === 6, 'all Task and Submission APIs must use auth=true')

const taskStore = read('stores/task.js')
for (const token of [
  'upsertRemoteTask',
  'startTaskSubmission',
  'saveTaskNote',
  'completeTaskSubmission',
  'submissionQueues',
  'sessionEpoch',
  'taskImageCache',
]) {
  assert(taskStore.includes(token), `taskStore missing ${token}`)
}
assert(taskStore.includes('tasksApi.startTaskSubmission'), 'taskStore must call real Submission start')
assert(taskStore.includes('tasksApi.updateTaskSubmission'), 'taskStore must call real Submission PATCH')
assert(taskStore.includes('tasksApi.completeTaskSubmission'), 'taskStore must call real Submission complete')
assert(!taskStore.includes('markTaskCompleted'), '4C-2 must remove local markTaskCompleted')
assert(!taskStore.includes('localTaskDrafts'), '4C-3 must remove localTaskDrafts')
assert(taskStore.includes('remoteTask.status'), 'display Task status must come from Remote Task')
assert(taskStore.includes('remoteRecord.note'), 'display Task note must come from Remote Task')
assert(taskStore.includes('remoteTask.completedAt'), 'display Task completedAt must come from Remote Task')
assert(taskStore.includes('this.tasksByPlanId'), 'progress must use remote tasksByPlanId')
assert(taskStore.includes('String('), 'Task id comparisons must remain normalized')

const tasksPage = read('pages/tasks/index.vue')
assert(tasksPage.includes('开始探索后即可记录任务'), 'Tasks page must explain ready Plan recording gate')
assert(tasksPage.includes('startExploration'), 'Tasks page must provide explicit Plan start action')

const detailPage = read('pages/task-detail/index.vue')
for (const token of ['noteDraft', 'startTask', 'flushNoteSave', '开始探索后即可记录这个任务', '开始任务']) {
  assert(detailPage.includes(token), `Task Detail missing ${token}`)
}
assert(detailPage.includes('600'), 'Task Detail must debounce note saving around 600ms')
assert(!detailPage.includes('markTaskCompleted'), 'Task Detail must not locally complete tasks')
assert(!detailPage.includes('imagePath: this.noteDraft'), 'Task Detail must not send imagePath as note payload')

const recordPage = read('pages/record/index.vue')
assert(recordPage.includes('currentPlanTasks'), 'Record page must use merged display Tasks')
assert(!recordPage.includes('tasksByPlanId'), 'Record page must not bypass display Task merge')

assert(readProject('README.md').includes('第 4C-2 阶段记录'), 'README must document 4C-2')
assert(readProject('docs/backend-design.md').includes('第 4C-2 前端联调记录'), 'backend-design must document 4C-2')

console.log('phase4c2 task submission integration checks passed')
