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
assert(profile.includes('plan.resetSessionState'), 'logout must clear planStore')
assert(profile.includes('task.resetSessionState'), 'logout must clear taskStore')

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
