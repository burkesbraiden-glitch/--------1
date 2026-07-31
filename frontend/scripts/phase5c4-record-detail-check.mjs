import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const storePath = join(root, 'src/stores/record.js')
const listPath = join(root, 'src/pages/record/index.vue')
const detailPath = join(root, 'src/pages/record-detail/index.vue')
const pagesPath = join(root, 'src/pages.json')
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

function codeMask(source) {
  let result = ''
  let state = 'code'

  for (let index = 0; index < source.length; index += 1) {
    const character = source[index]
    const next = source[index + 1]

    if (state === 'code') {
      if (character === '/' && next === '/') {
        result += '  '
        index += 1
        state = 'line-comment'
      } else if (character === '/' && next === '*') {
        result += '  '
        index += 1
        state = 'block-comment'
      } else if (character === '\'' || character === '"') {
        result += character
        state = character
      } else if (character === '`') {
        result += character
        state = 'template'
      } else {
        result += character
      }
      continue
    }

    if (state === 'line-comment') {
      result += character === '\n' ? '\n' : ' '
      if (character === '\n') state = 'code'
      continue
    }

    if (state === 'block-comment') {
      if (character === '*' && next === '/') {
        result += '  '
        index += 1
        state = 'code'
      } else {
        result += character === '\n' ? '\n' : ' '
      }
      continue
    }

    if (state === 'template') {
      result += character === '\n' || character === '`' ? character : ' '
      if (character === '`') state = 'code'
      continue
    }

    if (character === '\\') {
      result += ' '
      if (next) {
        result += next === '\n' ? '\n' : ' '
        index += 1
      }
      continue
    }

    result += character === '\n' || character === state ? character : ' '
    if (character === state) state = 'code'
  }

  return result
}

