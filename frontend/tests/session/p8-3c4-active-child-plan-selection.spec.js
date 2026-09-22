import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { beforeEach, describe, expect, test } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { CURRENT_PLAN_SELECTION_KEY, usePlanStore } from '../../src/stores/plan.js'
import { useChildStore } from '../../src/stores/child.js'
import { useUserStore } from '../../src/stores/user.js'
import { ensureCurrentPlanReady } from '../../src/utils/planRecovery.js'
import {
  createDeferred,
  flushRuntimePromises,
  getRequestCalls,
  resetUniRuntime,
  setRequestHandler,
} from './setup/uniRuntime.js'

const workspaceRoot = resolve(process.cwd(), '..')
const readSource = (...segments) => readFileSync(resolve(workspaceRoot, 'frontend', ...segments), 'utf8')

const user = { id: 8304, nickname: 'P8.3C4 User' }
const childA = { id: 101, name: '小宁', age: 8, ageGroup: '7-12', isDefault: true }
const childB = { id: 102, name: '小安', age: 6, ageGroup: '3-6', isDefault: false }
const planA = { id: 401, childId: childA.id, title: 'A 的探索计划', destination: '故宫', status: 'ready' }
const planB = { id: 402, childId: childB.id, title: 'B 的探索计划', destination: '中国国家博物馆', status: 'ready' }

function respond(options, data, statusCode = 200) {
  options.success({ statusCode, data: { success: true, data } })
}

function login() {
  useUserStore().loginSuccess('p8-3c4-token', user)
}

function activateChild(childId) {
  const childStore = useChildStore()
  childStore.applyChildrenPayload({
    children: [childA, childB],
    currentChild: childA,
  }, user.id)
  expect(childStore.setActiveChild(childId)).toBe(true)
  return childStore
}

function persistPlan(planId) {
  uni.setStorageSync(CURRENT_PLAN_SELECTION_KEY, { userId: user.id, planId })
}

function installPlans(plans) {
  setRequestHandler((options) => {
    if (options.url.endsWith('/plans') && options.method === 'GET') {
      respond(options, { plans })
      return
    }
    throw new Error(`Unexpected request: ${options.method} ${options.url}`)
  })
}

async function recover(options = {}) {
  return ensureCurrentPlanReady({ withTasks: false, force: true, ...options })
}

beforeEach(() => {
  resetUniRuntime()
  setActivePinia(createPinia())
  login()
})

