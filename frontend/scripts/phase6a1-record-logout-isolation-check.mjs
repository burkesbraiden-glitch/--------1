import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const profilePath = join(root, 'src/pages/profile/index.vue')
const sessionBoundaryPath = join(root, 'src/utils/sessionBoundary.js')
const recordStorePath = join(root, 'src/stores/record.js')
const userStorePath = join(root, 'src/stores/user.js')
const childStorePath = join(root, 'src/stores/child.js')
const planStorePath = join(root, 'src/stores/plan.js')
const guideStorePath = join(root, 'src/stores/guide.js')
const taskStorePath = join(root, 'src/stores/task.js')
const recordListPath = join(root, 'src/pages/record/index.vue')

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

function commentMask(source) {
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
      } else if (character === '\'' || character === '"' || character === '`') {
        result += character
        state = character
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

    result += character
    if (character === '\\' && state !== '`' && next) {
      result += next
      index += 1
    } else if (character === state) {
      state = 'code'
    }
  }

  return result
}

function methodSource(source, name) {
  const match = source.match(new RegExp(`(?:async\\s+)?${name}\\s*\\([^)]*\\)\\s*\\{`, 'm'))
  assert(match, `${name} method exists`)
  return blockSource(source, match.index + match[0].length - 1, `${name} method must close correctly`)
}

function blockSource(source, openBraceIndex, message) {
  const masked = codeMask(source)
  let depth = 0

  for (let index = openBraceIndex; index < masked.length; index += 1) {
    if (masked[index] === '{') depth += 1
    if (masked[index] === '}') depth -= 1
    if (depth === 0 && index > openBraceIndex) return source.slice(openBraceIndex, index + 1)
  }

  throw new Error(message)
}

