import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { afterEach, beforeEach, describe, expect, test } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import {
  getReLaunchCalls,
  getRequestCalls,
  resetUniRuntime,
  setRequestHandler,
} from './setup/uniRuntime.js'
import { CURRENT_PLAN_SELECTION_KEY, usePlanStore } from '../../src/stores/plan.js'
import { useGuideStore } from '../../src/stores/guide.js'
import { useUserStore } from '../../src/stores/user.js'
import { ensureCurrentPlanReady } from '../../src/utils/planRecovery.js'
import { endUserSession } from '../../src/utils/sessionBoundary.js'

const workspaceRoot = resolve(process.cwd(), '..')
const frontendFile = (...segments) => resolve(workspaceRoot, 'frontend', ...segments)
const exploreDetailSource = readFileSync(frontendFile('src', 'pages', 'explore-detail', 'index.vue'), 'utf8')
const guideSource = readFileSync(frontendFile('src', 'pages', 'guide', 'index.vue'), 'utf8')
const user = { id: 811, nickname: 'P8.1 Runtime User' }
const planA = {
  id: 401,
  title: 'Plan A',
  destination: '北京',
  ageGroup: '7-12',
  duration: '3小时',
  interests: [],
  taskCount: 0,
  status: 'ready',
}
const planB = {
  ...planA,
  id: 402,
  title: 'Plan B',
  destination: '西安',
}

function guideFor(planId) {
  return {
    id: `guide-${planId}`,
    planId,
    childIntro: [`Intro ${planId}`],
    questions: [`Question ${planId}`],
    focusItems: [`Focus ${planId}`],
  }
}

function respond(options, data, statusCode = 200) {
  options.success({ statusCode, data: { success: true, data } })
}

function guideRequestPlanId(options) {
  return decodeURIComponent(options.url.match(/\/plans\/([^/]+)\/guide/)?.[1] || '')
}

function guideRequests() {
  return getRequestCalls().filter((call) => call.url.includes('/guide'))
}

function authenticate() {
  useUserStore().loginSuccess('p8f1-runtime-token', user)
}

function persistPlan(planId) {
  uni.setStorageSync(CURRENT_PLAN_SELECTION_KEY, { userId: user.id, planId })
}

function loadPageOptions(source) {
  const script = source.match(/<script>\s*([\s\S]*?)<\/script>/)?.[1]
  expect(script).toBeTruthy()

  const executable = script
    .replace(/^import .+$/gm, '')
    .replace(/export default\s+/, 'return ')

  return new Function(
    'AppTabbar',
    'useGuideStore',
    'usePlanStore',
    'useUserStore',
    'ensureCurrentPlanReady',
    'endUserSession',
    executable,
  )(
    {},
    useGuideStore,
    usePlanStore,
    useUserStore,
    ensureCurrentPlanReady,
    endUserSession,
  )
}

function createPageVm(pageOptions) {
  const vm = { ...(pageOptions.data?.() || {}) }

  for (const [name, getter] of Object.entries(pageOptions.computed || {})) {
    Object.defineProperty(vm, name, {
      configurable: true,
      get: () => getter.call(vm),
    })
  }
  for (const [name, method] of Object.entries(pageOptions.methods || {})) {
    vm[name] = method.bind(vm)
  }

  return vm
}

function pageMethodContaining(pageOptions, marker) {
  return Object.entries(pageOptions.methods || {}).find(([, method]) => method.toString().includes(marker)) || null
}

function configurePlansAndGuides({ plans, onGuideRequest }) {
  setRequestHandler((options) => {
    if (options.url.endsWith('/plans')) {
      respond(options, { plans })
      return
    }

    const planId = guideRequestPlanId(options)
    if (planId) {
      onGuideRequest(options, Number(planId))
      return
    }

    throw new Error(`Unexpected request: ${options.method} ${options.url}`)
  })
}

beforeEach(() => {
  resetUniRuntime()
  setActivePinia(createPinia())
})

afterEach(() => {
  delete uni.navigateTo
  delete uni.navigateBack
})