function namedImportSet(source, modulePath) {
  const maskedSource = codeMask(source)
  const importPattern = /^\s*import\s*\{([\s\S]*?)\}\s*from\s*(['"])[\s]*\2\s*;?/gm
  let match

  while ((match = importPattern.exec(maskedSource))) {
    const rawImport = source.slice(match.index, importPattern.lastIndex)
    const expectedPath = new RegExp(`from\\s*['"]${modulePath.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}['"]\\s*;?$`)
    if (!expectedPath.test(rawImport.trim())) {
      continue
    }

    return new Set(
      match[1]
        .split(',')
        .map((item) => item.trim().split(/\s+as\s+/)[0])
        .filter(Boolean),
    )
  }

  return new Set()
}

const store = read(storePath)
const list = read(listPath)
const detail = read(detailPath)
const pages = JSON.parse(read(pagesPath))

const route = pages.pages.find((page) => page.path === 'pages/record-detail/index')
assert(route?.style?.navigationStyle === 'custom', 'record detail route uses custom navigation')
assert(!Object.prototype.hasOwnProperty.call(route?.style || {}, 'navigationBarTitleText'), 'record detail does not add a system title')

assert(/@click="openRecordDetail\(record\)"/.test(list), 'record cards open their corresponding detail')
assert(/hover-class="record-card--pressed"/.test(list), 'record cards provide a uni-app press response')
const openRecordDetail = methodSource(list, 'openRecordDetail')
assert(/Number\.isInteger\(planId\)\s*&&\s*planId\s*>\s*0/.test(openRecordDetail), 'record detail navigation validates planId')
assert(/url:\s*`\/pages\/record-detail\/index\?planId=\$\{planId\}`/.test(openRecordDetail), 'record detail navigation sends only planId')
assert(!/record\.id/.test(openRecordDetail), 'record detail navigation does not use recordId')
assert(!/fetchJourneyRecord|fetchJourneyRecords|createJourneyRecord|updateJourneyRecord|finalizeJourneyRecord/.test(openRecordDetail), 'record page does not request detail or write data')
assert(/<AiPet\s*\/>/.test(list) && /<AppTabbar active="record"\s*\/>/.test(list), 'record list keeps AiPet and AppTabbar')

const journeyRecordClients = namedImportSet(store, '../api/journeyRecords.js')
assert(journeyRecordClients.has('fetchJourneyRecords') && journeyRecordClients.has('fetchJourneyRecord'), 'record store imports the list and detail GET clients')
assert(journeyRecordClients.has('updateJourneyRecord') && journeyRecordClients.has('finalizeJourneyRecord'), 'record store imports the draft-save and finalize write clients')
const loadList = methodSource(store, 'loadJourneyRecords')
assert(/fetchJourneyRecords\(query\)/.test(loadList), 'record list loader uses the GET list client')
assert(!/\b(?:createJourneyRecord|updateJourneyRecord|finalizeJourneyRecord)\b/.test(loadList), 'record list loader does not call JourneyRecord write APIs')
for (const field of ['currentRecord', 'detailLoading', 'detailError', 'detailHasLoaded', 'detailRequestId', 'detailPlanId', 'detailImageResources']) {
  assert(new RegExp(`\\b${field}\\b`).test(store), `record store owns ${field}`)
}
for (const action of ['loadJourneyRecordDetail', 'retryJourneyRecordDetail', 'clearJourneyRecordDetail']) {
  methodSource(store, action)
}
const loadDetail = methodSource(store, 'loadJourneyRecordDetail')
assert(/Number\.isInteger\(validPlanId\)\s*&&\s*validPlanId\s*>\s*0/.test(loadDetail), 'detail loader validates planId before requesting')
assert(/fetchJourneyRecord\(validPlanId\)/.test(loadDetail), 'detail loader uses the GET detail client with planId')
assert(!/\b(?:createJourneyRecord|updateJourneyRecord|finalizeJourneyRecord)\b/.test(loadDetail), 'detail loader does not call JourneyRecord write APIs')
assert(/data\?\.journeyRecord/.test(loadDetail), 'detail loader unwraps data.journeyRecord')
assert(/Array\.isArray\(data\?\.journeyRecord\?\.entries\)/.test(loadDetail), 'detail loader rejects a malformed entries payload')
assert(/detailRequestId/.test(loadDetail) && /!==\s*requestId/.test(loadDetail), 'detail loader blocks stale request writes')
assert(/mapJourneyRecordDetail/.test(store), 'detail store maps the real JourneyRecord detail payload')
assert(/entries/.test(store) && /displayImage/.test(store), 'detail store maps real entries and display images')
assert(/downloadAuthenticatedFile/.test(store), 'detail store reuses authenticated image downloads')
assert(/detailImageResources/.test(store) && /Map\(\)/.test(store), 'detail images use an independent URL-keyed Map')
assert(/DETAIL_IMAGE_CONCURRENCY\s*=\s*3/.test(store), 'detail image downloads cap concurrency at three')
assert(/resource\?\.cleanup\?\.\(\)/.test(store), 'stale detail image downloads release their resources')
const clearDetail = methodSource(store, 'clearJourneyRecordDetail')
assert(/detailImageResources/.test(clearDetail) && /currentRecord\s*=\s*null/.test(clearDetail), 'detail cleanup releases only detail resources and clears detail data')
assert(!/coverResources/.test(clearDetail), 'detail cleanup does not release list covers')
const resetRecordState = methodSource(store, 'resetRecordState')
assert(/clearJourneyRecordDetail\(\)/.test(resetRecordState), 'logout reset also clears detail resources')
const saveDraft = methodSource(store, 'saveJourneyRecordDraft')
assert(/updateJourneyRecord\(validPlanId, payload\)/.test(saveDraft), 'draft save uses the independent write method')
assert(!/\bfinalizeJourneyRecord\b/.test(saveDraft), 'draft save does not finalize a JourneyRecord')
const finalizeDraft = methodSource(store, 'finalizeJourneyRecordDraft')
assert(/finalizeJourneyRecord\(validPlanId\)/.test(finalizeDraft), 'record finalize uses the independent write method')
assert(!/\bupdateJourneyRecord\b/.test(finalizeDraft), 'record finalize does not save a JourneyRecord draft')

assert(/onLoad\(options\)/.test(detail) && /loadJourneyRecordDetail/.test(detail), 'detail loads only from onLoad')
assert(/onUnload\(\)/.test(detail) && /clearJourneyRecordDetail/.test(detail), 'detail unload clears detail resources')
assert(!/async\s+onShow\s*\(/.test(detail), 'detail does not duplicate loading from onShow')
assert(/return\s+this\.recordStore\.detailLoading\s*&&\s*!this\.record\s*(?:\r?\n|;)/.test(detail), 'detail retry keeps a visible loading state when no record exists')
assert(/这份旅行记录暂时无法打开/.test(detail), 'detail handles invalid planId without a request')
assert(/正在翻开旅行手账/.test(detail), 'detail has a loading state')
assert(/旅行记录加载失败/.test(detail) && /retryJourneyRecordDetail/.test(detail), 'detail has error and retry states')
assert(/displayCoverImage/.test(detail) && /entry\.displayImage/.test(detail), 'detail binds only processed image display fields')
assert(!/:src="(?:record\.)?(?:coverImageUrl|imageUrl)"/.test(detail), 'detail never binds protected source URLs directly')
assert(/entry\.title/.test(detail) && /entry\.subtitle/.test(detail) && /entry\.note/.test(detail) && /entry\.completedAt/.test(detail), 'detail renders real entry fields')
assert(/这份旅行记录里还没有可展示的任务内容/.test(detail), 'detail has an empty entries state')
assert(/这份旅行记录已经封存/.test(detail), 'detail has a finalized read-only notice')
assert(/<AiPet\s*\/>/.test(detail), 'detail keeps AiPet')
assert(!/AppTabbar/.test(detail), 'detail does not render AppTabbar')
const executableDetail = codeMask(detail)
assert(!/\b(?:createJourneyRecord|updateJourneyRecord|finalizeJourneyRecord|PATCH|POST)\b/.test(executableDetail), 'detail does not create a JourneyRecord or call write clients directly')
assert(/<view\s+v-if="record\.status === 'draft'"\s+class="record-detail-editor">/.test(detail), 'draft records alone render the editable fields')
assert(/<view\s+v-if="record\.status === 'draft'"\s+class="record-detail-finalize-action">/.test(detail), 'draft records alone render the finalize entry')
const saveDraftChanges = methodSource(detail, 'saveDraftChanges')
assert(/if\s*\(!this\.record\s*\|\|\s*this\.record\.status\s*!==\s*'draft'\s*\|\|\s*this\.saving\s*\|\|\s*this\.finalizing\)\s*\{\s*return/.test(saveDraftChanges), 'draft save rejects finalized and busy records before writing')
assert(/this\.recordStore\.saveJourneyRecordDraft\(this\.routePlanId, changes\)/.test(saveDraftChanges) && /this\.syncDraftFromRecord\(result\.journeyRecord\)/.test(saveDraftChanges), 'draft save delegates to the store and uses its returned record')
const confirmFinalizeRecord = methodSource(detail, 'confirmFinalizeRecord')
assert(/if\s*\(!this\.record\s*\|\|\s*this\.record\.status\s*!==\s*'draft'\s*\|\|\s*this\.saving\s*\|\|\s*this\.finalizing\)\s*\{\s*return/.test(confirmFinalizeRecord), 'finalize entry rejects finalized and busy records before confirmation')
const finalizeRecord = methodSource(detail, 'finalizeRecord')
assert(/if\s*\(!this\.record\s*\|\|\s*this\.record\.status\s*!==\s*'draft'\s*\|\|\s*this\.saving\s*\|\|\s*this\.finalizing\)\s*\{\s*return/.test(finalizeRecord) && /this\.recordStore\.finalizeJourneyRecordDraft\(this\.routePlanId\)/.test(finalizeRecord), 'finalize rejects invalid states and delegates to the store')
assert(/<view\s+v-if="record\.status === 'finalized'"\s+class="record-detail-finalized">/.test(detail), 'finalized records render a read-only branch')
assert(!/\b(?:this\.)?record\.status\s*=(?!=)/.test(executableDetail) && !/\b(?:this\.)?record\.finalizedAt\s*=(?!=)/.test(executableDetail) && !/\b(?:new\s+Date|Date\.now)\s*\(/.test(executableDetail), 'detail never fabricates finalized state or finalizedAt on the client')

const goBack = methodSource(detail, 'goBack')
assert(/getCurrentPages\s*\(\s*\)/.test(goBack), 'record detail return must inspect the uni-app page stack before navigateBack')
const backToRecordList = methodSource(detail, 'backToRecordList')
assert(/Array\.isArray\(pages\)\s*&&\s*pages\.length\s*>\s*1/.test(goBack), 'record detail returns through navigateBack only when the page stack has a previous page')
assert(/uni\.navigateBack\s*\(\s*\{[\s\S]*?delta\s*:\s*1/.test(goBack), 'record detail returns one page when a previous page exists')
assert(/fail\s*:\s*\(\)\s*=>\s*this\.backToRecordList\(\)/.test(goBack), 'record detail navigateBack failure uses the safe record list return')
assert(/this\.backToRecordList\(\)/.test(goBack), 'record detail direct entry uses the safe record list return')
assert(/uni\.switchTab\s*\(\s*\{[\s\S]*?url\s*:\s*['"]\/pages\/record\/index['"]/.test(backToRecordList), 'record detail safe return switches to the record tab')
assert(!/\b(?:window\.history|history\.back|setTimeout)\b/.test(`${goBack}\n${backToRecordList}`), 'record detail return does not use browser history or timing workarounds')

console.log('phase5c4 record detail checks passed')
