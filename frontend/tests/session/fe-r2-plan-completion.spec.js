import { beforeEach, describe, expect, test } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import {
  createDeferred,
  flushRuntimePromises,
  getRequestCalls,
  resetUniRuntime,
  setRequestHandler,
} from './setup/uniRuntime.js'
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

function respondError(options, error, statusCode = 409) {
  options.success({ statusCode, data: { success: false, error } })
}

function logoutResponse(options) {
  if (options.url.endsWith('/auth/logout')) {
    respond(options, {})
    return true
  }
  return false
}

function inProgressPlan(id = 119) {
  return { id, title: '故宫探索', status: 'in-progress', taskCount: 3 }
}

function completedPlan(id = 119) {
  return { ...inProgressPlan(id), status: 'completed' }
}

function seedPlan(user, planData = inProgressPlan()) {
  const plan = usePlanStore()
  plan.applyPlanList([planData], user.id)
  return plan
}

describe('FE-R2.1 Plan Completion', () => {
  beforeEach(() => {
    resetUniRuntime()
    setActivePinia(createPinia())
  })

  test('sends the authenticated completion POST through the real request layer', async () => {
    login(userA)
    const plan = seedPlan(userA)
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      if (!options.url.endsWith('/plans/119/complete')) throw new Error(`Unexpected request: ${options.url}`)
      respond(options, { plan: completedPlan(), completedNow: true })
    })

    await plan.completeExploration(119, userA.id)

    const completionRequests = getRequestCalls().filter((request) => request.url.endsWith('/plans/119/complete'))
    expect(completionRequests).toHaveLength(1)
    expect(completionRequests[0].method).toBe('POST')
    expect(completionRequests[0].header.Authorization).toBe('Bearer token-101')
  })

  test('updates the selected Plan only from the completed Plan returned by the server', async () => {
    login(userA)
    const plan = seedPlan(userA)
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      respond(options, { plan: completedPlan(), completedNow: true })
    })

    const result = await plan.completeExploration(119, userA.id)

    expect(result.status).toBe('completed')
    expect(plan.currentPlan).toMatchObject({ id: 119, status: 'completed' })
    expect(plan.plans.find((item) => item.id === 119)).toMatchObject({ status: 'completed' })
    expect(plan.status).toBe('completed')
  })

  test('accepts an idempotent completed response when completedNow is false', async () => {
    login(userA)
    const plan = seedPlan(userA)
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      respond(options, { plan: completedPlan(), completedNow: false })
    })

    await expect(plan.completeExploration(119, userA.id)).resolves.toMatchObject({ id: 119, status: 'completed' })

    expect(plan.currentPlan.status).toBe('completed')
    expect(plan.completionError).toBeNull()
  })

  test('does not request completion when userId does not belong to the current session', async () => {
    login(userA)
    const plan = seedPlan(userA)
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      respond(options, { plan: completedPlan(), completedNow: true })
    })

    await expect(plan.completeExploration(119, userB.id)).resolves.toBeNull()

    expect(getRequestCalls()).toEqual([])
    expect(plan.isCompleting).toBe(false)
    expect(plan.completionError).toBeNull()
  })

  test('preserves an in-progress Plan and exposes a network completion failure', async () => {
    login(userA)
    const plan = seedPlan(userA)
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      options.fail({ errMsg: 'network down' })
    })

    await expect(plan.completeExploration(119, userA.id)).rejects.toMatchObject({ code: 'NETWORK_ERROR' })

    expect(plan.currentPlan.status).toBe('in-progress')
    expect(plan.plans.find((item) => item.id === 119).status).toBe('in-progress')
    expect(plan.completionError).toMatchObject({ code: 'NETWORK_ERROR' })
  })

  test('preserves an in-progress Plan and exposes PLAN_TASKS_INCOMPLETE', async () => {
    login(userA)
    const plan = seedPlan(userA)
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      respondError(options, { code: 'PLAN_TASKS_INCOMPLETE', message: 'incomplete' })
    })

    await expect(plan.completeExploration(119, userA.id)).rejects.toMatchObject({ code: 'PLAN_TASKS_INCOMPLETE' })

    expect(plan.currentPlan.status).toBe('in-progress')
    expect(plan.completionError).toMatchObject({ code: 'PLAN_TASKS_INCOMPLETE' })
  })

  test('dedupes same-session completion calls for the same Plan', async () => {
    const completion = createDeferred()
    login(userA)
    const plan = seedPlan(userA)
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      completion.promise.then((data) => respond(options, data))
    })

    const first = plan.completeExploration(119, userA.id)
    const second = plan.completeExploration(119, userA.id)
    await flushRuntimePromises()

    expect(getRequestCalls().filter((request) => request.url.endsWith('/plans/119/complete'))).toHaveLength(1)
    completion.resolve({ plan: completedPlan(), completedNow: true })

    await expect(Promise.all([first, second])).resolves.toEqual([
      expect.objectContaining({ id: 119, status: 'completed' }),
      expect.objectContaining({ id: 119, status: 'completed' }),
    ])
  })

  test('does not let a late User A completion success overwrite User B Plan state', async () => {
    const completionA = createDeferred()
    const completionB = createDeferred()
    let requestCount = 0
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      requestCount += 1
      const pending = requestCount === 1 ? completionA : completionB
      pending.promise.then((data) => respond(options, data))
    })

    login(userA)
    const plan = seedPlan(userA)
    const pendingA = plan.completeExploration(119, userA.id)
    await flushRuntimePromises()
    await endUserSession()
    login(userB)
    seedPlan(userB, inProgressPlan(220))
    const pendingB = plan.completeExploration(220, userB.id)
    await flushRuntimePromises()

    completionB.resolve({ plan: completedPlan(220), completedNow: true })
    await pendingB
    completionA.resolve({ plan: completedPlan(119), completedNow: true })
    await pendingA

    expect(plan.loadedForUserId).toBe(userB.id)
    expect(plan.currentPlan).toMatchObject({ id: 220, status: 'completed' })
    expect(plan.plans.map((item) => item.id)).toEqual([220])
  })

  test('does not let a late User A completion error write into User B completion state', async () => {
    const completionA = createDeferred()
    const completionB = createDeferred()
    let requestCount = 0
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      requestCount += 1
      const pending = requestCount === 1 ? completionA : completionB
      pending.promise.then((data) => respond(options, data), (error) => options.fail(error))
    })

    login(userA)
    const plan = seedPlan(userA)
    const pendingA = plan.completeExploration(119, userA.id)
    await flushRuntimePromises()
    await endUserSession()
    login(userB)
    seedPlan(userB, inProgressPlan(220))
    const pendingB = plan.completeExploration(220, userB.id)
    await flushRuntimePromises()

    completionA.reject({ errMsg: 'late User A failure' })
    await expect(pendingA).rejects.toMatchObject({ code: 'NETWORK_ERROR' })

    expect(plan.isCompleting).toBe(true)
    expect(plan.completionError).toBeNull()
    completionB.resolve({ plan: completedPlan(220), completedNow: true })
    await pendingB
  })

  test('does not let a late User A finally clear User B completion loading', async () => {
    const completionA = createDeferred()
    const completionB = createDeferred()
    let requestCount = 0
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      requestCount += 1
      const pending = requestCount === 1 ? completionA : completionB
      pending.promise.then((data) => respond(options, data))
    })

    login(userA)
    const plan = seedPlan(userA)
    const pendingA = plan.completeExploration(119, userA.id)
    await flushRuntimePromises()
    await endUserSession()
    login(userB)
    seedPlan(userB, inProgressPlan(220))
    const pendingB = plan.completeExploration(220, userB.id)
    await flushRuntimePromises()

    completionA.resolve({ plan: completedPlan(119), completedNow: true })
    await pendingA

    expect(plan.isCompleting).toBe(true)
    completionB.resolve({ plan: completedPlan(220), completedNow: true })
    await pendingB
    expect(plan.isCompleting).toBe(false)
  })

  test('keeps the Plan Store reset when a delayed completion response arrives after logout', async () => {
    const completion = createDeferred()
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      completion.promise.then((data) => respond(options, data))
    })

    login(userA)
    const plan = seedPlan(userA)
    const pending = plan.completeExploration(119, userA.id)
    await flushRuntimePromises()
    await endUserSession()
    completion.resolve({ plan: completedPlan(), completedNow: true })
    await pending

    expect(useUserStore().isLoggedIn).toBe(false)
    expect(plan.currentPlan).toBeNull()
    expect(plan.plans).toEqual([])
    expect(plan.isCompleting).toBe(false)
    expect(plan.completionError).toBeNull()
  })

  test('rejects a malformed delayed completion response without reviving a logged-out session', async () => {
    const completion = createDeferred()
    setRequestHandler((options) => {
      if (logoutResponse(options)) return
      completion.promise.then((data) => respond(options, data))
    })

    login(userA)
    const plan = seedPlan(userA)
    const pending = plan.completeExploration(119, userA.id)
    await flushRuntimePromises()
    await endUserSession()
    completion.resolve({ plan: null, completedNow: true })

    await expect(pending).rejects.toMatchObject({ code: 'INVALID_RESPONSE' })
    expect(plan.currentPlan).toBeNull()
    expect(plan.plans).toEqual([])
    expect(plan.isCompleting).toBe(false)
    expect(plan.completionError).toBeNull()
  })
})
