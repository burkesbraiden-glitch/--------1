import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useChildStore } from '../../src/stores/child.js'
import { usePlanStore } from '../../src/stores/plan.js'
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
const tasksSource = readSource('src', 'pages', 'tasks', 'index.vue')
const guideSource = readSource('src', 'pages', 'guide', 'index.vue')
const homeSource = readSource('src', 'pages', 'home', 'index.vue')

const user = { id: 8404, nickname: 'P8.4B User' }
const childA = { id: 101, name: '小宁', age: 8, ageGroup: '7-12', isDefault: true }
const childB = { id: 102, name: '小安', age: 6, ageGroup: '3-6', isDefault: false }
const planA = { id: 401, childId: childA.id, title: 'A 的探索计划', destination: '故宫', status: 'ready' }
const planB = { id: 402, childId: childB.id, title: 'B 的探索计划', destination: '国家博物馆', status: 'ready' }

function respond(options, data, statusCode = 200) {
  options.success({ statusCode, data: { success: true, data } })
}

function respondError(options, statusCode, code = 'HTTP_ERROR', message = 'request failed') {
  options.success({ statusCode, data: { success: false, error: { code, message } } })
}

function login() {
  useUserStore().loginSuccess('p8-4b-token', user)
}

function activateChild(childId = childB.id) {
  const childStore = useChildStore()
  childStore.applyChildrenPayload({
    children: [childA, childB],
    currentChild: childA,
  }, user.id)
  expect(childStore.setActiveChild(childId)).toBe(true)
}

function installPlans(plans) {
  setRequestHandler((options) => {
    if (options.url.endsWith('/plans') && options.method === 'GET') {
      respond(options, { plans })
      return
    }
    throw new Error(`Unexpected request: ${options.url}`)
  })
}

function pageMethod(source, name, dependencies = {}) {
  const match = source.match(new RegExp(`async ${name}\\(([^)]*)\\) \\{[\\s\\S]*?\\n    \\},`))
  if (!match) {
    throw new Error(`Missing ${name} method`)
  }
  const functionSource = match[0]
    .replace(`async ${name}(`, `async function ${name}(`)
    .replace(/,\s*$/, '')
  return Function(...Object.keys(dependencies), `return (${functionSource})`)(...Object.values(dependencies))
}

function computedMethod(source, name) {
  const match = source.match(new RegExp(`${name}\\(\\) \\{[\\s\\S]*?\\n    \\},`))
  if (!match) {
    throw new Error(`Missing ${name} computed property`)
  }
  const functionSource = match[0]
    .replace(`${name}()`, `function ${name}()`)
    .replace(/,\s*$/, '')
  return Function(`return (${functionSource})`)()
}

const taskStateMessage = computedMethod(tasksSource, 'taskStateMessage')
const taskDisplayPlan = computedMethod(tasksSource, 'displayPlan')
const guidePlanRecoveryBusy = computedMethod(guideSource, 'isPlanRecoveryBusy')

function taskContext({ planStore = {}, task = {} } = {}) {
  return {
    planStore: {
      currentPlan: null,
      error: null,
      isLoading: false,
      ...planStore,
    },
    task: {
      isGenerating: false,
      isLoading: false,
      currentPlanTasks: [],
      error: null,
      ensureTasks: vi.fn().mockResolvedValue([]),
      ...task,
    },
    recordStore: {},
    isCompletedPlan: false,
    displayPlan: {},
    hasEnsuredJourneyRecord: false,
    hasCurrentEnsureState: false,
    ensureJourneyRecordForCompletedPlan: vi.fn(),
  }
}

function guideContext({ planId = '', ensureGuide = vi.fn().mockResolvedValue(null) } = {}) {
  return {
    planId,
    isPlanUnavailable: false,
    recoveryError: null,
    guideStore: {
      clearGuideForPlanChange: vi.fn(),
      resetSessionState: vi.fn(),
      ensureGuide,
    },
    planStore: { isLoading: false, currentPlan: null },
  }
}

