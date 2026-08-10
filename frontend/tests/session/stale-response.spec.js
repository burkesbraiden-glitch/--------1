import { beforeEach, describe, expect, test } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import {
  createDeferred,
  flushRuntimePromises,
  getRequestCalls,
  resetUniRuntime,
  setRequestHandler,
} from './setup/uniRuntime.js'
import { useChildStore } from '../../src/stores/child.js'
import { useGuideStore } from '../../src/stores/guide.js'
import { usePlanStore } from '../../src/stores/plan.js'
import { useUserStore } from '../../src/stores/user.js'
import { endUserSession } from '../../src/utils/sessionBoundary.js'

const userA = { id: 101, nickname: 'User A' }
const userB = { id: 202, nickname: 'User B' }

function login(user) {
  useUserStore().loginSuccess(`token-${user.id}`, user)
}

function respond(options, data, statusCode = 200) {
  options.success({ statusCode, data: { success: true, data } })
}

function logoutResponse(options) {
  if (options.url.endsWith('/auth/logout')) {
    respond(options, {})
    return true
  }
  return false
}

async function switchUser() {
  await endUserSession()
  login(userB)
}

describe('session isolation for delayed Store responses', () => {
  beforeEach(() => {
    resetUniRuntime()
    setActivePinia(createPinia())
  })

  test('keeps User B children when User A child request resolves late', async () => {
    const child = useChildStore()
    const childA = createDeferred()
    const childB = createDeferred()
    let childRequestCount = 0
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      if (!options.url.endsWith('/children')) throw new Error(`Unexpected request: ${options.url}`)
      childRequestCount += 1
      const pending = childRequestCount === 1 ? childA : childB
      pending.promise.then((data) => respond(options, data))
    })

    login(userA)
    const pendingA = child.fetchChildren(userA.id)
    await flushRuntimePromises()
    await switchUser()
    const pendingB = child.fetchChildren(userB.id)
    await flushRuntimePromises()

    childB.resolve({
      children: [{ id: 2, name: 'B Child', age: 9 }],
      currentChild: { id: 2, name: 'B Child', age: 9 },
    })
    await pendingB
    childA.resolve({
      children: [{ id: 1, name: 'A Child', age: 8 }],
      currentChild: { id: 1, name: 'A Child', age: 8 },
    })
    await pendingA

    expect(getRequestCalls().filter((request) => request.url.endsWith('/children'))).toHaveLength(2)
    expect(child.loadedForUserId).toBe(userB.id)
    expect(child.currentChild.id).toBe(2)
    expect(child.children.map((item) => item.id)).toEqual([2])
  })

  test('keeps User B plans when User A plan request resolves late', async () => {
    const plan = usePlanStore()
    const plansA = createDeferred()
    const plansB = createDeferred()
    let planRequestCount = 0
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      if (!options.url.endsWith('/plans')) throw new Error(`Unexpected request: ${options.url}`)
      planRequestCount += 1
      const pending = planRequestCount === 1 ? plansA : plansB
      pending.promise.then((data) => respond(options, data))
    })

    login(userA)
    const pendingA = plan.fetchPlans(userA.id)
    await flushRuntimePromises()
    await switchUser()
    const pendingB = plan.fetchPlans(userB.id)
    await flushRuntimePromises()

    plansB.resolve({ plans: [{ id: 22, title: 'B Plan', status: 'ready' }] })
    await pendingB
    plansA.resolve({ plans: [{ id: 11, title: 'A Plan', status: 'ready' }] })
    await pendingA

    expect(plan.loadedForUserId).toBe(userB.id)
    expect(plan.currentPlan.id).toBe(22)
    expect(plan.plans.map((item) => item.id)).toEqual([22])
  })

  test('keeps User B guide when User A guide request resolves late', async () => {
    const guide = useGuideStore()
    const guideA = createDeferred()
    const guideB = createDeferred()
    let guideRequestCount = 0
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      if (!options.url.includes('/guide')) throw new Error(`Unexpected request: ${options.url}`)
      guideRequestCount += 1
      const pending = guideRequestCount === 1 ? guideA : guideB
      pending.promise.then((data) => respond(options, data))
    })

    login(userA)
    const pendingA = guide.ensureGuide(31)
    await flushRuntimePromises()
    await switchUser()
    const pendingB = guide.ensureGuide(32)
    await flushRuntimePromises()

    guideB.resolve({ guide: { id: 320, planId: 32, childIntro: ['B guide'] } })
    await pendingB
    guideA.resolve({ guide: { id: 310, planId: 31, childIntro: ['A guide'] } })
    await pendingA

    expect(guide.loadedForPlanId).toBe(32)
    expect(guide.currentGuide.id).toBe(320)
  })

  test('does not write a late User A rejection into User B child state', async () => {
    const child = useChildStore()
    const childA = createDeferred()
    const childB = createDeferred()
    let childRequestCount = 0
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      childRequestCount += 1
      const pending = childRequestCount === 1 ? childA : childB
      pending.promise.then((data) => respond(options, data), (error) => options.fail(error))
    })

    login(userA)
    const pendingA = child.fetchChildren(userA.id)
    await flushRuntimePromises()
    await switchUser()
    const pendingB = child.fetchChildren(userB.id)
    await flushRuntimePromises()
    childB.resolve({ children: [], currentChild: null })
    await pendingB
    childA.reject({ errMsg: 'late User A failure' })
    await expect(pendingA).rejects.toMatchObject({ code: 'NETWORK_ERROR' })

    expect(child.loadedForUserId).toBe(userB.id)
    expect(child.error).toBeNull()
  })

  test('does not let a late User A finally clear User B loading', async () => {
    const child = useChildStore()
    const childA = createDeferred()
    const childB = createDeferred()
    let childRequestCount = 0
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      childRequestCount += 1
      const pending = childRequestCount === 1 ? childA : childB
      pending.promise.then((data) => respond(options, data))
    })

    login(userA)
    const pendingA = child.fetchChildren(userA.id)
    await flushRuntimePromises()
    await switchUser()
    const pendingB = child.fetchChildren(userB.id)
    await flushRuntimePromises()

    childA.resolve({ children: [{ id: 1, name: 'A Child', age: 8 }], currentChild: { id: 1, name: 'A Child', age: 8 } })
    await pendingA
    expect(child.isLoading).toBe(true)

    childB.resolve({ children: [{ id: 2, name: 'B Child', age: 9 }], currentChild: { id: 2, name: 'B Child', age: 9 } })
    await pendingB
    expect(child.isLoading).toBe(false)
  })

  test('keeps stores reset when a delayed response arrives after logout without a new login', async () => {
    const child = useChildStore()
    const childA = createDeferred()
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      childA.promise.then((data) => respond(options, data))
    })

    login(userA)
    const pendingA = child.fetchChildren(userA.id)
    await flushRuntimePromises()
    await endUserSession()

    childA.resolve({
      children: [{ id: 1, name: 'A Child', age: 8 }],
      currentChild: { id: 1, name: 'A Child', age: 8 },
    })
    await pendingA

    expect(useUserStore().isLoggedIn).toBe(false)
    expect(child.children).toEqual([])
    expect(child.loadedForUserId).toBeNull()
    expect(child.hasRemoteChild).toBe(false)
    expect(child.error).toBeNull()
  })

  test('does not generate a guide after GET reports missing and the session ends', async () => {
    const guide = useGuideStore()
    let sessionEnd
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      if (options.method === 'GET') {
        options.success({
          statusCode: 404,
          data: { success: false, error: { code: 'GUIDE_NOT_FOUND', message: 'missing' } },
        })
        sessionEnd = endUserSession()
        return
      }
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    login(userA)
    const pendingGuide = guide.ensureGuide(31)
    await pendingGuide
    await sessionEnd

    const guideRequests = getRequestCalls().filter((request) => request.url.includes('/guide'))
    expect(guideRequests).toHaveLength(1)
    expect(guideRequests[0].method).toBe('GET')
    expect(guide.currentGuide).toBeNull()
    expect(guide.isGenerating).toBe(false)
  })

  test('generates once when the guide does not exist in the active session', async () => {
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      if (options.url.endsWith('/plans/101/guide') && options.method === 'GET') {
        options.success({
          statusCode: 404,
          data: { success: false, error: { code: 'GUIDE_NOT_FOUND', message: 'Guide not found' } },
        })
        return
      }
      if (options.url.endsWith('/plans/101/guide/generate') && options.method === 'POST') {
        respond(options, {
          guide: {
            id: 501,
            planId: 101,
            childIntro: ['Intro 101'],
            questions: ['Question 101'],
            focusItems: ['Focus 101'],
          },
        }, 201)
        return
      }
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    login(userA)
    const result = await useGuideStore().ensureGuide(101)

    expect(result.id).toBe(501)
    expect(getRequestCalls().filter((request) => request.url.endsWith('/plans/101/guide/generate'))).toHaveLength(1)
  })

  test('dedupes concurrent reads for an existing guide', async () => {
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      if (options.url.endsWith('/plans/202/guide') && options.method === 'GET') {
        respond(options, {
          guide: {
            id: 602,
            planId: 202,
            childIntro: ['Intro 202'],
            questions: ['Question 202'],
            focusItems: ['Focus 202'],
          },
        })
        return
      }
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    login(userA)
    const [first, second] = await Promise.all([useGuideStore().ensureGuide(202), useGuideStore().ensureGuide(202)])

    expect([first.id, second.id]).toEqual([602, 602])
    expect(getRequestCalls().filter((request) => request.url.endsWith('/plans/202/guide'))).toHaveLength(1)
    expect(getRequestCalls().filter((request) => request.url.endsWith('/plans/202/guide/generate'))).toHaveLength(0)
  })

  test('does not generate after a guide network failure', async () => {
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      if (options.url.endsWith('/plans/303/guide') && options.method === 'GET') {
        options.fail({ errMsg: 'network down' })
        return
      }
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    login(userA)
    const guide = useGuideStore()
    guide.applyGuide({ id: 602, planId: 202, childIntro: [], questions: [], focusItems: [] }, 202)
    guide.clearGuideForPlanChange(303)

    await expect(guide.ensureGuide(303)).rejects.toMatchObject({ code: 'NETWORK_ERROR' })
    expect(guide.currentGuide).toBeNull()
    expect(getRequestCalls().filter((request) => request.url.endsWith('/plans/303/guide/generate'))).toHaveLength(0)
  })

  test('does not request an empty plan and clears Guide session state', async () => {
    login(userA)
    const guide = useGuideStore()
    guide.applyGuide({ id: 602, planId: 202, childIntro: [], questions: [], focusItems: [] }, 202)
    guide.isLoading = true
    guide.isGenerating = true

    await expect(guide.ensureGuide(null)).resolves.toBeNull()
    expect(getRequestCalls()).toHaveLength(0)

    guide.resetSessionState()
    expect(guide.currentGuide).toBeNull()
    expect(guide.loadedForPlanId).toBeNull()
    expect(guide.isLoading).toBe(false)
    expect(guide.isGenerating).toBe(false)
  })
})
