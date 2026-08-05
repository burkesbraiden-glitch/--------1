import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const helperRelativePath = 'src/utils/sessionBoundary.js'
const helperPath = join(root, helperRelativePath)
const loginPath = '/pages/login/index'

function assert(condition, message) {
  if (!condition) {
    throw new Error(message)
  }
}

function read(relativePath) {
  return readFileSync(join(root, relativePath), 'utf8')
}

// Keep source offsets stable while removing non-code text. This lets checks inspect
// real branches without allowing comments or string literals to satisfy them.
function maskComments(source, { maskStrings = false } = {}) {
  let output = ''
  let index = 0
  let state = 'code'

  const blank = (character) => (character === '\n' || character === '\r' ? character : ' ')

  while (index < source.length) {
    const character = source[index]
    const next = source[index + 1]

    if (state === 'code') {
      if (character === '/' && next === '/') {
        output += '  '
        index += 2
        state = 'line-comment'
        continue
      }
      if (character === '/' && next === '*') {
        output += '  '
        index += 2
        state = 'block-comment'
        continue
      }
      if (character === "'" || character === '"' || character === '`') {
        output += maskStrings ? character : character
        index += 1
        state = character === "'" ? 'single-quote' : character === '"' ? 'double-quote' : 'template'
        continue
      }
      output += character
      index += 1
      continue
    }

    if (state === 'line-comment') {
      output += blank(character)
      index += 1
      if (character === '\n') state = 'code'
      continue
    }

    if (state === 'block-comment') {
      if (character === '*' && next === '/') {
        output += '  '
        index += 2
        state = 'code'
        continue
      }
      output += blank(character)
      index += 1
      continue
    }

    const quote = state === 'single-quote' ? "'" : state === 'double-quote' ? '"' : '`'
    if (character === '\\') {
      output += maskStrings ? ' ' : character
      output += index + 1 < source.length ? blank(source[index + 1]) : ''
      index += 2
      continue
    }
    if (character === quote) {
      output += maskStrings ? quote : character
      index += 1
      state = 'code'
      continue
    }
    output += maskStrings ? blank(character) : character
    index += 1
  }

  return output
}

function codeMask(source) {
  return maskComments(source, { maskStrings: true })
}