describe('P8.3C4 active-child-aware default Plan selection', () => {
  test('1. explicit Plan A remains first priority when active Child is B', async () => {
    activateChild(childB.id)
    persistPlan(planB.id)
    installPlans([planA, planB])

    const result = await recover({ planId: planA.id })

    expect(result.currentPlan?.id).toBe(planA.id)
    expect(result.unavailable).toBe(false)
  })

  test('2. an invalid explicit Plan never falls back to persisted or active-child Plans', async () => {
    activateChild(childB.id)
    persistPlan(planB.id)
    installPlans([planA, planB])

    const result = await recover({ planId: 999 })

    expect(result.currentPlan).toBeNull()
    expect(result.unavailable).toBe(true)
    expect(usePlanStore().currentPlan).toBeNull()
  })

  test('3. without an explicit Plan, persisted Plan A is ignored for active Child B', async () => {
    activateChild(childB.id)
    persistPlan(planA.id)
    installPlans([planA, planB])

    const result = await recover()

    expect(result.currentPlan?.id).toBe(planB.id)
  })

  test('4. a persisted Plan B remains usable for active Child B', async () => {
    activateChild(childB.id)
    persistPlan(planB.id)
    installPlans([planA, planB])

    const result = await recover()

    expect(result.currentPlan?.id).toBe(planB.id)
  })

  test('5. active Child B falls back only within B Plans when no suitable persistence exists', async () => {
    activateChild(childB.id)
    persistPlan(planA.id)
    installPlans([planA, planB])

    const result = await recover()

    expect(result.currentPlan?.id).toBe(planB.id)
  })

  test('6. active Child B with no Plan resolves to an empty context instead of Plan A', async () => {
    activateChild(childB.id)
    persistPlan(planA.id)
    installPlans([planA])

    const result = await recover()

    expect(result.currentPlan).toBeNull()
    expect(usePlanStore().currentPlan).toBeNull()
  })

  test('7. Tasks uses the shared no-explicit selection path', () => {
    const source = readSource('src', 'pages', 'tasks', 'index.vue')

    expect(source).toContain('ensureCurrentPlanReady({ withTasks: false, force })')
    expect(source).not.toContain('plans[0]')
  })

  test('8. Tasks has a current-child empty state instead of showing another child task list', () => {
    const source = readSource('src', 'pages', 'tasks', 'index.vue')

    expect(source).toContain('当前孩子还没有探索计划')
  })

  test('9. Task Detail remains an explicit-plan consumer', () => {
    const source = readSource('src', 'pages', 'task-detail', 'index.vue')

    expect(source).toMatch(/ensureCurrentPlanReady\(\{[\s\S]*planId:\s*this\.routePlanId/)
  })

  test('10. Guide keeps explicit planId above active-child context', () => {
    const source = readSource('src', 'pages', 'guide', 'index.vue')

    expect(source).toContain("{ planId: explicitPlanId, withTasks: false, force: true }")
  })

  test('11. a no-explicit Guide entry resolves active Child B before it requests a Guide', async () => {
    activateChild(childB.id)
    persistPlan(planA.id)
    installPlans([planA, planB])

    const result = await recover()
    const guideSource = readSource('src', 'pages', 'guide', 'index.vue')

    expect(result.currentPlan?.id).toBe(planB.id)
    expect(guideSource).toContain('await this.guideStore.ensureGuide(planId)')
  })

  test('12. no Plan for active Child B leaves Guide without a cross-child request target', async () => {
    activateChild(childB.id)
    persistPlan(planA.id)
    installPlans([planA])

    const result = await recover()
    const guideSource = readSource('src', 'pages', 'guide', 'index.vue')

    expect(result.currentPlan).toBeNull()
    expect(guideSource).toMatch(/if \(!planId\) \{[\s\S]*resetSessionState\(\)[\s\S]*return/)
  })

  test('13. Guide invalid explicit-plan behavior stays unavailable rather than falling back', async () => {
    activateChild(childB.id)
    persistPlan(planB.id)
    installPlans([planA, planB])

    const result = await recover({ planId: 999 })

    expect(result.unavailable).toBe(true)
    expect(result.currentPlan).toBeNull()
  })

  test('14. Home Audio takes only the shared resolved Plan ID', () => {
    const source = readSource('src', 'pages', 'home', 'index.vue')
    const openAudioGuide = source.match(/async openAudioGuide\(\) \{[\s\S]*?\n    \},/)?.[0] || ''

    expect(openAudioGuide).toContain('ensureCurrentPlanReady({ withTasks: false })')
    expect(openAudioGuide).toMatch(/audioGuidePlanId\s*=\s*result\.currentPlan\.id/)
    expect(openAudioGuide).not.toContain('plans[0]')
  })

  test('15. Home Audio with no active-child Plan cannot open another child Guide', async () => {
    activateChild(childB.id)
    persistPlan(planA.id)
    installPlans([planA])

    const result = await recover()

    expect(result.currentPlan).toBeNull()
    expect(getRequestCalls().filter((call) => call.url.includes('/guide'))).toEqual([])
  })

  test('16. AudioGuideSheet keeps planId as its only Plan-selection boundary', () => {
    const source = readSource('src', 'components', 'AudioGuideSheet.vue')

    expect(source).toContain('planId:')
    expect(source).toContain('samePlanId(plan.id, this.planId)')
    expect(source).not.toContain('activeChild')
  })

  test('17. A-to-B switching ignores persisted A without deleting it', async () => {
    activateChild(childB.id)
    persistPlan(planA.id)
    installPlans([planA, planB])

    const result = await recover()

    expect(result.currentPlan?.id).toBe(planB.id)
    expect(uni.getStorageSync(CURRENT_PLAN_SELECTION_KEY)).toEqual({ userId: user.id, planId: planA.id })
  })

  test('18. returning from B to A permits A to become the default again', async () => {
    const childStore = activateChild(childB.id)
    persistPlan(planA.id)
    installPlans([planA, planB])
    await recover()

    childStore.setActiveChild(childA.id)
    const result = await recover()

    expect(result.currentPlan?.id).toBe(planA.id)
  })

  test('19. a delayed Plan response resolves using the latest active Child context', async () => {
    const childStore = activateChild(childA.id)
    const deferredPlans = createDeferred()
    setRequestHandler((options) => {
      if (options.url.endsWith('/plans') && options.method === 'GET') {
        deferredPlans.promise.then((data) => respond(options, data))
        return
      }
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    const pending = recover()
    await flushRuntimePromises()
    childStore.setActiveChild(childB.id)
    deferredPlans.resolve({ plans: [planA, planB] })

    await expect(pending).resolves.toMatchObject({ currentPlan: { id: planB.id } })
    expect(usePlanStore().currentPlan?.id).toBe(planB.id)
  })
})
