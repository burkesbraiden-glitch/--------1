import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const src = join(root, 'src')

function read(relativePath) {
  return readFileSync(join(src, relativePath), 'utf8')
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message)
  }
}

const { resolveBackendResourceUrl } = await import('../src/utils/authenticatedFile.js')
const apiBaseUrl = 'http://127.0.0.1:5000/api/v1'
const resourcePath = '/api/v1/plans/100/tasks/68/submission/image'

assert(
  resolveBackendResourceUrl(resourcePath, apiBaseUrl) === 'http://127.0.0.1:5000/api/v1/plans/100/tasks/68/submission/image',
  'resource path with /api/v1 must join only the backend origin',
)
assert(
  !resolveBackendResourceUrl(resourcePath, apiBaseUrl).includes('/api/v1/api/v1/'),
  'resource URL must not duplicate /api/v1',
)
assert(
  resolveBackendResourceUrl('/plans/100/tasks', apiBaseUrl) === 'http://127.0.0.1:5000/api/v1/plans/100/tasks',
  'ordinary API endpoint must keep API_BASE_URL behavior',
)
assert(
  resolveBackendResourceUrl('plans/100/tasks', apiBaseUrl) === 'http://127.0.0.1:5000/api/v1/plans/100/tasks',
  'ordinary API endpoint without a leading slash must keep API_BASE_URL behavior',
)
assert(
  resolveBackendResourceUrl('https://cdn.example.test/task.png', apiBaseUrl) === 'https://cdn.example.test/task.png',
  'absolute resource URL must not be changed',
)

const tasksApi = read('api/tasks.js')
assert(tasksApi.includes('uploadAuthenticatedFile(`/plans/${planId}/tasks/${taskId}/submission/image`'), 'upload endpoint must remain unchanged')

const authenticatedFile = read('utils/authenticatedFile.js')
assert(authenticatedFile.includes('resolveBackendResourceUrl(path)'), 'downloads must use the resource URL resolver')
assert(authenticatedFile.includes('throw backendError(body, response.status)'), 'HTTP 404 must remain an HTTP resource error, not a network error')
assert(!authenticatedFile.includes('token='), 'JWT must not be placed in a URL')

console.log('phase4c3 resource url checks passed')
