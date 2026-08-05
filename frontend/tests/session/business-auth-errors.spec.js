import { beforeEach, describe, expect, test, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { createDeferred, flushRuntimePromises, getReLaunchCalls, getRequestCalls, resetUniRuntime, setRequestHandler } from './setup/uniRuntime.js'
import * as guidesApi from '../../src/api/guides.js'
import * as tasksApi from '../../src/api/tasks.js'
import { usePlanStore } from '../../src/stores/plan.js'
import { useTaskStore } from '../../src/stores/task.js'
import { useUserStore } from '../../src/stores/user.js'
import { isAuthenticationError } from '../../src/utils/request.js'
import { endUserSession } from '../../src/utils/sessionBoundary.js'

const userId = 9001
const planId = 7001
const taskId = 8001

function loginAndSeedTask() {
  const user = useUserStore()
  const plan = usePlanStore()
  const task = useTaskStore()
  const cleanup = vi.fn()
  user.loginSuccess('test-session-token', { id: userId, nickname: 'Business API Test User' })
  plan.applyPlanList([{ id: planId, title: 'Business API Test Plan', status: 'in-progress' }], userId)
  task.setTasksForPlan(planId, [{ id: taskId, planId, status: 'in-progress', record: {} }])
  task.ensureSubmissionSessionOwner(userId)
  task.taskImageCache[`${userId}:${planId}:${taskId}`] = {
    displayPath: 'blob:business-auth-old',
    sourceImageUrl: '/api/v1/test-image',
    loading: false,
    isUploading: false,
    error: null,
    generation: 0,
    cleanup,
  }
  return { user, plan, task, cleanup }
}

function auth401(options) {
  options.success({
    statusCode: 401,
    data: { error: { code: 'INVALID_TOKEN', message: 'test authentication expired' } },
  })
}

async function runProtectedRequest(promise) {
  try {
    return await promise
  } catch (error) {
    if (isAuthenticationError(error)) {
      await endUserSession()
      return null
    }
    throw error
  }
}

describe('business API authentication errors', () => {
  beforeEach(() => {
    resetUniRuntime()
    setActivePinia(createPinia())
  })

  test('normalizes a Guide API 401 with its authenticated request path', async () => {
    loginAndSeedTask()
    setRequestHandler(auth401)

    await expect(guidesApi.getGuide(planId)).rejects.toMatchObject({ statusCode: 401, code: 'INVALID_TOKEN' })

    expect(getRequestCalls()).toEqual([expect.objectContaining({
      url: expect.stringMatching(/\/plans\/7001\/guide$/),
      method: 'GET',
      header: expect.objectContaining({ Authorization: 'Bearer test-session-token' }),
    })])
  })

  test('normalizes a Tasks API 401 with its authenticated request path', async () => {
    loginAndSeedTask()
    setRequestHandler(auth401)

    await expect(tasksApi.getTasks(planId)).rejects.toMatchObject({ statusCode: 401, code: 'INVALID_TOKEN' })

    expect(getRequestCalls()).toEqual([expect.objectContaining({
      url: expect.stringMatching(/\/plans\/7001\/tasks$/),
      method: 'GET',
      header: expect.objectContaining({ Authorization: 'Bearer test-session-token' }),
    })])
  })

  test('normalizes a Task Detail API 401 with its authenticated request path', async () => {
    loginAndSeedTask()
    setRequestHandler(auth401)

    await expect(tasksApi.getTask(planId, taskId)).rejects.toMatchObject({ statusCode: 401, code: 'INVALID_TOKEN' })

    expect(getRequestCalls()).toEqual([expect.objectContaining({
      url: expect.stringMatching(/\/plans\/7001\/tasks\/8001$/),
      method: 'GET',
      header: expect.objectContaining({ Authorization: 'Bearer test-session-token' }),
    })])
  })

  test('concurrent business authentication failures share one logout and one login navigation', async () => {
    const { user, plan, task, cleanup } = loginAndSeedTask()
    const logoutDeferred = createDeferred()
    setRequestHandler((options) => {
      if (options.url.endsWith('/auth/logout')) {
        logoutDeferred.promise.then(() => options.success({ statusCode: 200, data: { success: true, data: {} } }))
        return
      }
      auth401(options)
    })

    const results = Promise.all([
      runProtectedRequest(guidesApi.getGuide(planId)),
      runProtectedRequest(tasksApi.getTasks(planId)),
      runProtectedRequest(tasksApi.getTask(planId, taskId)),
    ])
    await flushRuntimePromises()
    await flushRuntimePromises()

    const businessCalls = getRequestCalls().filter((call) => !call.url.endsWith('/auth/logout'))
    expect(businessCalls).toHaveLength(3)
    expect(businessCalls.map((call) => call.url)).toEqual(expect.arrayContaining([
      expect.stringMatching(/\/plans\/7001\/guide$/),
      expect.stringMatching(/\/plans\/7001\/tasks$/),
      expect.stringMatching(/\/plans\/7001\/tasks\/8001$/),
    ]))
    expect(getRequestCalls().filter((call) => call.url.endsWith('/auth/logout'))).toHaveLength(1)
    expect(getReLaunchCalls()).toEqual([])

    logoutDeferred.resolve()
    await expect(results).resolves.toEqual([null, null, null])

    expect(user.isLoggedIn).toBe(false)
    expect(plan.currentPlan).toBeNull()
    expect(task.tasksByPlanId).toEqual({})
    expect(cleanup).toHaveBeenCalledTimes(1)
    expect(getReLaunchCalls()).toEqual([{ url: '/pages/login/index' }])
  })

  test('a network error remains outside the shared session boundary', async () => {
    const { user, plan, task } = loginAndSeedTask()
    setRequestHandler((options) => options.fail({ errMsg: 'request:fail connection refused' }))

    await expect(runProtectedRequest(tasksApi.getTasks(planId))).rejects.toMatchObject({
      statusCode: 0,
      code: 'NETWORK_ERROR',
    })

    expect(user.isLoggedIn).toBe(true)
    expect(user.token).toBe('test-session-token')
    expect(plan.currentPlan?.id).toBe(planId)
    expect(task.tasksByPlanId[String(planId)]).toHaveLength(1)
    expect(getRequestCalls()).toHaveLength(1)
    expect(getReLaunchCalls()).toEqual([])
  })
})
