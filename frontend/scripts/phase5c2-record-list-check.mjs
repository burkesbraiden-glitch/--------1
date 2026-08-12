import { execFileSync } from 'node:child_process'
import { readFileSync, readdirSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const storePath = join(root, 'src/stores/record.js')
const pagePath = join(root, 'src/pages/record/index.vue')
const profilePath = join(root, 'src/pages/profile/index.vue')
const allowedChangedFiles = new Set([
  'frontend/scripts/phase5c2-record-list-check.mjs',
  'frontend/src/stores/record.js',
  'frontend/src/pages/record/index.vue',
  'frontend/src/pages/profile/index.vue',
])

const removedRecordFields = [
  'discoveries',
  'currentJourneyRecord',
  'generateJourneyRecord',
  'recordJourney',
  'mockRecords',
  'growthSkills',
]

function listVueFiles(directory) {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const entryPath = join(directory, entry.name)
    if (entry.isDirectory()) {
      return listVueFiles(entryPath)
    }
    return entry.isFile() && entry.name.endsWith('.vue') ? [entryPath] : []
  })
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message)
  }
  console.log(`PASS: ${message}`)
}

function actionBody(source, actionName) {
  const match = new RegExp(`(?:async\\s+)?${actionName}\\s*\\([^)]*\\)\\s*\\{`).exec(source)
  if (!match) {
    return ''
  }

  let depth = 0
  const bodyStart = match.index + match[0].length - 1
  for (let index = bodyStart; index < source.length; index += 1) {
    if (source[index] === '{') depth += 1
    if (source[index] === '}') depth -= 1
    if (depth === 0) return source.slice(match.index, index + 1)
  }
  return ''
}

const store = readFileSync(storePath, 'utf8')
const page = readFileSync(pagePath, 'utf8')
const profile = readFileSync(profilePath, 'utf8')

assert(!/record\.discoveries|this\.record\.discoveries|currentJourneyRecord|generateJourneyRecord|recordJourney|mockRecords|record\.growthSkills|this\.record\.growthSkills/.test(profile), 'profile/index.vue does not reference removed Record Store fields')

const listAction = actionBody(store, 'loadJourneyRecords')
assert(/import\s*\{[\s\S]*?\bfetchJourneyRecords\b[\s\S]*?\}\s*from\s*['"]\.\.\/api\/journeyRecords\.js['"]/.test(store), 'record store imports the JourneyRecord list client')
assert(/\bfetchJourneyRecords\s*\(\s*query\s*\)/.test(listAction), 'loadJourneyRecords calls the JourneyRecord list client')
assert(!/\b(?:fetchJourneyRecord|updateJourneyRecord|finalizeJourneyRecord)\s*\(/.test(listAction), 'loadJourneyRecords remains scoped to list loading')
assert(!/mock\/records|recordJourney\.mjs|generateJourneyRecord|usePlanStore|useTaskStore/.test(store), 'record store 已切断 Mock、计划和任务聚合')
assert(/records:\s*\[\]/.test(store), 'record store 存储真实 records')
assert(/total:\s*0/.test(store) && /limit:\s*20/.test(store) && /offset:\s*0/.test(store), 'record store 保存分页元数据')
assert(/loading:\s*false/.test(store) && /error:\s*null/.test(store) && /hasLoaded:\s*false/.test(store), 'record store 具有加载、错误和已加载状态')
assert(/latestRequestId/.test(store) && /lastQuery/.test(store), 'record store 具有过期请求保护和重试 query')
assert(/coverResources/.test(store) && /downloadAuthenticatedFile/.test(store), 'record store 复用认证封面下载与资源缓存')
assert(/loadJourneyRecords\s*\(/.test(store) && /retryJourneyRecords\s*\(/.test(store) && /resetRecordState\s*\(/.test(store), 'record store 提供加载、重试和重置 action')
assert(/Array\.isArray\(data\?\.items\)/.test(store), 'record store 正确解包 data.items')
assert(/latestRequestId\s*!==\s*requestId/.test(store), 'record store 阻止过期响应回写')
assert(/activeLoadPromise/.test(store), 'record store 阻止重复并发加载')
assert(/catch\s*\(error\)/.test(store) && !/catch\s*\(error\)\s*\{\s*return\s*\[\]/.test(store), '失败不会伪造空列表')

assert(/async\s+onShow\s*\(/.test(page) && /loadJourneyRecords/.test(page), '记录页 onShow 调用真实列表加载')
assert(!/generateJourneyRecord|currentJourneyRecord|mockRecords|usePlanStore|useTaskStore|ensureCurrentPlanReady|restoreTaskImages/.test(page), '记录页已切断 Mock、计划和任务聚合')
assert(/正在整理旅行记录/.test(page), '记录页存在首次加载状态')
assert(/旅行记录暂时加载失败/.test(page) && /重新加载/.test(page), '记录页存在错误与重试状态')
assert(/还没有旅行记录/.test(page), '记录页存在真实空状态')
assert(/v-for="\(record, index\) in records"/.test(page), '记录页循环渲染真实列表')
assert(/record\.displayTitle/.test(page) && /record\.destination/.test(page), '记录页使用真实标题与目的地')
assert(/record\.taskCount/.test(page) && /record\.completedTaskCount/.test(page) && /record\.photoCount/.test(page) && /record\.noteCount/.test(page), '记录页使用真实统计字段')
assert(/record\.status === 'draft'/.test(page) && /record\.status === 'finalized'/.test(page), '记录页区分 draft 和 finalized')
assert(/record\.displayCoverImage/.test(page), '记录页使用认证封面显示字段')
assert(/<AppTabbar active="record"\s*\/>/.test(page), '记录页保留 AppTabbar')

assert(/getters\s*:\s*\{[\s\S]*learningRecordCount\s*\(/.test(store), 'record store provides the real JourneyRecord total getter')
assert(/Number\(state\.total\)/.test(store) && /Array\.isArray\(state\.records\)/.test(store), 'learningRecordCount prioritizes pagination total with a records fallback')
assert(!/discoveries\s*:\s*\[\]/.test(store) && !/discoveries\s*\([^)]*\)\s*\{/.test(store), 'record store does not add a discoveries compatibility shim')

assert(!/record\.discoveries|this\.record\.discoveries|currentJourneyRecord|generateJourneyRecord|recordJourney|mockRecords|record\.growthSkills|this\.record\.growthSkills/.test(profile), 'profile/index.vue does not reference removed Record Store fields')
assert(/this\.record\.learningRecordCount/.test(profile), 'profile/index.vue uses the real JourneyRecord total getter')
assert(!/fetchJourneyRecords|api\/journeyRecords/.test(profile), 'profile/index.vue does not create a second JourneyRecord request')
assert(/条旅行记录/.test(profile), 'profile record copy matches JourneyRecord count semantics')

const productionPages = listVueFiles(join(root, 'src/pages'))
const staleConsumers = productionPages.flatMap((file) => {
  const source = readFileSync(file, 'utf8')
  return removedRecordFields
    .filter((field) => new RegExp(`(?:this\\.)?record\\.${field}`).test(source))
    .map((field) => `${file}: ${field}`)
})
assert(staleConsumers.length === 0, 'no production page reads removed Record Store fields')

console.log('phase5c2 record list checks passed')
