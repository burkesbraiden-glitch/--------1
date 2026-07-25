import { execFileSync } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const frontendRoot = join(dirname(fileURLToPath(import.meta.url)), '..')
const repositoryRoot = join(frontendRoot, '..')
const storePath = join(frontendRoot, 'src/stores/record.js')
const detailPath = join(frontendRoot, 'src/pages/record-detail/index.vue')
const allowedChangedFiles = new Set([
  'frontend/scripts/phase5c4-record-edit-check.mjs',
  'frontend/src/pages/record-detail/index.vue',
  'frontend/src/stores/record.js',
])

function assert(condition, message) {
  if (!condition) {
    throw new Error(message)
  }
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

assert(/import\s*\{\s*fetchJourneyRecords\s*,\s*fetchJourneyRecord\s*,\s*updateJourneyRecord\s*\}\s*from\s*['"]\.\.\/api\/journeyRecords\.js['"]/.test(store), 'record store imports updateJourneyRecord from the existing JourneyRecord client')
assert(!/\bfinalizeJourneyRecord\b/.test(store), 'record store does not import or call finalizeJourneyRecord')
assert(!/\b(?:request|uni\.request|fetch)\s*\(/.test(methodSource(store, 'saveJourneyRecordDraft')), 'draft save action uses only the existing JourneyRecord client')
assert(/\bsaving\s*:\s*false/.test(store) && /\bsaveError\s*:\s*null/.test(store), 'record store owns saving and saveError state')
assert(/\bsaveRequestId\s*:\s*0/.test(store), 'record store owns a save request id for page-switch races')

const saveDraft = methodSource(store, 'saveJourneyRecordDraft')
assert(/customTitle/.test(saveDraft) && /summary/.test(saveDraft) && /coverSubmissionId/.test(saveDraft), 'draft save action handles the three editable fields')
assert(/const allowedFields = \['customTitle', 'summary', 'coverSubmissionId'\]/.test(saveDraft), 'draft save action rebuilds its payload from the editable-field whitelist')
assert(/this\.saving/.test(saveDraft) && /return\s+\{\s*saved:\s*false/.test(saveDraft), 'draft save action blocks duplicate or empty saves')
assert(/status\s*!==\s*['"]draft['"]/.test(saveDraft), 'draft save action protects finalized records')
assert(/updateJourneyRecord\(validPlanId,\s*payload\)/.test(saveDraft), 'draft save action PATCHes the validated plan and payload')
assert(/mapJourneyRecordDetail/.test(saveDraft), 'draft save action reuses the detail mapping')
const syncListItem = methodSource(store, 'syncJourneyRecordListItem')
assert(/this\.records/.test(syncListItem) && /loadRecordCover/.test(syncListItem) && /cleanupCoverResource/.test(syncListItem), 'draft save action synchronizes the corresponding record list card and its cover resource')
assert(/this\.saveError/.test(saveDraft) && /this\.saving\s*=\s*false/.test(saveDraft), 'draft save action keeps an explicit failure state and releases saving')
assert(/const saveRequestId = this\.saveRequestId \+ 1/.test(saveDraft) && /this\.saveRequestId === saveRequestId/.test(saveDraft), 'only the active save request can release the saving lock or write a save error')

for (const field of ['customTitleDraft', 'summaryDraft', 'selectedCoverSubmissionId', 'draftInitializedPlanId']) {
  assert(new RegExp(`\\b${field}\\b`).test(detail), `record detail owns local ${field}`)
}
assert(/<input[\s\S]*?v-model="customTitleDraft"[\s\S]*?maxlength="120"/.test(detail), 'draft title uses a 120-character single-line input')
assert(/<textarea[\s\S]*?v-model="summaryDraft"[\s\S]*?maxlength="2000"/.test(detail), 'draft summary uses a 2000-character textarea')
assert(/summaryDraft\.length\s*}}\s*\/\s*2000/.test(detail), 'draft summary shows its character count')
assert(/coverCandidates/.test(detail) && /entry\.submissionId/.test(detail) && /entry\.imageUrl/.test(detail), 'cover candidates derive from pictured entries using submissionId')
assert(/entry\.displayImage/.test(detail) && !/:src="entry\.imageUrl"/.test(detail), 'cover candidates bind processed image paths only')
assert(/完成带照片的观察任务后，就可以选择旅行记录封面。/.test(detail), 'draft editor has a no-cover-candidates hint')
assert(/清除封面/.test(detail) && /selectedCoverSubmissionId\s*=\s*null/.test(detail), 'draft editor can clear the explicit cover')

const buildChanges = methodSource(detail, 'buildDraftChanges')
assert(/customTitle/.test(buildChanges) && /summary/.test(buildChanges) && /coverSubmissionId/.test(buildChanges), 'page builds a three-field draft payload')
assert(/Object\.keys\(this\.buildDraftChanges\(\)\)\.length/.test(detail), 'page derives draft-change state from the payload')
const saveChanges = methodSource(detail, 'saveDraftChanges')
assert(/saveJourneyRecordDraft\(this\.routePlanId,\s*changes\)/.test(saveChanges), 'page delegates one unified save to the record store')
assert(/旅行记录已保存/.test(detail) && /保存失败，请稍后重试/.test(detail), 'page provides clear save feedback')
assert(/v-if="record\.status === 'draft'"/.test(detail), 'finalized records do not render the draft editor')
assert(/recordStore\.saveError/.test(detail) && !/detailError\s*=\s*this\.recordStore\.saveError/.test(detail), 'save errors stay separate from detail loading errors')
assert(/<AiPet\s*\/>/.test(detail), 'record detail retains AiPet')
assert(!/AppTabbar/.test(detail), 'record detail does not add AppTabbar')
assert(!/\bfinalizeJourneyRecord\b/.test(detail), 'record detail has no finalize behavior')

const status = execFileSync('git', ['status', '--porcelain', '--untracked-files=all'], { cwd: repositoryRoot, encoding: 'utf8' })
  .split(/\r?\n/)
  .filter(Boolean)
  .map((line) => line.slice(3))
assert(status.length === allowedChangedFiles.size, 'Git status contains exactly the three phase 5C-4.2 files')
assert(new Set(status).size === status.length && status.every((file) => allowedChangedFiles.has(file)), 'no protected or unrelated file changed')

console.log('phase5c4 record edit checks passed')
