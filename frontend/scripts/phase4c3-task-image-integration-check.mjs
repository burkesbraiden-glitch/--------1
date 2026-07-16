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

const tasksApi = read('api/tasks.js')
for (const name of ['uploadTaskImage', 'downloadTaskImage']) {
  assert(tasksApi.includes(`function ${name}`), `tasks API missing ${name}`)
}
assert(tasksApi.includes('/submission/image'), 'tasks API must target the Task image endpoint')
assert(!tasksApi.includes('token='), 'Task image API must not put JWT in the URL')

const authenticatedFilePath = join(src, 'utils/authenticatedFile.js')
assert(existsSync(authenticatedFilePath), 'Missing unified authenticatedFile utility')
const authenticatedFile = read('utils/authenticatedFile.js')
for (const token of ['buildApiUrl', 'Authorization', 'uni.uploadFile', 'uni.downloadFile', 'fetch(', "cache: 'no-store'", 'URL.createObjectURL', 'URL.revokeObjectURL']) {
  assert(authenticatedFile.includes(token), `authenticatedFile missing ${token}`)
}
assert(!authenticatedFile.includes('multipart/form-data'), 'upload must not manually set multipart boundary')
assert(!authenticatedFile.includes('token='), 'authenticatedFile must not put JWT in a URL')

const taskStore = read('stores/task.js')
for (const token of ['taskImageCache', 'ensureTaskImageDisplay', 'uploadTaskImage', 'generation', 'sessionEpoch', 'userId', 'planId', 'taskId', 'URL.revokeObjectURL']) {
  assert(taskStore.includes(token), `taskStore missing ${token}`)
}
assert(!taskStore.includes('localTaskDrafts'), '4C-3 must remove localTaskDrafts')
assert(!taskStore.includes('imagePath'), '4C-3 taskStore must not retain local final imagePath')
assert(taskStore.includes('upsertRemoteTask'), 'image upload must upsert the returned Remote Task')

const detailPage = read('pages/task-detail/index.vue')
for (const token of ['pendingPreviewPath', 'uploadTaskImage', 'ensureTaskImageDisplay', 'displayImagePath']) {
  assert(detailPage.includes(token), `Task Detail missing ${token}`)
}
assert(!detailPage.includes('updateTaskImagePath'), 'Task Detail must not retain local image drafts')

const recordPage = read('pages/record/index.vue')
assert(recordPage.includes('ensureTaskImageDisplay'), 'Record page must restore authenticated task images')
assert(recordPage.includes('displayImagePath'), 'Record page must consume displayImagePath')
assert(!recordPage.includes('record.imagePath'), 'Record page must not use local imagePath as a final record source')

const recordJourney = read('stores/recordJourney.mjs')
assert(recordJourney.includes('displayImagePath'), 'Record journey must use displayImagePath')
assert(!recordJourney.includes('task.record?.imagePath'), 'Record journey must not use local Task imagePath')

assert(readProject('README.md').includes('4C-3'), 'README must document 4C-3')
assert(readProject('docs/backend-design.md').includes('4C-3'), 'backend design notes must document 4C-3')

console.log('phase4c3 task image integration checks passed')