function homeContext() {
  return {
    isOpeningAudioGuide: false,
    audioGuideOpen: false,
    audioGuidePlanId: planA.id,
    handleAuthExpired: vi.fn(),
    showToast: vi.fn(),
  }
}

beforeEach(() => {
  resetUniRuntime()
  setActivePinia(createPinia())
  login()
})

describe('P8.4B Plan error versus empty decoupling', () => {
  test('1. a successful Plan response resolves the active Child B Plan', async () => {
    activateChild(childB.id)
    installPlans([planA, planB])

    const result = await ensureCurrentPlanReady({ withTasks: false, force: true })

    expect(result.currentPlan?.id).toBe(planB.id)
    expect(usePlanStore()).toMatchObject({ isLoaded: true, error: null })
  })

  test('2. a successful response with no active Child B Plan is a true empty context', async () => {
    activateChild(childB.id)
    installPlans([planA])

    const result = await ensureCurrentPlanReady({ withTasks: false, force: true })

    expect(result.currentPlan).toBeNull()
    expect(usePlanStore()).toMatchObject({ plans: [expect.objectContaining({ id: planA.id })], isLoaded: true, error: null })
  })

  test('3. a Plan network error remains an error and never returns an empty result', async () => {
    activateChild(childB.id)
    setRequestHandler((options) => options.fail({ errMsg: 'request:fail offline' }))

    await expect(ensureCurrentPlanReady({ withTasks: false, force: true })).rejects.toMatchObject({
      statusCode: 0,
      code: 'NETWORK_ERROR',
    })
    expect(usePlanStore()).toMatchObject({ isLoaded: false, error: { code: 'NETWORK_ERROR' } })
  })

  test('4. a Plan 500 remains an error and never returns an empty result', async () => {
    activateChild(childB.id)
    setRequestHandler((options) => respondError(options, 500, 'PLAN_SERVICE_ERROR', 'temporary failure'))

    await expect(ensureCurrentPlanReady({ withTasks: false, force: true })).rejects.toMatchObject({
      statusCode: 500,
      code: 'PLAN_SERVICE_ERROR',
    })
    expect(usePlanStore()).toMatchObject({ isLoaded: false, error: { code: 'PLAN_SERVICE_ERROR' } })
  })

  test('5. a Plan 401 is delegated to the existing Tasks session-boundary owner', async () => {
    const authError = { statusCode: 401, code: 'INVALID_TOKEN' }
    const endUserSession = vi.fn().mockResolvedValue()
    const restorePlanAndTasks = pageMethod(tasksSource, 'restorePlanAndTasks', {
      ensureCurrentPlanReady: vi.fn().mockRejectedValue(authError),
      isAuthenticationError: (error) => error?.statusCode === 401,
      endUserSession,
    })
    const context = taskContext()

    await restorePlanAndTasks.call(context)

    expect(endUserSession).toHaveBeenCalledOnce()
    expect(context.task.ensureTasks).not.toHaveBeenCalled()
  })

  test('6. Tasks keeps the current-child empty copy for a successful empty Plan context', () => {
    expect(taskStateMessage.call(taskContext())).toBe('当前孩子还没有探索计划')
  })

  test('7. Tasks displays a Plan loading error before its empty state', () => {
    const context = taskContext({ planStore: { error: { code: 'NETWORK_ERROR' } } })

    expect(taskStateMessage.call(context)).toBe('探索计划加载失败，请重试')
  })

  test('8. Tasks exposes its existing retry affordance for a Plan context error', () => {
    expect(tasksSource).toContain('planStore.error')
    expect(tasksSource).toContain('探索计划加载失败，请重试')
    expect(tasksSource).toContain('restorePlanAndTasks(true)')
  })

  test('9. Tasks retry rebuilds Plan context before loading Tasks', async () => {
    const ensureCurrentPlanReady = vi.fn().mockResolvedValue({ currentPlan: planB })
    const restorePlanAndTasks = pageMethod(tasksSource, 'restorePlanAndTasks', {
      ensureCurrentPlanReady,
      isAuthenticationError: () => false,
      endUserSession: vi.fn(),
    })
    const context = taskContext({ planStore: { currentPlan: planB } })

    await restorePlanAndTasks.call(context, true)

    expect(ensureCurrentPlanReady).toHaveBeenCalledWith({ withTasks: false, force: true })
    expect(context.task.ensureTasks).toHaveBeenCalledWith(planB.id, planB.status)
  })

  test('10. Tasks retry with a successful empty result does not request Tasks', async () => {
    const ensureCurrentPlanReady = vi.fn().mockResolvedValue({ currentPlan: null })
    const restorePlanAndTasks = pageMethod(tasksSource, 'restorePlanAndTasks', {
      ensureCurrentPlanReady,
      isAuthenticationError: () => false,
      endUserSession: vi.fn(),
    })
    const context = taskContext()

    await restorePlanAndTasks.call(context, true)

    expect(context.task.ensureTasks).not.toHaveBeenCalled()
  })

  test('11. a failed Child B refresh cannot expose stale Child A as the Tasks display Plan', () => {
    const context = taskContext({
      planStore: { currentPlan: planA, error: { code: 'NETWORK_ERROR' } },
    })

    expect(taskDisplayPlan.call(context)).toEqual({})
  })

  test('12. a no-explicit Guide entry keeps its true empty Plan state', () => {
    expect(guideSource).toContain('当前孩子暂无可用探索计划')
  })

  test('13. a no-explicit Guide Plan error becomes a Plan recovery error', async () => {
    const requestError = { statusCode: 0, code: 'NETWORK_ERROR' }
    const restoreCurrentPlan = pageMethod(guideSource, 'restoreCurrentPlan', {
      ensureCurrentPlanReady: vi.fn().mockRejectedValue(requestError),
      endUserSession: vi.fn(),
    })
    const context = guideContext()

    await restoreCurrentPlan.call(context)

    expect(context.recoveryError).toBe(requestError)
    expect(context.guideStore.clearGuideForPlanChange).toHaveBeenCalledOnce()
  })

  test('14. a no-explicit Guide Plan error never requests a Guide', async () => {
    const restoreCurrentPlan = pageMethod(guideSource, 'restoreCurrentPlan', {
      ensureCurrentPlanReady: vi.fn().mockRejectedValue({ code: 'NETWORK_ERROR', statusCode: 0 }),
      endUserSession: vi.fn(),
    })
    const ensureGuide = vi.fn()
    const context = guideContext({ ensureGuide })

    await restoreCurrentPlan.call(context)

    expect(ensureGuide).not.toHaveBeenCalled()
  })

  test('15. a successful Guide retry continues only after Plan context recovery succeeds', async () => {
    const requestError = { code: 'NETWORK_ERROR', statusCode: 0 }
    const ensureCurrentPlanReady = vi.fn()
      .mockRejectedValueOnce(requestError)
      .mockResolvedValueOnce({ currentPlan: planB })
    const restoreCurrentPlan = pageMethod(guideSource, 'restoreCurrentPlan', {
      ensureCurrentPlanReady,
      endUserSession: vi.fn(),
    })
    const ensureGuide = vi.fn().mockResolvedValue({ planId: planB.id })
    const context = guideContext({ ensureGuide })

    await restoreCurrentPlan.call(context)
    await restoreCurrentPlan.call(context)

    expect(ensureCurrentPlanReady).toHaveBeenCalledTimes(2)
    expect(ensureGuide).toHaveBeenCalledWith(planB.id)
    expect(context.recoveryError).toBeNull()
  })

  test('16. explicit Guide Plan selection remains strict', () => {
    expect(guideSource).toContain("{ planId: explicitPlanId, withTasks: false, force: true }")
  })

  test('17. an invalid explicit Plan remains unavailable without a fallback', async () => {
    activateChild(childB.id)
    installPlans([planA, planB])

    const result = await ensureCurrentPlanReady({ planId: 999, withTasks: false, force: true })

    expect(result).toMatchObject({ currentPlan: null, unavailable: true })
  })

  test('18. Home Audio keeps a successful empty Plan context closed', async () => {
    const openAudioGuide = pageMethod(homeSource, 'openAudioGuide', {
      ensureCurrentPlanReady: vi.fn().mockResolvedValue({ currentPlan: null }),
    })
    const context = homeContext()

    await openAudioGuide.call(context)

    expect(context.audioGuideOpen).toBe(false)
    expect(context.audioGuidePlanId).toBeNull()
  })

  test('19. Home Audio keeps a Plan network error closed and shows a light error', async () => {
    const openAudioGuide = pageMethod(homeSource, 'openAudioGuide', {
      ensureCurrentPlanReady: vi.fn().mockRejectedValue({ statusCode: 0, code: 'NETWORK_ERROR' }),
    })
    const context = homeContext()

    await openAudioGuide.call(context)

    expect(context.audioGuideOpen).toBe(false)
    expect(context.audioGuidePlanId).toBeNull()
    expect(context.showToast).toHaveBeenCalledWith('探索计划加载失败，请重试')
  })

  test('20. Home Audio does not fall back to stale Child A after a Plan error', async () => {
    const openAudioGuide = pageMethod(homeSource, 'openAudioGuide', {
      ensureCurrentPlanReady: vi.fn().mockRejectedValue({ statusCode: 500, code: 'PLAN_SERVICE_ERROR' }),
    })
    const context = homeContext()
    context.audioGuidePlanId = planA.id

    await openAudioGuide.call(context)

    expect(context.audioGuidePlanId).toBeNull()
    expect(context.audioGuideOpen).toBe(false)
  })

  test('21. the next successful Home Audio attempt opens only the newly resolved Child B Plan', async () => {
    const ensureCurrentPlanReady = vi.fn()
      .mockRejectedValueOnce({ statusCode: 0, code: 'NETWORK_ERROR' })
      .mockResolvedValueOnce({ currentPlan: planB })
    const openAudioGuide = pageMethod(homeSource, 'openAudioGuide', { ensureCurrentPlanReady })
    const context = homeContext()

    await openAudioGuide.call(context)
    expect(context.audioGuideOpen).toBe(false)
    await openAudioGuide.call(context)

    expect(context.audioGuideOpen).toBe(true)
    expect(context.audioGuidePlanId).toBe(planB.id)
  })

  test('22. a no-explicit Guide uses the loading state while Plan recovery is pending', () => {
    expect(guidePlanRecoveryBusy.call({ planId: '', planStore: { isLoading: true }, recoveryError: null })).toBe(true)
  })

  test('23. a stale same-session Plan error cannot overwrite a later successful response', async () => {
    const firstRequest = createDeferred()
    const secondRequest = createDeferred()
    let requestCount = 0
    setRequestHandler((options) => {
      if (!options.url.endsWith('/plans')) throw new Error(`Unexpected request: ${options.url}`)
      requestCount += 1
      const deferred = requestCount === 1 ? firstRequest : secondRequest
      deferred.promise.then(
        (data) => respond(options, data),
        () => options.fail({ errMsg: 'request:fail stale request' }),
      )
    })

    const planStore = usePlanStore()
    const pendingFirst = planStore.fetchPlans(user.id, { force: true, selectionPolicy: 'default' })
    await flushRuntimePromises()
    const pendingSecond = planStore.fetchPlans(user.id, { force: true, selectionPolicy: 'none' })
    await flushRuntimePromises()

    secondRequest.resolve({ plans: [planB] })
    await pendingSecond
    firstRequest.reject()
    await expect(pendingFirst).resolves.toMatchObject({ plans: [expect.objectContaining({ id: planB.id })] })

    expect(planStore).toMatchObject({ plans: [expect.objectContaining({ id: planB.id })], isLoaded: true, error: null })
  })

  test('24. a Plan error does not start a Guide API request', async () => {
    activateChild(childB.id)
    setRequestHandler((options) => options.fail({ errMsg: 'request:fail offline' }))

    await expect(ensureCurrentPlanReady({ withTasks: false, force: true })).rejects.toMatchObject({ code: 'NETWORK_ERROR' })

    expect(getRequestCalls().filter((call) => call.url.includes('/guide'))).toEqual([])
  })
})
