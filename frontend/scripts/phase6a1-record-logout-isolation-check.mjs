import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const profilePath = join(root, 'src/pages/profile/index.vue')
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
  const match = /if\s*\(\s*key\s*===\s*['"]logout['"]\s*\)\s*\{/.exec(commentsMasked)
  assert(match, 'the template-bound menu handler has an executable logout branch')
  return blockSource(handler, match.index + match[0].length - 1, 'logout branch must close correctly')
}

function hasResetBeforeLoginNavigation(source) {
  const executable = codeMask(source)
  const resetIndex = executable.search(/\bthis\.record\.resetRecordState\s*\(\s*\)/)
  const navigationIndex = executable.search(/\buni\.reLaunch\s*\(/)
  const nearestFunction = executable.lastIndexOf('function', resetIndex)
  const nearestClosedBlock = executable.lastIndexOf('}', resetIndex)
  const resetIsInUnusedFunction = nearestFunction > nearestClosedBlock
  return resetIndex >= 0 && navigationIndex >= 0 && resetIndex < navigationIndex && !resetIsInUnusedFunction
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
    hasResetBeforeLoginNavigation("this.record.resetRecordState(); uni.reLaunch({ url: '/pages/login/index' })"),
    'logout boundary accepts a reset before login navigation',
  )
  for (const [name, sample] of [
    ['missing reset', "uni.reLaunch({ url: '/pages/login/index' })"],
    ['navigation before reset', "uni.reLaunch({ url: '/pages/login/index' }); this.record.resetRecordState()"],
    ['comment or string only', "// this.record.resetRecordState()\\nconst note = 'this.record.resetRecordState()'; uni.reLaunch({ url: '/pages/login/index' })"],
    ['unused cleanup helper', "function unused() { this.record.resetRecordState() } uni.reLaunch({ url: '/pages/login/index' })"],
  ]) {
    assert(!hasResetBeforeLoginNavigation(sample), `logout boundary rejects ${name}`)
  }
}

const profile = read(profilePath)
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

assert(namedImportSet(profile, '../../stores/record').has('useRecordStore'), 'profile imports the real Record Store')
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
for (const [name, source, modulePath] of [
  ['Child', childStore, '../../stores/child'],
  ['Plan', planStore, '../../stores/plan'],
  ['Guide', guideStore, '../../stores/guide'],
  ['Task', taskStore, '../../stores/task'],
]) {
  assert(namedImportSet(profile, modulePath).has(`use${name}Store`), `profile imports the real ${name} Store`)
  assert(/resetSessionState\s*\(/.test(codeMask(source)), `${name} Store exposes its existing session reset`)
}

const template = profile.match(/<template>([\s\S]*?)<\/template>/)?.[1] || ''
assert(/@click="handleMenu\(item\.key\)"/.test(template), 'the logout menu is bound to the real handleMenu handler')
assert(/key:\s*['"]logout['"]\s*,\s*label:\s*['"]退出登录['"]/.test(profile), 'the menu declares the real logout item')
const handleMenu = methodSource(profile, 'handleMenu')
const logoutBranch = logoutBranchSource(handleMenu)
const executableLogoutBranch = codeMask(logoutBranch)

for (const storeName of ['child', 'plan', 'guide', 'task']) {
  assert(new RegExp(`this\\.${storeName}\\.resetSessionState\\s*\\(\\s*\\)`).test(executableLogoutBranch), `normal logout resets the ${storeName} Store`)
}
assert(/this\.user\.logout\s*\(\s*\)/.test(executableLogoutBranch), 'normal logout calls the official User Store logout')
assert(hasOfficialLoginNavigation(logoutBranch), 'normal logout navigates to the official login page')

assert(/handleAuthExpired\s*\([^)]*\)\s*\{[\s\S]*?recordStore\.resetRecordState\s*\(\s*\)[\s\S]*?uni\.reLaunch/.test(codeMask(recordList)), 'JourneyRecord 401 handling already resets state before login navigation')
assert(
  hasResetBeforeLoginNavigation(logoutBranch),
  'normal logout resets JourneyRecord state before login navigation',
)

console.log('phase6a1 record logout isolation checks passed')
