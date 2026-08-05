import { existsSync, readFileSync } from 'node:fs'
import { join, resolve } from 'node:path'

const root = process.cwd()
const src = join(root, 'src')
const projectRoot = resolve(root, '..')

function read(relativePath) {
  return readFileSync(join(src, relativePath), 'utf8')
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message)
  }
}

function methodSource(source, name) {
  const match = source.match(new RegExp(`^\\s*(?:async\\s+)?${name}\\s*\\([^)]*\\)\\s*\\{`, 'm'))
  assert(match, `Missing ${name} method`)

  let depth = 1
  const start = match.index + match[0].length
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

function blockSource(source, openBraceIndex) {
  const masked = codeMask(source)
  let depth = 0
  for (let index = openBraceIndex; index < masked.length; index += 1) {
    if (masked[index] === '{') depth += 1
    if (masked[index] === '}') depth -= 1
    if (depth === 0 && index > openBraceIndex) return source.slice(openBraceIndex, index + 1)
  }
  return null
}

function depthAt(masked, openBraceIndex, targetIndex) {
  let depth = 1
  for (let index = openBraceIndex + 1; index < targetIndex; index += 1) {
    if (masked[index] === '{') depth += 1
    if (masked[index] === '}') depth -= 1
  }
  return depth
}

function directMethodSource(source, objectName, methodName) {
  const masked = codeMask(source)
  const container = new RegExp(`\\b${objectName}\\s*:\\s*\\{`).exec(masked)
  if (!container) return null

  const containerBrace = container.index + container[0].lastIndexOf('{')
  const methodPattern = new RegExp(`(?:async\\s+)?${methodName}\\s*\\([^)]*\\)\\s*\\{`, 'g')
  let match
  while ((match = methodPattern.exec(masked))) {
    if (match.index > containerBrace && depthAt(masked, containerBrace, match.index) === 1) {
      const methodBrace = match.index + match[0].lastIndexOf('{')
      return blockSource(source, methodBrace)
    }
  }
  return null
}

function namedImportSet(source, modulePath) {
  const masked = codeMask(source)
  const pattern = /\bimport\s*\{[\s\S]*?\}\s*from\s*(['"])\s*\1\s*;?/g
  const names = new Set()
  let match

  while ((match = pattern.exec(masked))) {
    const rawImport = source.slice(match.index, match.index + match[0].length)
    const moduleMatch = rawImport.match(/\bfrom\s*(['"])([^'"]+)\1/)
    if (!moduleMatch || moduleMatch[2] !== modulePath) continue

    const namesMatch = rawImport.match(/\bimport\s*\{([\s\S]*?)\}\s*from/)
    if (!namesMatch) continue
    for (const item of namesMatch[1].split(',')) {
      names.add(item.trim().split(/\s+as\s+/)[0])
    }
  }

  return names
}

function hasNamedImport(source, modulePaths, name) {
  return modulePaths.some((modulePath) => namedImportSet(source, modulePath).has(name))
}

function logoutBranchSource(method) {
  const masked = codeMask(method)
  const pattern = /\bif\s*\(\s*key\s*===\s*(['"])\s*\1\s*\)\s*\{/g
  let match
  while ((match = pattern.exec(masked))) {
    const branchBrace = match.index + match[0].lastIndexOf('{')
    const rawCondition = method.slice(match.index, branchBrace)
    if (/['"]logout['"]/.test(rawCondition)) return blockSource(method, branchBrace)
  }
  return null
}

function hasDirectCall(block, name) {
  if (!block) return false
  const masked = codeMask(block)
  const openingBrace = masked.indexOf('{')
  const pattern = new RegExp(`\\b${name}\\s*\\(`, 'g')
  let match
  while ((match = pattern.exec(masked))) {
    const statementStart = Math.max(masked.lastIndexOf(';', match.index), masked.lastIndexOf('{', match.index), masked.lastIndexOf('}', match.index)) + 1
    if (depthAt(masked, openingBrace, match.index) === 1 && !/(?:=>|\bfunction\b)/.test(masked.slice(statementStart, match.index))) return true
  }
  return false
}

function exportedFunctionSource(source, name) {
  const masked = codeMask(source)
  const match = new RegExp(`\\bexport\\s+(?:async\\s+)?function\\s+${name}\\s*\\([^)]*\\)\\s*\\{`).exec(masked)
  if (!match) return null
  return blockSource(source, match.index + match[0].lastIndexOf('{'))
}

function immediateCleanupSource(functionSource) {
  if (!functionSource) return null
  const masked = codeMask(functionSource)
  const match = /\(\s*async\s*\(\s*\)\s*=>\s*\{/.exec(masked)
  if (!match) return null
  const openBrace = match.index + match[0].lastIndexOf('{')
  const cleanup = blockSource(functionSource, openBrace)
  if (!cleanup) return null
  const end = openBrace + cleanup.length
  return /^\s*\)\s*\(\s*\)/.test(masked.slice(end)) ? cleanup : null
}

function helperStoreAction(cleanup, factory, action) {
  if (!cleanup) return -1
  const masked = codeMask(cleanup)
  const factoryMatch = new RegExp(`\\b(?:const|let)\\s+([A-Za-z_$][\\w$]*)\\s*=\\s*${factory}\\s*\\(\\s*\\)`).exec(masked)
  if (!factoryMatch) return -1

  const actionPattern = new RegExp(`\\b${factoryMatch[1]}\\.${action}\\s*\\(`, 'g')
  const actionMatch = actionPattern.exec(masked)
  if (!actionMatch) return -1

  const between = masked.slice(factoryMatch.index, actionMatch.index)
  return /(?:\bfunction\b|=>)/.test(between) ? -1 : actionMatch.index
}

function hasProfileLogoutInvocation(profileSource) {
  const template = profileSource.slice(0, profileSource.indexOf('<script')).replace(/<!--[\s\S]*?-->/g, '')
  const handleMenu = directMethodSource(profileSource, 'methods', 'handleMenu')
  const logoutBranch = logoutBranchSource(handleMenu)
  return /@click\s*=\s*['"]handleMenu\(item\.key\)['"]/.test(template) && hasDirectCall(logoutBranch, 'endUserSession')
}

function assertSessionBoundaryRuleExamples() {
  const executable = `<template><button @click="handleMenu(item.key)" /></template><script>export default { methods: { handleMenu(key) { if (key === 'logout') { endUserSession() } } } }</script>`
  assert(hasProfileLogoutInvocation(executable), 'shared logout rule must accept the executable menu path')
  assert(
    !hasProfileLogoutInvocation(`<template><button @click="handleMenu(item.key)" /></template><script>export default { methods: { handleMenu(key) { if (key === 'logout') { // endUserSession()\n const note = 'endUserSession()' } } } }</script>`),
    'shared logout rule must ignore comments and strings',
  )
  assert(
    !hasProfileLogoutInvocation(`<template><button @click="handleMenu(item.key)" /></template><script>export default { methods: { handleMenu(key) { if (key === 'logout') { const unusedLogout = () => endUserSession() } } } }</script>`),
    'shared logout rule must reject an unused nested callback',
  )
}

function assertProfileUsesSharedSessionBoundary(profileSource, boundarySource) {
  assertSessionBoundaryRuleExamples()
  assert(hasProfileLogoutInvocation(profileSource), 'Profile logout must remain reachable from its template and directly delegate the real logout branch')
  assert(
    hasNamedImport(profileSource, ['../../utils/sessionBoundary', '../../utils/sessionBoundary.js'], 'endUserSession'),
    'Profile logout must import endUserSession from the formal sessionBoundary module',
  )

  for (const [storeModule, storeFactory] of [
    ['../stores/plan', 'usePlanStore'],
    ['../stores/task', 'useTaskStore'],
    ['../stores/user', 'useUserStore'],
  ]) {
    assert(
      hasNamedImport(boundarySource, [storeModule, `${storeModule}.js`], storeFactory),
      `sessionBoundary must import ${storeFactory} from its formal Store module`,
    )
  }

  const cleanup = immediateCleanupSource(exportedFunctionSource(boundarySource, 'endUserSession'))
  assert(cleanup, 'sessionBoundary endUserSession must execute its cleanup in an immediate async flow')
  const planReset = helperStoreAction(cleanup, 'usePlanStore', 'resetSessionState')
  const taskReset = helperStoreAction(cleanup, 'useTaskStore', 'resetSessionState')
  const userLogout = helperStoreAction(cleanup, 'useUserStore', 'logout')
  const navigation = codeMask(cleanup).search(/\buni\.reLaunch\s*\(/)

  assert(planReset >= 0, 'sessionBoundary must call the formal Plan resetSessionState action')
  assert(taskReset >= 0, 'sessionBoundary must call the formal Task resetSessionState action')
  assert(userLogout >= 0, 'sessionBoundary must call the formal User logout action')
  assert(navigation >= 0 && /url:\s*['"]\/pages\/login\/index['"]/.test(cleanup), 'sessionBoundary must reLaunch to the login page')
  assert(planReset < userLogout && taskReset < userLogout, 'Plan and Task reset must happen before User logout')
  assert(planReset < navigation && taskReset < navigation && userLogout < navigation, 'session cleanup must complete before login navigation')
}

const plansApiPath = join(src, 'api/plans.js')
assert(existsSync(plansApiPath), 'Missing src/api/plans.js')

const plansApi = read('api/plans.js')
assert(
  plansApi.includes("from '../utils/request'") || plansApi.includes("from '../utils/request.js'"),
  'plans API must reuse unified request',
)
for (const name of ['createPlan', 'getPlans', 'getPlan', 'updatePlan', 'startPlan']) {
  assert(plansApi.includes(`function ${name}`), `plans API missing ${name}`)
}
for (const path of [
  "path: '/plans'",
  "path: `/plans/${id}`",
  "path: `/plans/${id}/start`",
]) {
  assert(plansApi.includes(path), `plans API missing ${path}`)
}
assert((plansApi.match(/auth:\s*true/g) || []).length >= 5, 'all plans API calls must use auth=true')
assert(!plansApi.includes('guide'), 'phase 3C-1 must not add Guide API')
assert(!plansApi.includes('uni.request'), 'plans API must not call uni.request directly')

const planStore = read('stores/plan.js')
assert(
  planStore.includes("from '../api/plans'") || planStore.includes("from '../api/plans.js'"),
  'planStore must import real plans API',
)
assert(!/currentPlan:\s*mockPlans\[0\]/.test(planStore), 'planStore must not default currentPlan to mockPlans[0]')
assert(!/plans:\s*mockPlans/.test(planStore), 'planStore must not default plans to mockPlans')
assert(/currentPlan:\s*null/.test(planStore), 'planStore currentPlan must initially be null')
assert(/plans:\s*\[\]/.test(planStore), 'planStore plans must initially be []')
assert(planStore.includes('plansApi.getPlans'), 'planStore must use real getPlans')
assert(planStore.includes('plansApi.createPlan'), 'planStore must use real createPlan')
assert(planStore.includes('plansApi.startPlan'), 'planStore must use real startPlan')
assert(planStore.includes('plansApi.updatePlan'), 'planStore must use real updatePlan')
assert(planStore.includes('tonglvji_current_plan_selection'), 'planStore must use current plan selection storage key')
assert(planStore.includes('userId') && planStore.includes('planId'), 'current plan storage must include userId and planId')
assert(planStore.includes('fetchPromise'), 'planStore must prevent duplicate fetchPlans calls')
assert(planStore.includes('loadedForUserId'), 'planStore must track loadedForUserId')
assert(planStore.includes('resetSessionState'), 'planStore must expose resetSessionState')
assert(!planStore.includes('Date.now()'), 'planStore must not generate local random Plan id')
assert(!/taskCount:\s*[^,\n]*3/.test(planStore), 'planStore must not write taskCount=3 to real Plan')
assert(!planStore.includes('mockPlanId') && !planStore.includes('backendId') && !planStore.includes('taskTemplateKey'), 'Plan object must not use double-id or template fields')

const home = read('pages/home/index.vue')
assert(home.includes('useUserStore'), 'home page must check auth before creating plan')
assert(home.includes('restoreSession'), 'home page must restore auth before creating plan')
assert(home.includes('登录后才能创建探索计划'), 'home page must block unauthenticated local plan creation')
assert(home.includes('请先完善孩子档案'), 'home page must block plan creation without real child')
assert(home.includes('ageGroup') && home.includes('currentChild.ageGroup'), 'home page must validate ageGroup against real child')
assert(home.includes('isCreatingPlan'), 'home page must prevent duplicate createPlan submissions')
assert(!home.includes('Date.now()'), 'home page must not create local random Plan id')

const planPage = read('pages/plan/index.vue')
assert(!planPage.includes('mockPlans[0]'), 'Plan page must not use mockPlans[0] as real fallback')
assert(planPage.includes('ensureCurrentPlanReady'), 'Plan page must restore real plans')
assert(planPage.includes('realTaskCount'), 'Plan page must show real taskCount')
assert(planPage.includes('startExploration'), 'Plan page must keep startExploration entry')
assert(planPage.includes('isStarting'), 'Plan page must prevent duplicate start')

const taskStore = read('stores/task.js')
assert(taskStore.includes('tasksByPlanId'), 'taskStore must keep real tasks by plan')
assert(taskStore.includes('taskImageCache'), 'taskStore must expose authenticated image display cache')
assert(taskStore.includes('ensureTasks'), 'taskStore must expose ensureTasks')
assert(taskStore.includes('resetSessionState'), 'taskStore must expose resetSessionState')
assert(taskStore.includes('currentPlanId()'), 'taskStore must keep currentPlanId getter')
assert(taskStore.includes('return []'), 'taskStore must return [] when currentPlan is null')

const tasksPage = read('pages/tasks/index.vue')
assert(tasksPage.includes('ensureTasks'), 'Tasks page must initialize real tasks')
assert(tasksPage.includes('ensureCurrentPlanReady'), 'Tasks page must restore real currentPlan')

const recordPage = read('pages/record/index.vue')
const recordStore = read('stores/record.js')
const recordOnShow = methodSource(recordPage, 'onShow')
const loadRecords = methodSource(recordPage, 'loadRecords')
const openRecordDetail = methodSource(recordPage, 'openRecordDetail')
const loadJourneyRecords = methodSource(recordStore, 'loadJourneyRecords')
assert(/await\s+this\.loadRecords\(\)/.test(recordOnShow), 'Record page must load journey records when shown')
assert(/await\s+this\.recordStore\.loadJourneyRecords\(params\)/.test(loadRecords), 'Record page must load records through the record store')
assert(/fetchJourneyRecords\(query\)/.test(loadJourneyRecords) && /this\.records\s*=\s*records/.test(loadJourneyRecords), 'Record store must load and store real JourneyRecord list data')
assert(!recordPage.includes('usePlanStore') && !/generateRecord|buildRecord|createLocalRecord|localTaskSessions|localTaskDrafts|mockRecords/.test(recordPage), 'Record page must not depend on currentPlan or local record generation')
assert(/record\?\.planId/.test(openRecordDetail) && /record-detail\/index\?planId=\$\{planId\}/.test(openRecordDetail), 'Record detail navigation must use each record planId')

const guidePage = read('pages/guide/index.vue')
assert(!guidePage.includes('mockPlans[0]'), 'Guide page must not use mockPlans[0] as real fallback')
assert(guidePage.includes('ensureCurrentPlanReady'), 'Guide page must still restore real currentPlan')

const profile = read('pages/profile/index.vue')
const sessionBoundary = read('utils/sessionBoundary.js')
assertProfileUsesSharedSessionBoundary(profile, sessionBoundary)

assert(existsSync(join(src, 'api/tasks.js')), 'phase 4C-1 must add api/tasks.js')
assert(!existsSync(join(src, 'api/records.js')), 'phase 3C-1 must not add records API')

const backendFiles = [
  'backend/app/api/v1/plans.py',
  'backend/app/services/plans.py',
  'backend/app/api/v1/guides.py',
  'backend/app/services/guides.py',
]
for (const file of backendFiles) {
  assert(existsSync(join(projectRoot, file)), `Missing backend contract file ${file}`)
}

console.log('phase3c1 plan integration checks passed')