describe('P8.1 Explore Detail → Guide entry', () => {
  test('navigates from the current Detail Plan to its exact encoded Guide URL without starting other work', async () => {
    authenticate()
    const routePlan = { ...planA, id: 'A /?&' }
    usePlanStore().applyPlanList([routePlan], user.id)
    const detailPage = loadPageOptions(exploreDetailSource)
    const vm = createPageVm(detailPage)
    const navigationCalls = []
    uni.navigateTo = (options) => {
      navigationCalls.push(options)
      return Promise.resolve()
    }
    setRequestHandler(() => {
      throw new Error('Viewing a Detail Guide entry must not request data')
    })

    const guideEntry = pageMethodContaining(detailPage, '/pages/guide/index')
    expect(guideEntry).not.toBeNull()
    if (!guideEntry) return

    await guideEntry[1].call(vm)

    expect(navigationCalls).toEqual([
      { url: `/pages/guide/index?planId=${encodeURIComponent(String(routePlan.id))}` },
    ])
    expect(getRequestCalls()).toEqual([])
    expect(usePlanStore().currentPlan?.id).toBe(routePlan.id)
  })

  test('keeps Detail browsing independent of the Guide Store, Guide API, and Task preparation', () => {
    const startExploration = exploreDetailSource.match(/async startExploration\(\) \{[\s\S]*?\n    \},/)?.[0] || ''

    expect(exploreDetailSource).not.toContain('useGuideStore')
    expect(exploreDetailSource).not.toMatch(/from\s*['"][^'"]*api\/(?:guides|tasks)/)
    expect(exploreDetailSource).not.toContain('ensureGuide')
    expect(startExploration).toContain('ensureTasks')
  })
})

describe('P8.1 Guide explicit planId recovery runtime', () => {
  test('records the explicit URL Plan ID before recovery begins', async () => {
    const guidePage = loadPageOptions(guideSource)
    const vm = createPageVm(guidePage)

    expect(typeof guidePage.onLoad).toBe('function')
    if (typeof guidePage.onLoad !== 'function') return

    await guidePage.onLoad.call(vm, { planId: String(planA.id) })
    expect(vm.planId).toBe(String(planA.id))
  })

  test('recovers explicit Plan A instead of persisted Plan B and requests only Guide A', async () => {
    authenticate()
    persistPlan(planB.id)
    configurePlansAndGuides({
      plans: [planB, planA],
      onGuideRequest(options, planId) {
        expect(options.method).toBe('GET')
        respond(options, { guide: guideFor(planId) })
      },
    })
    const guidePage = loadPageOptions(guideSource)
    const vm = createPageVm(guidePage)
    vm.planId = String(planA.id)

    await guidePage.onShow.call(vm)

    expect(usePlanStore().currentPlan?.id).toBe(planA.id)
    expect(useGuideStore().loadedForPlanId).toBe(planA.id)
    expect(guideRequests().map((call) => [call.method, call.url])).toEqual([
      ['GET', expect.stringMatching(/\/plans\/401\/guide$/)],
    ])
  })

  test('uses explicit Plan A for an existing GuideCard without generating a different Plan GuideCard', async () => {
    authenticate()
    persistPlan(planB.id)
    configurePlansAndGuides({
      plans: [planB, planA],
      onGuideRequest(options, planId) {
        if (options.method === 'GET') {
          respond(options, { guide: guideFor(planId) })
          return
        }
        respond(options, { guide: guideFor(planId) }, 201)
      },
    })
    const guidePage = loadPageOptions(guideSource)
    const vm = createPageVm(guidePage)
    vm.planId = String(planA.id)

    await guidePage.onShow.call(vm)

    expect(guideRequests().map((call) => [call.method, call.url])).toEqual([
      ['GET', expect.stringMatching(/\/plans\/401\/guide$/)],
    ])
  })

  test('generates exactly one missing GuideCard for explicit Plan A, never persisted Plan B', async () => {
    authenticate()
    persistPlan(planB.id)
    configurePlansAndGuides({
      plans: [planB, planA],
      onGuideRequest(options, planId) {
        if (options.method === 'GET') {
          options.success({
            statusCode: 404,
            data: { success: false, error: { code: 'GUIDE_NOT_FOUND', message: 'missing' } },
          })
          return
        }
        respond(options, { guide: guideFor(planId) }, 201)
      },
    })
    const guidePage = loadPageOptions(guideSource)
    const vm = createPageVm(guidePage)
    vm.planId = String(planA.id)

    await guidePage.onShow.call(vm)

    expect(guideRequests().map((call) => [call.method, call.url])).toEqual([
      ['GET', expect.stringMatching(/\/plans\/401\/guide$/)],
      ['POST', expect.stringMatching(/\/plans\/401\/guide\/generate$/)],
    ])
  })

  test('makes invalid explicit Plan A unavailable instead of presenting or reading persisted Plan B', async () => {
    authenticate()
    persistPlan(planB.id)
    configurePlansAndGuides({
      plans: [planB],
      onGuideRequest(options, planId) {
        respond(options, { guide: guideFor(planId) })
      },
    })
    const guidePage = loadPageOptions(guideSource)
    const vm = createPageVm(guidePage)
    vm.planId = String(planA.id)
    vm.isPlanUnavailable = false

    await guidePage.onShow.call(vm)

    expect(vm.isPlanUnavailable).toBe(true)
    expect(vm.displayPlan).toBeNull()
    expect(guideRequests()).toEqual([])
  })

  test('clears stale Guide B when explicit Plan A is unavailable', async () => {
    authenticate()
    persistPlan(planB.id)
    const guideStore = useGuideStore()
    guideStore.applyGuide(guideFor(planB.id), planB.id)
    configurePlansAndGuides({
      plans: [planB],
      onGuideRequest(options, planId) {
        respond(options, { guide: guideFor(planId) })
      },
    })
    const guidePage = loadPageOptions(guideSource)
    const vm = createPageVm(guidePage)
    vm.planId = String(planA.id)

    await guidePage.onShow.call(vm)

    expect(vm.displayPlan).toBeNull()
    expect(guideStore.currentGuide).toBeNull()
    expect(guideRequests()).toEqual([])
  })

  test('does not keep persisted Plan B or stale Guide B visible when explicit Plan A recovery fails', async () => {
    authenticate()
    persistPlan(planB.id)
    const planStore = usePlanStore()
    planStore.applyPlanList([planB], user.id)
    const guideStore = useGuideStore()
    guideStore.applyGuide(guideFor(planB.id), planB.id)
    setRequestHandler((options) => {
      if (options.url.endsWith('/plans')) {
        options.fail({ errMsg: 'plan list unavailable' })
        return
      }
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })
    const guidePage = loadPageOptions(guideSource)
    const vm = createPageVm(guidePage)
    vm.planId = String(planA.id)

    await guidePage.onShow.call(vm)

    expect(vm.displayPlan).toBeNull()
    expect(guideStore.currentGuide).toBeNull()
    expect(guideRequests()).toEqual([])
  })

  test('preserves legacy Home entry recovery when the Guide URL has no planId', async () => {
    authenticate()
    persistPlan(planB.id)
    configurePlansAndGuides({
      plans: [planA, planB],
      onGuideRequest(options, planId) {
        respond(options, { guide: guideFor(planId) })
      },
    })
    const guidePage = loadPageOptions(guideSource)
    const vm = createPageVm(guidePage)

    await guidePage.onShow.call(vm)

    expect(usePlanStore().currentPlan?.id).toBe(planB.id)
    expect(useGuideStore().loadedForPlanId).toBe(planB.id)
    expect(guideRequests().map((call) => [call.method, call.url])).toEqual([
      ['GET', expect.stringMatching(/\/plans\/402\/guide$/)],
    ])
  })
})

describe('P8.1 Guide return navigation', () => {
  test('returns to the existing Explore Detail stack with navigateBack rather than replacing navigation', async () => {
    const guidePage = loadPageOptions(guideSource)
    const vm = createPageVm(guidePage)
    const navigationCalls = []
    uni.navigateBack = (options) => {
      navigationCalls.push(options)
      return Promise.resolve()
    }

    const returnAction = pageMethodContaining(guidePage, 'navigateBack')
    expect(returnAction).not.toBeNull()
    if (!returnAction) return

    await returnAction[1].call(vm)

    expect(navigationCalls).toEqual([{ delta: 1 }])
    expect(getReLaunchCalls()).toEqual([])
    expect(returnAction[1].toString()).not.toContain('switchTab')
  })
})
