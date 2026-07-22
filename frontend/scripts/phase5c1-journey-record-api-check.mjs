import { execFileSync } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const apiRelativePath = 'src/api/journeyRecords.js'
const apiPath = join(root, apiRelativePath)
const allowedChangedFiles = new Set([
  'frontend/src/api/journeyRecords.js',
  'frontend/scripts/phase5c1-journey-record-api-check.mjs',
])

function assert(condition, message) {
  if (!condition) {
    throw new Error(message)
  }
  console.log(`PASS: ${message}`)
}

if (!existsSync(apiPath)) {
  console.error(`FAIL: ${apiRelativePath} 不存在`)
  process.exit(1)
}

const source = readFileSync(apiPath, 'utf8')

function exportedFunction(name) {
  const match = source.match(new RegExp(`export\\s+function\\s+${name}\\s*\\([^)]*\\)\\s*\\{([\\s\\S]*?)\\n\\}`, 'm'))
  assert(match, `导出函数 ${name} 存在`)
  return match[0]
}

assert(/import\s+request\s+from\s+['"]\.\.\/utils\/request\.js['"]/.test(source), '使用现有 request()')
assert(!/uni\.request/.test(source), '不直接使用 uni.request')
assert(!/\bfetch\s*\(/.test(source), '不直接使用 fetch')
assert(!/\/api\/v1/.test(source), 'path 不重复包含 /api/v1')
assert(!/mock|localTaskSessions|localTaskDrafts|authenticatedFile|\bBlob\b|\.\.\/pages\/|\.\.\/stores\/|uni\.(showToast|navigateTo|navigateBack|reLaunch|getStorageSync|setStorageSync|removeStorageSync)/i.test(source), '不依赖 Mock、本地草稿、图片、页面、store、UI 或 storage')

const list = exportedFunction('fetchJourneyRecords')
assert(/path:\s*['"]\/journey-records['"]/.test(list), '列表 path 为 /journey-records')
assert(/method:\s*['"]GET['"]/.test(list), '列表使用 GET')
assert(/data:\s*params/.test(list), '列表透传 query params')
assert(/auth:\s*true/.test(list), '列表启用 JWT')

const detail = exportedFunction('fetchJourneyRecord')
assert(/path:\s*`\/plans\/\$\{planId\}\/journey-record`/.test(detail), '详情 path 正确')
assert(/method:\s*['"]GET['"]/.test(detail), '详情使用 GET')
assert(/auth:\s*true/.test(detail), '详情启用 JWT')

const create = exportedFunction('createJourneyRecord')
assert(/path:\s*`\/plans\/\$\{planId\}\/journey-record`/.test(create), '创建 path 正确')
assert(/method:\s*['"]POST['"]/.test(create), '创建使用 POST')
assert(!/data\s*:/.test(create), '创建不发送 body')
assert(/auth:\s*true/.test(create), '创建启用 JWT')

const update = exportedFunction('updateJourneyRecord')
assert(/path:\s*`\/plans\/\$\{planId\}\/journey-record`/.test(update), '修改 path 正确')
assert(/method:\s*['"]PATCH['"]/.test(update), '修改使用 PATCH')
assert(/data:\s*payload/.test(update), '修改透传 payload')
assert(/auth:\s*true/.test(update), '修改启用 JWT')

const finalize = exportedFunction('finalizeJourneyRecord')
assert(/path:\s*`\/plans\/\$\{planId\}\/journey-record\/finalize`/.test(finalize), 'finalize path 正确')
assert(/method:\s*['"]POST['"]/.test(finalize), 'finalize 使用 POST')
assert(!/data\s*:/.test(finalize), 'finalize 不发送 body')
assert(/auth:\s*true/.test(finalize), 'finalize 启用 JWT')

const status = execFileSync('git', ['status', '--porcelain'], { cwd: root, encoding: 'utf8' })
  .split(/\r?\n/)
  .filter(Boolean)
  .map((line) => line.slice(3))
assert(status.length === allowedChangedFiles.size, 'Git 状态恰好包含两个目标文件')
assert(new Set(status).size === status.length && status.every((file) => allowedChangedFiles.has(file)), '本阶段未修改页面、store、后端或无关文件')

console.log('phase5c1 journey record API checks passed')
