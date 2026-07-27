import { execFileSync } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const frontendRoot = join(dirname(fileURLToPath(import.meta.url)), '..')
const repositoryRoot = join(frontendRoot, '..')
const storePath = join(frontendRoot, 'src/stores/record.js')
const detailPath = join(frontendRoot, 'src/pages/record-detail/index.vue')
const allowedChangedFiles = new Set([
  'frontend/scripts/phase5c4-record-finalize-check.mjs',
  'frontend/src/pages/record-detail/index.vue',
  'frontend/src/stores/record.js',
])

function assert(condition, message) {
  if (!condition) throw new Error(message)
  console.log(`PASS: ${message}`)
}

function read(path) {
  assert(existsSync(path), `${path} exists`)
  return readFileSync(path, 'utf8')
}

function methodSource(source, name) {
  const match = source.match(new RegExp(`(?:async\\s+)?${name}\\s*\\([^)]*\\)\\s*\\{`, 'm'))
  assert(match, `${name} method exists`)
  const start = match.index + match[0].length
  let depth = 1
  for (let index = start; index < source.length; index += 1) {
    if (source[index] === '{') depth += 1
    if (source[index] === '}') depth -= 1
    if (depth === 0) return source.slice(match.index, index + 1)
  }
  throw new Error(`${name} method must close correctly`)
}

const store = read(storePath)
const detail = read(detailPath)

assert(/import\s*\{\s*fetchJourneyRecords\s*,\s*fetchJourneyRecord\s*,\s*updateJourneyRecord\s*,\s*finalizeJourneyRecord\s*\}\s*from\s*['"]\.\.\/api\/journeyRecords\.js['"]/.test(store), 'record store imports finalizeJourneyRecord from the existing JourneyRecord client')
assert(!/\bcreateJourneyRecord\b/.test(store), 'record store does not add JourneyRecord creation behavior')
assert(/\bfinalizing\s*:\s*false/.test(store) && /\bfinalizeError\s*:\s*null/.test(store) && /\bfinalizeRequestId\s*:\s*0/.test(store), 'record store owns isolated finalize state')

const saveDraft = methodSource(store, 'saveJourneyRecordDraft')
assert(/this\.finalizing/.test(saveDraft) && /reason:\s*['"]finalizing['"]/.test(saveDraft), 'draft saves are blocked while finalizing')
const finalizeDraft = methodSource(store, 'finalizeJourneyRecordDraft')
assert(/normalizePlanId/.test(finalizeDraft) && /currentRecord/.test(finalizeDraft) && /status\s*!==\s*['"]draft['"]/.test(finalizeDraft), 'finalize action validates the active draft record')
assert(/this\.saving/.test(finalizeDraft) && /this\.finalizing/.test(finalizeDraft), 'finalize action prevents save and finalize concurrency')
assert(/finalizeJourneyRecord\(validPlanId\)/.test(finalizeDraft), 'finalize action calls the existing API with only the plan id')
assert(!/finalizeJourneyRecord\([^)]*,/.test(finalizeDraft), 'finalize action does not send editable fields or a request body')
assert(/data\?\.journeyRecord/.test(finalizeDraft) && /data\?\.finalizedNow/.test(finalizeDraft), 'finalize action reads the server record and finalizedNow')
assert(/mapJourneyRecordDetail/.test(finalizeDraft) && /syncJourneyRecordListItem/.test(finalizeDraft), 'finalize action maps the server response and synchronizes its list item')
assert(!/fetchJourneyRecord\(/.test(finalizeDraft), 'finalize action does not perform an extra detail GET')
assert(!/new Date\(|Date\.now\(/.test(finalizeDraft), 'finalize action never generates finalizedAt on the client')
assert(/this\.finalizeError/.test(finalizeDraft) && /this\.finalizing\s*=\s*false/.test(finalizeDraft), 'finalize failures stay isolated and release finalizing')
assert(/this\.finalizeRequestId === finalizeRequestId/.test(finalizeDraft), 'only the active finalize request can update finalize state')

const clearDetail = methodSource(store, 'clearJourneyRecordDetail')
assert(/this\.finalizeRequestId\s*\+=\s*1/.test(clearDetail) && /this\.finalizing\s*=\s*false/.test(clearDetail) && /this\.finalizeError\s*=\s*null/.test(clearDetail), 'detail cleanup resets finalize state safely')

assert(/finalizing\(\)\s*\{\s*return this\.recordStore\.finalizing/.test(detail), 'record detail exposes finalizing state')
assert(/finalizeError\(\)\s*\{\s*return this\.recordStore\.finalizeError/.test(detail), 'record detail keeps finalize errors separate from detail errors')
assert(/:disabled="!hasDraftChanges \|\| saving \|\| finalizing"/.test(detail), 'save button is disabled while finalizing')
assert(/v-if="record\.status === 'draft'"[\s\S]*?封存这份旅行记录/.test(detail), 'only draft records render the finalize entry')
assert(/:disabled="saving \|\| finalizing"/.test(detail), 'finalize button is disabled while saving or finalizing')

const confirmFinalize = methodSource(detail, 'confirmFinalizeRecord')
assert(/uni\.showModal\(/.test(confirmFinalize), 'finalize entry opens a uni.showModal confirmation')
assert(/title:\s*['"]确认封存['"]/.test(confirmFinalize) && /封存后将不能再修改标题、摘要和封面/.test(confirmFinalize), 'confirmation explains the permanent read-only consequence')
assert(/confirmText:\s*['"]确认封存['"]/.test(confirmFinalize) && /cancelText:\s*['"]再想想['"]/.test(confirmFinalize), 'confirmation provides clear confirm and cancel actions')
assert(/if\s*\(result\.confirm\)\s*\{\s*this\.finalizeRecord\(\)/.test(confirmFinalize), 'only confirmation invokes the finalize action')
assert(!/window\.confirm/.test(detail) && !/setTimeout|setInterval/.test(confirmFinalize), 'finalize confirmation uses neither browser confirm nor timers')

const finalizePage = methodSource(detail, 'finalizeRecord')
assert(/record\.status !== ['"]draft['"]/.test(finalizePage) && /this\.saving \|\| this\.finalizing/.test(finalizePage), 'page finalize action protects non-draft and busy states')
assert(/finalizeJourneyRecordDraft\(this\.routePlanId\)/.test(finalizePage), 'page delegates one finalize request to the record store')
assert(/旅行记录已封存/.test(finalizePage) && /finalizeErrorMessage/.test(detail), 'page provides success and safe failure feedback')
assert(!/finalizeJourneyRecordDraft/.test(methodSource(detail, 'loadDetail')) && !/finalizeJourneyRecordDraft/.test(methodSource(detail, 'syncDraftFromRecord')), 'page never finalizes while loading or watching data')
assert(/record\.displayFinalizedAt/.test(detail) && /这份旅行记录已经封存/.test(detail), 'finalized page displays server finalized time and a read-only notice')
assert(!/AppTabbar/.test(detail) && /<AiPet\s*\/>/.test(detail), 'detail keeps AiPet without AppTabbar')

const status = execFileSync('git', ['status', '--porcelain', '--untracked-files=all'], { cwd: repositoryRoot, encoding: 'utf8' })
  .split(/\r?\n/)
  .filter(Boolean)
  .map((line) => line.slice(3))
assert(status.length === allowedChangedFiles.size, 'Git status contains exactly the three phase 5C-4.3 files')
assert(new Set(status).size === status.length && status.every((file) => allowedChangedFiles.has(file)), 'no protected or unrelated file changed')

console.log('phase5c4 record finalize checks passed')