function namedImportSet(source, modulePath) {
  const maskedSource = codeMask(source)
  const importPattern = /^\s*import\s*\{([\s\S]*?)\}\s*from\s*(['"])[\s]*\2\s*;?/gm
  let match

  while ((match = importPattern.exec(maskedSource))) {
    const rawImport = source.slice(match.index, importPattern.lastIndex)
    const expectedPath = new RegExp(`from\\s*['"]${modulePath.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}['"]\\s*;?$`)
    if (!expectedPath.test(rawImport.trim())) continue

    return new Set(
      match[1]
        .split(',')
        .map((item) => item.trim().split(/\s+as\s+/)[0])
        .filter(Boolean),
    )
  }

  return new Set()
}

function logoutBranchSource(handler) {
  const commentsMasked = commentMask(handler)
  const executable = codeMask(handler)
  const pattern = /if\s*\(\s*key\s*===\s*['"]logout['"]\s*\)\s*\{/g
  let match

  while ((match = pattern.exec(commentsMasked))) {
    if (executable.slice(match.index, match.index + 2) === 'if') {
      return blockSource(handler, match.index + match[0].length - 1, 'logout branch must close correctly')
    }
  }

  throw new Error('the template-bound menu handler has an executable logout branch')
}

function functionSource(source, name) {
  const masked = codeMask(source)
  const match = masked.match(new RegExp(`(?:export\\s+)?(?:async\\s+)?function\\s+${name}\\s*\\([^)]*\\)\\s*\\{`, 'm'))
  assert(match, `${name} function exists`)
  return blockSource(source, match.index + match[0].length - 1, `${name} function must close correctly`)
}

function hasSharedSessionCall(source) {
  return /\bendUserSession\s*\(\s*\)/.test(executableBoundaryMask(source))
}

function matchingBraceIndex(masked, openBraceIndex) {
  let depth = 0

  for (let index = openBraceIndex; index < masked.length; index += 1) {
    if (masked[index] === '{') depth += 1
    if (masked[index] === '}') depth -= 1
    if (depth === 0 && index > openBraceIndex) return index
  }

  return -1
}

function executableBoundaryMask(source) {
  const masked = codeMask(source)
  const hiddenRanges = []
  const nestedFunctionPattern = /(?:async\s+)?function\s+[A-Za-z_$][\w$]*\s*\([^)]*\)\s*\{/g
  const arrowFunctionPattern = /=>\s*\{/g

  for (const match of masked.matchAll(nestedFunctionPattern)) {
    const openBraceIndex = match.index + match[0].lastIndexOf('{')
    const closeBraceIndex = matchingBraceIndex(masked, openBraceIndex)
    if (closeBraceIndex >= 0) hiddenRanges.push([openBraceIndex, closeBraceIndex])
  }

  for (const match of masked.matchAll(arrowFunctionPattern)) {
    const openBraceIndex = match.index + match[0].lastIndexOf('{')
    const closeBraceIndex = matchingBraceIndex(masked, openBraceIndex)
    if (closeBraceIndex < 0) continue

    const afterBody = masked.slice(closeBraceIndex + 1)
    const isImmediatelyInvoked = /^\s*\)\s*\(/.test(afterBody)
    if (!isImmediatelyInvoked) hiddenRanges.push([openBraceIndex, closeBraceIndex])
  }

  const executable = [...masked]
  for (const [openBraceIndex, closeBraceIndex] of hiddenRanges) {
    for (let index = openBraceIndex + 1; index < closeBraceIndex; index += 1) {
      if (executable[index] !== '\n') executable[index] = ' '
    }
  }

  return executable.join('')
}

function hasRecordResetBeforeLogoutAndLogin(source) {
  const executable = executableBoundaryMask(source)
  const resetIndex = executable.search(/\brecordStore\.resetRecordState\s*\(\s*\)/)
  const logoutIndex = executable.search(/\buserStore\.logout\s*\(\s*\)/)
  const navigationIndex = executable.search(/\buni\.reLaunch\s*\(/)
  return resetIndex >= 0 && logoutIndex >= 0 && navigationIndex >= 0 && resetIndex < logoutIndex && logoutIndex < navigationIndex
}

function hasOfficialLoginNavigation(source) {
  const executable = codeMask(source)
  const navigation = /\buni\.reLaunch\s*\(/.exec(executable)
  if (!navigation) return false

  const callTail = source.slice(navigation.index, navigation.index + 300)
  return /url\s*:\s*['"]\/pages\/login\/index['"]/.test(callTail)
}

function assertBoundaryExamples() {
  assert(
    hasSharedSessionCall('endUserSession()'),
    'logout boundary accepts an executable shared-session call',
  )
  for (const [name, sample] of [
    ['comment only', '// endUserSession()'],
    ['string only', "const note = 'endUserSession()'"],
    ['unused nested named function', 'function unusedBoundary() { endUserSession() }'],
    ['unused nested arrow function', 'const unusedBoundary = () => { endUserSession() }'],
  ]) {
    assert(!hasSharedSessionCall(sample), `logout boundary rejects ${name}`)
  }

  assert(
    hasRecordResetBeforeLogoutAndLogin("recordStore.resetRecordState(); userStore.logout(); uni.reLaunch({ url: '/pages/login/index' })"),
    'session boundary accepts Record reset before logout and login navigation',
  )
  assert(
    !hasRecordResetBeforeLogoutAndLogin("uni.reLaunch({ url: '/pages/login/index' }); recordStore.resetRecordState(); userStore.logout()"),
    'session boundary rejects navigation before Record reset and logout',
  )
  assert(
    !hasRecordResetBeforeLogoutAndLogin(`
      function unusedCleanup() {
        recordStore.resetRecordState()
        userStore.logout()
        uni.reLaunch({ url: '/pages/login/index' })
      }
    `),
    'session boundary rejects reset, logout, and navigation inside an unused nested named function',
  )
  assert(
    !hasRecordResetBeforeLogoutAndLogin(`
      const alsoUnused = () => {
        recordStore.resetRecordState()
        userStore.logout()
        uni.reLaunch({ url: '/pages/login/index' })
      }
    `),
    'session boundary rejects reset, logout, and navigation inside an unused nested arrow function',
  )
}

const profile = read(profilePath)
const sessionBoundary = read(sessionBoundaryPath)
const recordStore = read(recordStorePath)
const userStore = read(userStorePath)
const childStore = read(childStorePath)
const planStore = read(planStorePath)
const guideStore = read(guideStorePath)
const taskStore = read(taskStorePath)
const recordList = read(recordListPath)
const executableProfile = codeMask(profile)
const executableRecordStore = codeMask(recordStore)

assertBoundaryExamples()

assert(namedImportSet(profile, '../../stores/record').has('useRecordStore'), 'profile retains the real Record Store for its learning-record display')
const recordAccessor = methodSource(executableProfile, 'record')
assert(/\buseRecordStore\s*\(\s*\)/.test(recordAccessor), 'profile instantiates the real Record Store as record')

const resetRecordState = methodSource(executableRecordStore, 'resetRecordState')
const clearJourneyRecordDetail = methodSource(executableRecordStore, 'clearJourneyRecordDetail')
assert(/this\.records\s*=\s*\[\]/.test(resetRecordState), 'Record Store reset clears the JourneyRecord list')
assert(/this\.clearJourneyRecordDetail\s*\(\s*\)/.test(resetRecordState), 'Record Store reset delegates detail cleanup')
assert(/cleanupCoverResource/.test(resetRecordState), 'Record Store reset releases list cover resources')
assert(/this\.currentRecord\s*=\s*null/.test(clearJourneyRecordDetail), 'Record Store detail cleanup clears the current JourneyRecord')
assert(/detailImageResources\.forEach/.test(clearJourneyRecordDetail) && /detailImageResources\.clear/.test(clearJourneyRecordDetail), 'Record Store detail cleanup releases detail image resources')

assert(namedImportSet(profile, '../../stores/user').has('useUserStore'), 'profile imports the real User Store')
assert(/clearLocalAuth\s*\(\s*\)/.test(methodSource(codeMask(userStore), 'logout')), 'User Store logout clears official auth state')
for (const [name, source] of [
  ['Child', childStore],
  ['Plan', planStore],
  ['Guide', guideStore],
  ['Task', taskStore],
]) {
  assert(/resetSessionState\s*\(/.test(codeMask(source)), `${name} Store exposes its existing session reset`)
}

const template = profile.match(/<template>([\s\S]*?)<\/template>/)?.[1] || ''
assert(/@click="handleMenu\(item\.key\)"/.test(template), 'the logout menu is bound to the real handleMenu handler')
assert(/key:\s*['"]logout['"]\s*,\s*label:\s*['"]退出登录['"]/.test(profile), 'the menu declares the real logout item')
const handleMenu = methodSource(profile, 'handleMenu')
const logoutBranch = logoutBranchSource(handleMenu)
assert(namedImportSet(profile, '../../utils/sessionBoundary').has('endUserSession'), 'profile imports the shared session boundary')
assert(hasSharedSessionCall(logoutBranch), 'normal logout delegates through the shared session boundary')

assert(namedImportSet(recordList, '../../utils/sessionBoundary').has('endUserSession'), 'Record List imports the shared session boundary')
const recordListAuthExpired = methodSource(recordList, 'handleAuthExpired')
assert(hasSharedSessionCall(recordListAuthExpired), 'Record List 401 handler delegates through the shared session boundary')
const recordListLoadRecords = methodSource(recordList, 'loadRecords')
assert(
  /\bif\s*\(\s*isAuthenticationError\s*\(\s*error\s*\)\s*\)\s*\{\s*await\s+this\.handleAuthExpired\s*\(\s*\)/.test(codeMask(recordListLoadRecords)),
  'Record List real authentication-error branch enters its shared session handler',
)

assert(namedImportSet(sessionBoundary, '../stores/record').has('useRecordStore'), 'shared session boundary imports the formal Record Store')
assert(namedImportSet(sessionBoundary, '../stores/user').has('useUserStore'), 'shared session boundary imports the formal User Store')
const endUserSession = functionSource(sessionBoundary, 'endUserSession')
const executableSessionBoundary = codeMask(endUserSession)
assert(/\b(?:const|let)\s+recordStore\s*=\s*useRecordStore\s*\(\s*\)/.test(executableSessionBoundary), 'shared session boundary instantiates the formal Record Store')
assert(/\brecordStore\.resetRecordState\s*\(\s*\)/.test(executableSessionBoundary), 'shared session boundary calls the Record Store reset')
assert(/\b(?:const|let)\s+userStore\s*=\s*useUserStore\s*\(\s*\)/.test(executableSessionBoundary), 'shared session boundary instantiates the formal User Store')
assert(/\buserStore\.logout\s*\(\s*\)/.test(executableSessionBoundary), 'shared session boundary calls the official User logout')
assert(hasOfficialLoginNavigation(endUserSession), 'shared session boundary navigates to the official login page')
assert(hasRecordResetBeforeLogoutAndLogin(endUserSession), 'shared session boundary resets Record state before User logout and login navigation')

console.log('phase6a1 record logout isolation checks passed')