function importsFrom(source, moduleCandidates) {
  const candidates = new Set(moduleCandidates)
  const imports = new Set()
  const importSource = maskComments(source)
  const pattern = /^\s*import\s*\{([\s\S]*?)\}\s*from\s*(['"])([^'"\n]+)\2\s*;?/gm
  let match
  while ((match = pattern.exec(importSource))) {
    if (!candidates.has(match[3])) continue
    for (const item of match[1].split(',')) {
      const imported = item.trim().split(/\s+as\s+/)[0]?.trim()
      if (imported) imports.add(imported)
    }
  }
  return imports
}

function hasNamedImport(source, moduleCandidates, exportName) {
  return importsFrom(source, moduleCandidates).has(exportName)
}

function blockSource(source, openingBraceIndex) {
  const masked = codeMask(source)
  let depth = 0
  for (let index = openingBraceIndex; index < masked.length; index += 1) {
    if (masked[index] === '{') depth += 1
    if (masked[index] === '}') {
      depth -= 1
      if (depth === 0) return source.slice(openingBraceIndex, index + 1)
    }
  }
  return ''
}

function functionSource(source, name) {
  const masked = codeMask(source)
  const pattern = new RegExp(`(?:export\\s+)?(?:async\\s+)?function\\s+${name}\\s*\\([^)]*\\)\\s*\\{`)
  const match = pattern.exec(masked)
  if (!match) return ''
  return blockSource(source, match.index + match[0].lastIndexOf('{'))
}

function methodSource(source, name) {
  const masked = codeMask(source)
  const pattern = new RegExp(`(?:async\\s+)?${name}\\s*\\([^)]*\\)\\s*\\{`)
  const match = pattern.exec(masked)
  if (!match) return ''
  return blockSource(source, match.index + match[0].lastIndexOf('{'))
}

function ifBranches(source) {
  const masked = codeMask(source)
  const commentFree = maskComments(source)
  const branches = []
  const pattern = /\bif\s*\(/g
  let match

  while ((match = pattern.exec(masked))) {
    const openingParenthesis = match.index + match[0].lastIndexOf('(')
    let depth = 0
    let closingParenthesis = -1
    for (let index = openingParenthesis; index < masked.length; index += 1) {
      if (masked[index] === '(') depth += 1
      if (masked[index] === ')') {
        depth -= 1
        if (depth === 0) {
          closingParenthesis = index
          break
        }
      }
    }
    if (closingParenthesis < 0) continue

    let openingBrace = closingParenthesis + 1
    while (/\s/.test(masked[openingBrace] || '')) openingBrace += 1
    if (masked[openingBrace] !== '{') continue

    branches.push({
      condition: commentFree.slice(openingParenthesis + 1, closingParenthesis),
      body: blockSource(source, openingBrace),
    })
  }
  return branches
}

function hasBoundaryCall(source) {
  return /\b(?:await\s+)?endUserSession\s*\(/.test(codeMask(source))
}

function hasUnauthorizedBoundaryCall(source) {
  return ifBranches(source).some(({ condition, body }) => (
    /\b401\b|UNAUTHORIZED|INVALID_TOKEN|TOKEN_EXPIRED|isUnauthorized/.test(condition)
    && hasBoundaryCall(body)
  ))
}

function logoutMenuBranch(source) {
  return ifBranches(source).find(({ condition }) => /\bkey\s*===\s*['"]logout['"]/.test(condition))?.body || ''
}

function storeInstanceCalls(source, storeHook, actionName) {
  const masked = codeMask(source)
  if (new RegExp(`\\b${storeHook}\\s*\\(\\s*\\)\\s*\\.${actionName}\\s*\\(`).test(masked)) return true

  const instancePattern = new RegExp(`\\b(?:const|let|var)\\s+([A-Za-z_$][\\w$]*)\\s*=\\s*${storeHook}\\s*\\(`, 'g')
  let match
  while ((match = instancePattern.exec(masked))) {
    if (new RegExp(`\\b${match[1]}\\s*\\.${actionName}\\s*\\(`).test(masked)) return true
  }
  return false
}

function cleanupBeforeLoginNavigation(source) {
  const code = codeMask(source)
  const navigation = maskComments(source)
  const navigationIndex = navigation.search(/\buni\s*\.\s*reLaunch\s*\(\s*\{\s*url\s*:\s*['"]\/pages\/login\/index['"]\s*\}/)
  if (navigationIndex < 0) return false

  const cleanupPatterns = [
    /\.resetSessionState\s*\(/g,
    /\.resetRecordState\s*\(/g,
    /\.logout\s*\(/g,
  ]
  return cleanupPatterns.every((pattern) => {
    const matches = [...code.matchAll(pattern)]
    return matches.length > 0 && matches.every((match) => match.index < navigationIndex)
  })
}

function hasSingleflightGuard(source, boundary) {
  const allCode = codeMask(source)
  const body = codeMask(boundary)
  const candidates = [...allCode.matchAll(/\b(?:let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*null\b/g)]
    .map((match) => match[1])

  return candidates.some((name) => {
    const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const returnsExisting = new RegExp(`if\\s*\\(\\s*${escaped}\\s*\\)\\s*\\{?\\s*return\\s+${escaped}`).test(body)
    const assignsPromise = new RegExp(`\\b${escaped}\\s*=`).test(body)
    const releasesGuard = new RegExp(`\\b${escaped}\\s*=\\s*null`).test(body)
    return returnsExisting && assignsPromise && releasesGuard
  })
}

function verifyCheckerSamples() {
  const accepted = `
    import { endUserSession } from '../../utils/sessionBoundary.js'
    async function handleUnauthorized(error) {
      if (!isUnauthorized(error)) throw error
      await endUserSession({ reason: 'unauthorized' })
    }
  `
  const pageLocalReset = `
    async function handleUnauthorized() {
      planStore.resetSessionState()
      await userStore.logout()
      uni.reLaunch({ url: '/pages/login/index' })
    }
  `
  const recordOnlyReset = `
    async function handleUnauthorized() {
      recordStore.resetRecordState()
      await userStore.logout()
      uni.reLaunch({ url: '/pages/login/index' })
    }
  `
  const navigationFirst = `
    async function endUserSession() {
      uni.reLaunch({ url: '/pages/login/index' })
      childStore.resetSessionState()
      recordStore.resetRecordState()
      userStore.logout()
    }
  `
  const guarded = `
    let activeSessionEnd = null
    async function endUserSession() {
      if (activeSessionEnd) return activeSessionEnd
      activeSessionEnd = Promise.resolve().finally(() => { activeSessionEnd = null })
      return activeSessionEnd
    }
  `
  const commentsAndStrings = `
    // await endUserSession({ reason: 'unauthorized' })
    const note = 'endUserSession()'
    async function handleUnauthorized() { return false }
  `

  assert(
    hasNamedImport(accepted, ['../../utils/sessionBoundary.js'], 'endUserSession') && hasBoundaryCall(functionSource(accepted, 'handleUnauthorized')),
    'self-sample: valid shared boundary path must be accepted',
  )
  assert(!hasBoundaryCall(functionSource(pageLocalReset, 'handleUnauthorized')), 'self-sample: page-local reset must be rejected')
  assert(!hasBoundaryCall(functionSource(recordOnlyReset, 'handleUnauthorized')), 'self-sample: record-only reset must be rejected')
  assert(!cleanupBeforeLoginNavigation(functionSource(navigationFirst, 'endUserSession')), 'self-sample: navigation before cleanup must be rejected')
  assert(hasSingleflightGuard(guarded, functionSource(guarded, 'endUserSession')), 'self-sample: singleflight guard must be accepted')
  assert(!hasBoundaryCall(commentsAndStrings), 'self-sample: comments and strings must not count as calls')
}

verifyCheckerSamples()

const failures = []
function requireContract(condition, message) {
  if (!condition) failures.push(message)
}

const sessionImportCandidates = ['../../utils/sessionBoundary.js', '../../utils/sessionBoundary']
const storeImportCandidates = ['../utils/sessionBoundary.js', '../utils/sessionBoundary']

const profileSource = read('src/pages/profile/index.vue')
const homeSource = read('src/pages/home/index.vue')
const planSource = read('src/pages/plan/index.vue')
const guideSource = read('src/pages/guide/index.vue')
const tasksSource = read('src/pages/tasks/index.vue')
const taskDetailSource = read('src/pages/task-detail/index.vue')
const recordSource = read('src/pages/record/index.vue')
const recordDetailSource = read('src/pages/record-detail/index.vue')
const taskStoreSource = read('src/stores/task.js')
const recordStoreSource = read('src/stores/record.js')

requireContract(existsSync(helperPath), `shared session boundary module is missing: ${helperRelativePath}`)

const pathRules = [
  ['Profile normal logout', profileSource, 'handleMenu', sessionImportCandidates, 'logout-menu'],
  ['Profile child-load 401', profileSource, 'loadChildren', sessionImportCandidates, 'unauthorized-branch'],
  ['Home plan-submit 401', homeSource, 'handleAuthExpired', sessionImportCandidates, 'auth-handler'],
  ['Plan page 401', planSource, 'handleAuthExpired', sessionImportCandidates, 'auth-handler'],
  ['Guide plan-restore 401', guideSource, 'restoreCurrentPlan', sessionImportCandidates, 'unauthorized-branch'],
  ['Task list restore 401', tasksSource, 'restorePlanAndTasks', sessionImportCandidates, 'unauthorized-branch'],
  ['Task list start 401', tasksSource, 'startExploration', sessionImportCandidates, 'unauthorized-branch'],
  ['Task detail restore 401', taskDetailSource, 'restorePlanAndTasks', sessionImportCandidates, 'unauthorized-branch'],
  ['Record list 401', recordSource, 'handleAuthExpired', sessionImportCandidates, 'auth-handler'],
  ['Record detail 401', recordDetailSource, 'handleAuthExpired', sessionImportCandidates, 'auth-handler'],
  ['Task image download/upload 401', taskStoreSource, 'handleTaskImageError', storeImportCandidates, 'unauthorized-branch'],
]

for (const [label, source, methodName, importCandidates, ruleType] of pathRules) {
  const body = methodSource(source, methodName)
  requireContract(body.length > 0, `${label}: actual ${methodName} branch was not found`)
  requireContract(
    hasNamedImport(source, importCandidates, 'endUserSession'),
    `${label}: must import endUserSession from the shared session boundary`,
  )
  const expectedBody = ruleType === 'logout-menu' ? logoutMenuBranch(body) : body
  const usesBoundary = ruleType === 'unauthorized-branch'
    ? hasUnauthorizedBoundaryCall(body)
    : hasBoundaryCall(expectedBody)
  const scope = ruleType === 'logout-menu' ? 'the executable logout menu branch' : ruleType === 'unauthorized-branch' ? 'the actual 401/token-error branch' : `actual ${methodName} handler`
  requireContract(usesBoundary, `${label}: ${scope} must hand off to endUserSession instead of a page-local partial reset`)
}

// The formal task and record resets own Blob URL release. The session boundary must
// call those actions rather than duplicating their internals in page code.
requireContract(
  /\bcleanupImageState\s*\(/.test(codeMask(methodSource(taskStoreSource, 'resetSessionState'))),
  'Task resetSessionState must remain the formal task Blob URL cleanup path',
)
const recordReset = methodSource(recordStoreSource, 'resetRecordState')
const clearRecordDetail = methodSource(recordStoreSource, 'clearJourneyRecordDetail')
requireContract(
  /\bclearJourneyRecordDetail\s*\(/.test(codeMask(recordReset)) && /\.cleanup(?:\?\.)?\s*\(/.test(codeMask(clearRecordDetail)),
  'Record resetRecordState must remain the formal record Blob URL cleanup path',
)

if (existsSync(helperPath)) {
  const helperSource = read(helperRelativePath)
  const boundary = functionSource(helperSource, 'endUserSession')
  requireContract(boundary.length > 0, 'shared session boundary must export function endUserSession')

  const storeContracts = [
    ['Child', 'useChildStore', 'resetSessionState', '../stores/child'],
    ['Plan', 'usePlanStore', 'resetSessionState', '../stores/plan'],
    ['Guide', 'useGuideStore', 'resetSessionState', '../stores/guide'],
    ['Task', 'useTaskStore', 'resetSessionState', '../stores/task'],
    ['Record', 'useRecordStore', 'resetRecordState', '../stores/record'],
    ['User', 'useUserStore', 'logout', '../stores/user'],
  ]

  for (const [label, hook, action, modulePath] of storeContracts) {
    requireContract(
      hasNamedImport(helperSource, [modulePath, `${modulePath}.js`], hook),
      `shared session boundary must import ${hook} from ${modulePath}`,
    )
    requireContract(
      storeInstanceCalls(boundary, hook, action),
      `shared session boundary must call ${label}.${action}()`,
    )
  }

  requireContract(
    cleanupBeforeLoginNavigation(boundary),
    `shared session boundary must finish store cleanup before uni.reLaunch({ url: '${loginPath}' })`,
  )
  requireContract(
    hasSingleflightGuard(helperSource, boundary),
    'shared session boundary must guard concurrent 401/logout handling with one active promise',
  )
}

if (failures.length > 0) {
  console.error('RED: all logout and unauthorized paths use one shared session boundary')
  for (const failure of failures) {
    console.error(`- ${failure}`)
  }
  process.exitCode = 1
} else {
  console.log('PASS: session boundary contract is satisfied')
}
