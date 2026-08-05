import { beforeEach, describe, expect, test, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { getFetchCalls, getReLaunchCalls, getRequestCalls, resetUniRuntime, setFetchHandler, setRequestHandler } from './setup/uniRuntime.js'
import { usePlanStore } from '../../src/stores/plan.js'
import { useTaskStore } from '../../src/stores/task.js'
import { useUserStore } from '../../src/stores/user.js'

const userId = 9001
const planId = 7001
const taskId = 8001
const imageUrl = '/api/v1/plans/7001/tasks/8001/submission/image'

function seedImageContext() {
  const user = useUserStore()
  const plan = usePlanStore()
  const task = useTaskStore()
  const cleanup = vi.fn()

  user.loginSuccess('test-session-token', { id: userId, nickname: 'Image Test User' })
  plan.applyPlanList([{ id: planId, title: 'Image Test Plan', status: 'in-progress' }], userId)
  task.setTasksForPlan(planId, [{
    id: taskId,
    planId,
    status: 'in-progress',
    record: { imageUrl },
  }])
  task.ensureSubmissionSessionOwner(userId)
  task.taskImageCache[`${userId}:${planId}:${taskId}`] = {
    displayPath: 'blob:task-image-old',
    sourceImageUrl: imageUrl,
    loading: false,
    isUploading: false,
    error: null,
    generation: 0,
    cleanup,
  }

  return { user, plan, task, cleanup }
}

function logoutSuccess(options) {
  if (!options.url.endsWith('/auth/logout')) throw new Error(`Unexpected request: ${options.url}`)
  options.success({ statusCode: 200, data: { success: true, data: {} } })
}

describe('task image authentication boundary', () => {
  beforeEach(() => {
    resetUniRuntime()
    setActivePinia(createPinia())
  })

  test('task image 401 clears session and releases the previous Blob once', async () => {
    const { user, plan, task, cleanup } = seedImageContext()
    setRequestHandler(logoutSuccess)
    setFetchHandler(async () => ({
      ok: false,
      status: 401,
      json: async () => ({ error: { code: 'INVALID_TOKEN', message: 'test image authentication expired' } }),
    }))

    await expect(task.ensureTaskImageDisplay(taskId, { force: true })).rejects.toMatchObject({
      statusCode: 401,
      code: 'INVALID_TOKEN',
    })

    await vi.waitFor(() => expect(getReLaunchCalls()).toEqual([{ url: '/pages/login/index' }]))
    expect(getFetchCalls()).toEqual([expect.objectContaining({
      url: expect.stringMatching(/\/api\/v1\/plans\/7001\/tasks\/8001\/submission\/image$/),
      options: expect.objectContaining({
        cache: 'no-store',
        headers: expect.objectContaining({ Authorization: 'Bearer test-session-token' }),
      }),
    })])
    expect(cleanup).toHaveBeenCalledTimes(1)
    expect(getRequestCalls()).toEqual([expect.objectContaining({ url: expect.stringMatching(/\/auth\/logout$/) })])
    expect(user.isLoggedIn).toBe(false)
    expect(plan.currentPlan).toBeNull()
    expect(task.tasksByPlanId).toEqual({})
    expect(task.taskImageCache).toEqual({})
  })

  test('a task image network failure preserves authentication and business state', async () => {
    const { user, plan, task, cleanup } = seedImageContext()
    setFetchHandler(async () => { throw new TypeError('connection refused') })

    await expect(task.ensureTaskImageDisplay(taskId, { force: true })).rejects.toMatchObject({
      statusCode: 0,
      code: 'NETWORK_ERROR',
    })

    expect(cleanup).toHaveBeenCalledTimes(1)
    expect(user.isLoggedIn).toBe(true)
    expect(user.token).toBe('test-session-token')
    expect(plan.currentPlan?.id).toBe(planId)
    expect(task.tasksByPlanId[String(planId)]).toHaveLength(1)
    expect(task.imageStateForTask(taskId).error).toMatchObject({ code: 'NETWORK_ERROR', statusCode: 0 })
    expect(getRequestCalls()).toEqual([])
    expect(getReLaunchCalls()).toEqual([])
  })

  test('a task image non-authentication HTTP error preserves authentication and does not relaunch', async () => {
    const { user, plan, task } = seedImageContext()
    setFetchHandler(async () => ({
      ok: false,
      status: 404,
      json: async () => ({ error: { code: 'TASK_IMAGE_NOT_FOUND', message: 'missing test image' } }),
    }))

    await expect(task.ensureTaskImageDisplay(taskId, { force: true })).rejects.toMatchObject({
      statusCode: 404,
      code: 'TASK_IMAGE_NOT_FOUND',
    })

    expect(user.isLoggedIn).toBe(true)
    expect(plan.currentPlan?.id).toBe(planId)
    expect(task.tasksByPlanId[String(planId)]).toHaveLength(1)
    expect(getRequestCalls()).toEqual([])
    expect(getReLaunchCalls()).toEqual([])
  })
})
