import { execFileSync } from 'node:child_process'
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const pagePath = join(root, 'src/pages/task-detail/index.vue')
const allowedChangedFiles = new Set([
  'frontend/scripts/phase5c3-journey-record-sync-check.mjs',
  'frontend/src/pages/task-detail/index.vue',
])

function assert(condition, message) {
  if (!condition) {
    throw new Error(message)
  }
  console.log(`PASS: ${message}`)
}

function methodSource(source, name) {
  const match = source.match(new RegExp(`(?:async\\s+)?${name}\\s*\\([^)]*\\)\\s*\\{`, 'm'))
  assert(match, `${name} 方法存在`)

  const start = match.index + match[0].length
  let depth = 1
  for (let index = start; index < source.length; index += 1) {
    if (source[index] === '{') {
      depth += 1
    } else if (source[index] === '}') {
      depth -= 1
      if (depth === 0) {
        return source.slice(match.index, index + 1)
      }
    }
  }

  throw new Error(`${name} 方法未正确闭合`)
}

const page = readFileSync(pagePath, 'utf8')

assert(
  /import\s*\{\s*createJourneyRecord\s*\}\s*from\s*['"]\.\.\/\.\.\/api\/journeyRecords\.js['"]/.test(page),
  'task-detail/index.vue 从既有 JourneyRecord API 导入 createJourneyRecord',
)
assert(!/\b(?:request|uni\.request|fetch)\s*\(/.test(page), 'task-detail/index.vue 不直接发起 JourneyRecord 请求')
assert(
  !/\b(?:fetchJourneyRecords|fetchJourneyRecord|updateJourneyRecord|finalizeJourneyRecord)\b/.test(page),
  'task-detail/index.vue 不调用 JourneyRecord 列表、详情、修改或封存 API',
)

const completeTask = methodSource(page, 'completeTask')
const syncJourneyRecordAfterCompletion = methodSource(page, 'syncJourneyRecordAfterCompletion')
const createCalls = page.match(/\bcreateJourneyRecord\s*\(/g) || []
assert(createCalls.length === 1, '页面仅有一个 JourneyRecord 创建调用入口')
assert(/await\s+createJourneyRecord\s*\(\s*validPlanId\s*\)/.test(syncJourneyRecordAfterCompletion), '同步 helper 使用已验证的真实 planId 创建 JourneyRecord')
assert(/Number\.isInteger\s*\(\s*validPlanId\s*\)\s*&&\s*validPlanId\s*>\s*0/.test(syncJourneyRecordAfterCompletion), '同步 helper 校验 planId')
assert(/catch\s*\(\s*error\s*\)\s*\{[\s\S]*?return\s+null\s*;?[\s\S]*?\}/.test(syncJourneyRecordAfterCompletion), '同步 helper 捕获失败且不向任务完成流程抛出')
assert(!/\bthrow\b/.test(syncJourneyRecordAfterCompletion), '同步 helper 不抛出 JourneyRecord 同步错误')

const completeRequestIndex = completeTask.search(/await\s+this\.task\.completeTaskSubmission\s*\(/)
const syncCallIndex = completeTask.search(/void\s+this\.syncJourneyRecordAfterCompletion\s*\(\s*task\.planId\s*\)/)
assert(completeRequestIndex >= 0, 'completeTask 保留原有 TaskSubmission 完成请求')
assert(syncCallIndex > completeRequestIndex, 'JourneyRecord 同步只发生在 TaskSubmission 完成成功之后')
assert(/if\s*\(\s*task\s*\)\s*\{[\s\S]*?void\s+this\.syncJourneyRecordAfterCompletion\s*\(\s*task\.planId\s*\)/.test(completeTask), 'JourneyRecord 同步使用完成任务返回的 planId')
assert(!/await\s+this\.syncJourneyRecordAfterCompletion\s*\(/.test(completeTask), 'completeTask 不阻塞等待 JourneyRecord 同步')
assert(!/createJourneyRecord\s*\(/.test(completeTask), 'completeTask 不直接创建 JourneyRecord')

for (const method of ['onLoad', 'onShow', 'chooseImage', 'uploadSelectedImage', 'saveNoteNow']) {
  assert(!/createJourneyRecord|syncJourneyRecordAfterCompletion/.test(methodSource(page, method)), `${method} 不触发 JourneyRecord 创建`)
}
assert(!/catch\s*\([^)]*\)\s*\{[\s\S]*?syncJourneyRecordAfterCompletion/.test(completeTask), '任务完成失败分支不触发 JourneyRecord 同步')
assert(!/finally\s*\{[\s\S]*?syncJourneyRecordAfterCompletion/.test(completeTask), '任务完成 finally 不触发 JourneyRecord 同步')

const status = execFileSync('git', ['status', '--porcelain'], { cwd: root, encoding: 'utf8' })
  .split(/\r?\n/)
  .filter(Boolean)
  .map((line) => line.slice(3))
assert(status.length === allowedChangedFiles.size, 'Git 状态恰好包含两个目标文件')
assert(new Set(status).size === status.length && status.every((file) => allowedChangedFiles.has(file)), '本阶段未修改 API、store、页面路由、依赖或后端')

console.log('phase5c3 journey record sync checks passed')
