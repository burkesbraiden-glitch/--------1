import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const appRelativePath = 'src/App.vue'

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function read(relativePath) {
  return readFileSync(join(root, relativePath), 'utf8')
}

// Keep source offsets stable while removing non-code text, so comments and
// string literals cannot satisfy the executable App launch contract.
function codeMask(source, { maskStrings = true } = {}) {
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
        output += character
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
      output += index + 1 < source.length ? (maskStrings ? blank(source[index + 1]) : source[index + 1]) : ''
      index += 2
      continue
    }
    if (character === quote) {
      output += character
      index += 1
      state = 'code'
      continue
    }
    output += maskStrings ? blank(character) : character
    index += 1
  }

  return output
}

function blockSource(source, openingBraceIndex) {
  const masked = codeMask(source, { maskStrings: false })
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

function appLaunchSource(source) {
  const masked = codeMask(source, { maskStrings: false })
  const patterns = [
    /\bonLaunch\s*:\s*(?:async\s+)?function\s*\([^)]*\)\s*\{/,
    /\basync\s+onLaunch\s*\([^)]*\)\s*\{/,
  ]

  for (const pattern of patterns) {
    const match = pattern.exec(masked)
    if (match) return blockSource(source, match.index + match[0].lastIndexOf('{'))
  }

  return ''
}

function hasNamedImport(source, exportName, moduleCandidates) {
  const masked = codeMask(source, { maskStrings: false })
  const escapedName = exportName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return moduleCandidates.some((modulePath) => {
    const escapedPath = modulePath.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const pattern = new RegExp(`\\bimport\\s*\\{[^}]*\\b${escapedName}\\b[^}]*\\}\\s*from\\s*['"]${escapedPath}['"]`)
    return pattern.test(masked)
  })
}

function ifBranches(source) {
  const masked = codeMask(source)
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
      condition: masked.slice(openingParenthesis + 1, closingParenthesis),
      body: blockSource(source, openingBrace),
    })
  }

  return branches
}

function hasAppLaunchRestoreBoundary(source) {
  const launch = appLaunchSource(source)
  if (!launch) return false

  const code = codeMask(launch)
  const imports = [
    hasNamedImport(source, 'useUserStore', ['./stores/user', './stores/user.js']),
    hasNamedImport(source, 'isAuthenticationError', ['./utils/request', './utils/request.js']),
    hasNamedImport(source, 'endUserSession', ['./utils/sessionBoundary', './utils/sessionBoundary.js']),
  ]
  if (imports.some((value) => !value)) return false

  const storeMatch = /\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*useUserStore\s*\(\s*\)/.exec(code)
  if (!storeMatch) return false
  const storeName = storeMatch[1]
  const restoredMatch = new RegExp(`\\b(?:const|let|var)\\s+([A-Za-z_$][\\w$]*)\\s*=\\s*await\\s+${storeName}\\s*\\.\\s*restoreSession\\s*\\(\\s*\\)`).exec(code)
  if (!restoredMatch) return false
  const restoredName = restoredMatch[1]

  const boundaryBranches = ifBranches(launch).filter(({ body }) => /\b(?:await\s+)?endUserSession\s*\(/.test(codeMask(body)))
  if (boundaryBranches.length !== 1) return false

  const { condition, body } = boundaryBranches[0]
  const authCondition = new RegExp(`!\\s*${restoredName}\\b`).test(condition)
    && new RegExp(`\\bisAuthenticationError\\s*\\(\\s*${storeName}\\s*\\.\\s*authError\\s*\\)`).test(condition)
  if (!authCondition || !/\bawait\s+endUserSession\s*\(\s*\)/.test(codeMask(body))) return false

  return !/\buni\s*\.\s*reLaunch\s*\(/.test(code)
    && !/\.resetSessionState\s*\(/.test(code)
    && !/\.resetRecordState\s*\(/.test(code)
    && !/\.logout\s*\(/.test(code)
}

function verifyCheckerSamples() {
  const valid = `
    import { useUserStore } from './stores/user'
    import { isAuthenticationError } from './utils/request'
    import { endUserSession } from './utils/sessionBoundary'
    export default {
      async onLaunch() {
        const userStore = useUserStore()
        const restored = await userStore.restoreSession()
        if (!restored && isAuthenticationError(userStore.authError)) {
          await endUserSession()
        }
      },
    }
  `
  const fireAndForget = `
    import { useUserStore } from './stores/user'
    import { isAuthenticationError } from './utils/request'
    import { endUserSession } from './utils/sessionBoundary'
    export default { onLaunch() { useUserStore().restoreSession() } }
  `
  const networkLogout = `
    import { useUserStore } from './stores/user'
    import { isAuthenticationError } from './utils/request'
    import { endUserSession } from './utils/sessionBoundary'
    export default { async onLaunch() {
      const userStore = useUserStore()
      const restored = await userStore.restoreSession()
      if (!restored) { await endUserSession() }
    } }
  `
  const commentsOnly = `
    // const userStore = useUserStore(); const restored = await userStore.restoreSession()
    // if (!restored && isAuthenticationError(userStore.authError)) await endUserSession()
    const note = 'endUserSession()'
    export default { onLaunch() {} }
  `

  assert(hasAppLaunchRestoreBoundary(valid), 'self-sample: valid App launch boundary must be accepted')
  assert(!hasAppLaunchRestoreBoundary(fireAndForget), 'self-sample: fire-and-forget restore must be rejected')
  assert(!hasAppLaunchRestoreBoundary(networkLogout), 'self-sample: network-error logout must be rejected')
  assert(!hasAppLaunchRestoreBoundary(commentsOnly), 'self-sample: comments and strings must not satisfy the contract')
}

verifyCheckerSamples()

if (!hasAppLaunchRestoreBoundary(read(appRelativePath))) {
  console.error('RED: App launch restore authentication failure does not hand off to endUserSession')
  process.exitCode = 1
} else {
  console.log('PASS: App launch restore authentication failures use the shared session boundary')
}
