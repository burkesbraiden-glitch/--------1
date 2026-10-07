import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { beforeEach, describe, expect, test } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import {
  getRequestCalls,
  resetUniRuntime,
  setRequestHandler,
} from './setup/uniRuntime.js'
import { CURRENT_PLAN_SELECTION_KEY, usePlanStore } from '../../src/stores/plan.js'
import { useUserStore } from '../../src/stores/user.js'
import { ensureCurrentPlanReady } from '../../src/utils/planRecovery.js'

const workspaceRoot = resolve(process.cwd(), '..')
const frontendFile = (...segments) => resolve(workspaceRoot, 'frontend', ...segments)
const detailPath = frontendFile('src', 'pages', 'explore-detail', 'index.vue')
const detailSource = existsSync(detailPath) ? readFileSync(detailPath, 'utf8') : ''
const pagesConfigSource = readFileSync(frontendFile('src', 'pages.json'), 'utf8')
const recoveryUser = { id: 702, nickname: 'Strict Recovery User' }
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

function requireDetailSource() {
  expect(existsSync(detailPath)).toBe(true)
  return detailSource
}

function respond(options, data) {
  options.success({ statusCode: 200, data: { success: true, data } })
}

function authenticateRecoveryUser() {
  useUserStore().loginSuccess('p7f2-strict-recovery-token', recoveryUser)
}

function providePlans(plans) {
  setRequestHandler((options) => {
    expect(options.url.endsWith('/plans')).toBe(true)
    respond(options, { plans })
  })
}

describe('P7F-2 Explore Detail', () => {
  test('registers the Explore Detail page', () => {
    expect(pagesConfigSource).toContain('pages/explore-detail/index')
    requireDetailSource()
  })

  test('reads an explicit planId from its URL', () => {
    const source = requireDetailSource()

    expect(source).toMatch(/onLoad\(options\)/)
    expect(source).toMatch(/options\?\.planId/)
    expect(source).toMatch(/this\.planId/)
  })

  test('strictly restores the URL Plan and presents unavailable state instead of falling back to the first Plan', () => {
    const source = requireDetailSource()

    expect(source).toContain('selectPlanById(this.planId)')
    expect(source).not.toMatch(/plans\s*\[\s*0\s*\]/)
    expect(source).toMatch(/(?:isPlanUnavailable|isUnavailable|notFound|unavailable|not-found)/)
  })

  test('takes over the former single-Plan hero, static exploration content, lifecycle action, and Task entry', () => {
    const source = requireDetailSource()

    expect(source).toContain('plan-hero')
    expect(source).toContain('随身探索清单')
    expect(source).toContain('开始探索')
    expect(source).toContain('继续探索')
    expect(source).toContain('startExploration')
    expect(source).toContain('/pages/tasks/index')
  })

  test('confines existing Task preparation to the explicit Detail lifecycle action and keeps Guide and Task APIs independent', () => {
    const source = requireDetailSource()
    const lifecycleSource = source.match(/async startExploration\(\) \{[\s\S]*?\n    \},/)?.[0] || ''

    expect(source).toContain('useTaskStore')
    expect(lifecycleSource).toContain('ensureTasks')
    expect(source).not.toContain('useGuideStore')
    expect(source).not.toMatch(/from\s*['"][^'"]*api\/(?:guides|tasks)/)
    expect(source).not.toContain('ensureGuide')
  })
})

describe('P7F-2 Explore Detail strict planId recovery runtime', () => {
  beforeEach(() => {
    resetUniRuntime()
    setActivePinia(createPinia())
  })

  test('keeps currentPlan empty and creates no fallback selection when explicit planId is unavailable', async () => {
    authenticateRecoveryUser()
    providePlans([planB])

    const result = await ensureCurrentPlanReady({ planId: planA.id, withTasks: false, force: true })
    const planStore = usePlanStore()

    expect(result).toMatchObject({ currentPlan: null, unavailable: true })
    expect(planStore.plans.map((plan) => plan.id)).toEqual([planB.id])
    expect(planStore.currentPlan).toBeNull()
    expect(uni.getStorageSync(CURRENT_PLAN_SELECTION_KEY)).toBeUndefined()
    expect(getRequestCalls().map((call) => call.url)).toEqual([expect.stringMatching(/\/plans$/)])
  })

  test('selects the explicit Plan A even when the server list starts with Plan B', async () => {
    authenticateRecoveryUser()
    providePlans([planB, planA])

    const result = await ensureCurrentPlanReady({ planId: planA.id, withTasks: false, force: true })

    expect(result.unavailable).toBe(false)
    expect(result.currentPlan?.id).toBe(planA.id)
    expect(usePlanStore().currentPlan?.id).toBe(planA.id)
  })

  test('overrides a valid persisted Plan B with the explicit Detail Plan A', async () => {
    authenticateRecoveryUser()
    uni.setStorageSync(CURRENT_PLAN_SELECTION_KEY, { userId: recoveryUser.id, planId: planB.id })
    providePlans([planA, planB])

    const result = await ensureCurrentPlanReady({ planId: planA.id, withTasks: false, force: true })

    expect(result.unavailable).toBe(false)
    expect(usePlanStore().currentPlan?.id).toBe(planA.id)
    expect(uni.getStorageSync(CURRENT_PLAN_SELECTION_KEY)).toEqual({ userId: recoveryUser.id, planId: planA.id })
  })

  test('does not use persisted Plan B as the current Plan when explicit Plan A is unavailable', async () => {
    authenticateRecoveryUser()
    uni.setStorageSync(CURRENT_PLAN_SELECTION_KEY, { userId: recoveryUser.id, planId: planB.id })
    providePlans([planB])

    const result = await ensureCurrentPlanReady({ planId: planA.id, withTasks: false, force: true })

    expect(result).toMatchObject({ currentPlan: null, unavailable: true })
    expect(usePlanStore().currentPlan).toBeNull()
    expect(uni.getStorageSync(CURRENT_PLAN_SELECTION_KEY)).toEqual({ userId: recoveryUser.id, planId: planB.id })
  })

  test('keeps the legacy persisted-selection recovery when no explicit planId is supplied', async () => {
    authenticateRecoveryUser()
    uni.setStorageSync(CURRENT_PLAN_SELECTION_KEY, { userId: recoveryUser.id, planId: planB.id })
    providePlans([planA, planB])

    const result = await ensureCurrentPlanReady({ withTasks: false, force: true })

    expect(result.unavailable).toBe(false)
    expect(result.currentPlan?.id).toBe(planB.id)
    expect(usePlanStore().currentPlan?.id).toBe(planB.id)
  })
})
