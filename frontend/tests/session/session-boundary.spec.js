import { beforeEach, describe, expect, test, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { createDeferred, flushRuntimePromises, getReLaunchCalls, getRequestCalls, getStorageSnapshot, resetUniRuntime, setRequestHandler } from './setup/uniRuntime.js'
import { useChildStore } from '../../src/stores/child.js'
import { useGuideStore } from '../../src/stores/guide.js'
import { usePlanStore } from '../../src/stores/plan.js'
import { useRecordStore } from '../../src/stores/record.js'
import { useRouteStore } from '../../src/stores/route.js'
import { useTaskStore } from '../../src/stores/task.js'
import { useUserStore } from '../../src/stores/user.js'
import { endUserSession } from '../../src/utils/sessionBoundary.js'

const userId = 9001
const planId = 7001
const taskId = 8001

function login() {
  const user = useUserStore()
  user.loginSuccess('test-session-token', { id: userId, nickname: 'Session Test User' })
  return user
}

function seedBusinessStores() {
  const child = useChildStore()
  const plan = usePlanStore()
  const route = useRouteStore()
  const guide = useGuideStore()
  const task = useTaskStore()
  const record = useRecordStore()
  const taskCleanup = vi.fn()
  const recordCleanup = vi.fn()

  child.applyChildrenPayload({
    children: [{ id: 6001, name: 'Test Child', age: 8 }],
    currentChild: { id: 6001, name: 'Test Child', age: 8 },
  }, userId)
  plan.applyPlanList([{ id: planId, title: 'Session Test Plan', status: 'in-progress' }], userId)
  route.applyReturnedRoute({ id: 3001, title: 'Session Test Route', city: '北京', days: [] })
  guide.applyGuide({ id: 5001, planId, title: 'Test Guide' }, planId)
  task.setTasksForPlan(planId, [{
    id: taskId,
    planId,
    status: 'in-progress',
    record: { imageUrl: '/api/v1/test-image' },
  }])
  task.ensureSubmissionSessionOwner(userId)
  task.taskImageCache[`${userId}:${planId}:${taskId}`] = {
    displayPath: 'blob:session-boundary-old',
    sourceImageUrl: '/api/v1/test-image',
    loading: false,
    isUploading: false,
    error: null,
    generation: 0,
    cleanup: taskCleanup,
  }
  record.records = [{ id: 4001, planId, title: 'Test Record' }]
  record.coverResources = {
    '4001:/api/v1/test-cover': {
      displayPath: 'blob:record-cover',
      cleanup: recordCleanup,
    },
  }
  record.detailImageResources.set('/api/v1/test-detail-image', {
    displayPath: 'blob:record-detail',
    cleanup: recordCleanup,
  })

  return { child, plan, route, guide, task, record, taskCleanup, recordCleanup }
}

function respondLogout(statusCode = 200, data = { success: true, data: {} }) {
  setRequestHandler((options) => {
    if (!options.url.endsWith('/auth/logout')) throw new Error(`Unexpected request: ${options.url}`)
    options.success({ statusCode, data })
  })
}

function expectCleared({ child, plan, route, guide, task, record }) {
  const user = useUserStore()
  expect(child.children).toEqual([])
  expect(child.hasRemoteChild).toBe(false)
  expect(plan.plans).toEqual([])
  expect(plan.currentPlan).toBeNull()
  expect(route.routes).toEqual([])
  expect(route.currentRoute).toBeNull()
  expect(guide.currentGuide).toBeNull()
  expect(task.tasksByPlanId).toEqual({})
  expect(task.taskImageCache).toEqual({})
  expect(record.records).toEqual([])
  expect(record.coverResources).toEqual({})
  expect(record.detailImageResources.size).toBe(0)
  expect(user.token).toBe('')
  expect(user.isLoggedIn).toBe(false)
  expect(getStorageSnapshot()).not.toHaveProperty('tonglvji_auth')
  expect(getStorageSnapshot()).not.toHaveProperty('tonglvji_current_plan_selection')
}

describe('shared session boundary', () => {
  beforeEach(() => {
    resetUniRuntime()
    setActivePinia(createPinia())
  })

  test('clears every business store, releases Blob resources, and navigates to login after logout succeeds', async () => {
    const user = login()
    const stores = seedBusinessStores()
    respondLogout()

    expect(user.isLoggedIn).toBe(true)
    expect(getStorageSnapshot()).toHaveProperty('tonglvji_auth')

    await endUserSession()

    expectCleared(stores)
    expect(stores.taskCleanup).toHaveBeenCalledTimes(1)
    expect(stores.recordCleanup).toHaveBeenCalledTimes(2)
    expect(getRequestCalls()).toHaveLength(1)
    expect(getReLaunchCalls()).toEqual([{ url: '/pages/login/index' }])
  })

  test('still clears local session and navigates to login when logout itself returns 401', async () => {
    login()
    const stores = seedBusinessStores()
    respondLogout(401, { error: { code: 'INVALID_TOKEN', message: 'expired in test' } })

    await expect(endUserSession()).resolves.toBeUndefined()

    expectCleared(stores)
    expect(stores.taskCleanup).toHaveBeenCalledTimes(1)
    expect(getRequestCalls()).toHaveLength(1)
    expect(getReLaunchCalls()).toEqual([{ url: '/pages/login/index' }])
  })

  test('concurrent authentication failures share one logout and one login navigation', async () => {
    login()
    const stores = seedBusinessStores()
    const logoutDeferred = createDeferred()
    setRequestHandler((options) => {
      if (!options.url.endsWith('/auth/logout')) throw new Error(`Unexpected request: ${options.url}`)
      logoutDeferred.promise.then(() => options.success({ statusCode: 200, data: { success: true, data: {} } }))
    })

    const first = endUserSession()
    const second = endUserSession()
    const third = endUserSession()
    await flushRuntimePromises()

    expect(first).toBe(second)
    expect(second).toBe(third)
    expect(getRequestCalls()).toHaveLength(1)
    expect(getReLaunchCalls()).toEqual([])

    logoutDeferred.resolve()
    await Promise.all([first, second, third])

    expectCleared(stores)
    expect(stores.taskCleanup).toHaveBeenCalledTimes(1)
    expect(stores.recordCleanup).toHaveBeenCalledTimes(2)
    expect(getRequestCalls()).toHaveLength(1)
    expect(getReLaunchCalls()).toEqual([{ url: '/pages/login/index' }])
  })

  test('releases the singleflight guard after completion so a new session can end normally', async () => {
    login()
    respondLogout()
    await endUserSession()

    login()
    await endUserSession()

    expect(getRequestCalls()).toHaveLength(2)
    expect(getReLaunchCalls()).toEqual([
      { url: '/pages/login/index' },
      { url: '/pages/login/index' },
    ])
  })
})
