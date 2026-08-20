import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { beforeEach, describe, expect, test } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import {
  createDeferred,
  flushRuntimePromises,
  getRequestCalls,
  resetUniRuntime,
  setRequestHandler,
} from './setup/uniRuntime.js'
import * as routesApi from '../../src/api/routes.js'
import { useRouteStore } from '../../src/stores/route.js'
import { useUserStore } from '../../src/stores/user.js'

const root = resolve(process.cwd(), '..')
const apiSource = readFileSync(resolve(root, 'frontend/src/api/routes.js'), 'utf8')
const storeSource = readFileSync(resolve(root, 'frontend/src/stores/route.js'), 'utf8')

const userA = { id: 101, nickname: 'Route User A' }
const userB = { id: 202, nickname: 'Route User B' }

const generationData = {
  routeId: 12,
  childId: 34,
  results: [
    { routeStopId: 82, result: 'existing', plan: { id: 700, title: '已存在计划' } },
    { routeStopId: 81, result: 'created', plan: { id: 701, title: '新建计划' } },
  ],
}

function login(user) {
  useUserStore().loginSuccess(`p7e5-token-${user.id}`, user)
}

function respond(options, data) {
  options.success({ statusCode: 200, data: { success: true, data } })
}

function respondError(options, error) {
  options.success({
    statusCode: error.statusCode,
    data: {
      success: false,
      error: {
        code: error.code,
        message: error.message,
        details: error.details || {},
      },
    },
  })
}

describe('P7E-5 Route exploration-plan generation wiring', () => {
  beforeEach(() => {
    resetUniRuntime()
    setActivePinia(createPinia())
  })

  test('sends the exact authenticated generation request through the shared request client', async () => {
    login(userA)
    setRequestHandler((options) => respond(options, generationData))

    const result = await routesApi.generateRouteExplorationPlans(123, 456, [82, 81])

    expect(result).toBe(generationData)
    expect(getRequestCalls()).toEqual([expect.objectContaining({
      method: 'POST',
      url: 'http://session.test/api/v1/routes/123/exploration-plans/generate',
      data: { childId: 456, routeStopIds: [82, 81] },
      header: expect.objectContaining({ Authorization: 'Bearer p7e5-token-101' }),
    })])
  })

  test('keeps the API client thin and free of a second request implementation', () => {
    expect(apiSource).toContain("import request from '../utils/request.js'")
    expect(apiSource).not.toContain('uni.request')
    expect(apiSource).not.toContain('fetch(')
    expect(apiSource).not.toContain('axios')
  })

  test('initializes independent generation state and stores the unmodified ordered backend result', async () => {
    login(userA)
    const store = useRouteStore()
    const existingRoutes = [{ id: 12, title: '不应修改的路线' }]
    const existingCurrentRoute = { id: 12, title: '不应修改的当前路线' }
    store.routes = existingRoutes
    store.currentRoute = existingCurrentRoute
    setRequestHandler((options) => respond(options, generationData))

    expect(store.planGenerationResult).toBeNull()
    expect(store.isGeneratingPlans).toBe(false)
    expect(store.planGenerationError).toBeNull()

    const result = await store.generateExplorationPlans(12, 34, [82, 81])

    expect(result).toBe(generationData)
    expect(store.isGeneratingPlans).toBe(false)
    expect(store.planGenerationResult).toEqual(generationData)
    expect(store.planGenerationError).toBeNull()
    expect(store.planGenerationResult.results).toEqual(generationData.results)
    expect(store.routes).toEqual(existingRoutes)
    expect(store.currentRoute).toEqual(existingCurrentRoute)
  })

  test('sets loading during the request and preserves the raw result ordering and created-existing values', async () => {
    login(userA)
    const store = useRouteStore()
    const deferred = createDeferred()
    setRequestHandler((options) => deferred.promise.then((data) => respond(options, data)))

    const pending = store.generateExplorationPlans(12, 34, [82, 81])
    await flushRuntimePromises()

    expect(store.isGeneratingPlans).toBe(true)
    deferred.resolve(generationData)
    await expect(pending).resolves.toBe(generationData)
    expect(store.planGenerationResult.results.map((item) => item.routeStopId)).toEqual([82, 81])
    expect(store.planGenerationResult.results.map((item) => item.result)).toEqual(['existing', 'created'])
  })

  test('passes through errors and preserves the prior successful result on failure', async () => {
    login(userA)
    const store = useRouteStore()
    const priorResult = { routeId: 12, childId: 34, results: [] }
    const backendError = {
      statusCode: 409,
      code: 'ROUTE_NOT_READY',
      message: 'Route not ready',
      details: {},
    }
    store.planGenerationResult = priorResult
    setRequestHandler((options) => respondError(options, backendError))

    const thrownError = await store.generateExplorationPlans(12, 34, [82]).catch((error) => error)

    expect(store.isGeneratingPlans).toBe(false)
    expect(thrownError).toEqual(backendError)
    expect(store.planGenerationError).toEqual(thrownError)
    expect(store.planGenerationResult).toEqual(priorResult)
  })

  test('clears every generation field during session reset', () => {
    const store = useRouteStore()
    store.planGenerationResult = generationData
    store.isGeneratingPlans = true
    store.planGenerationError = { code: 'ROUTE_NOT_READY' }

    store.resetSessionState()

    expect(store.planGenerationResult).toBeNull()
    expect(store.isGeneratingPlans).toBe(false)
    expect(store.planGenerationError).toBeNull()
  })

  test('blocks stale-session success writes while preserving the original promise result', async () => {
    login(userA)
    const store = useRouteStore()
    const deferred = createDeferred()
    setRequestHandler((options) => deferred.promise.then((data) => respond(options, data)))

    const pending = store.generateExplorationPlans(12, 34, [82])
    await flushRuntimePromises()
    login(userB)
    store.resetSessionState()
    deferred.resolve(generationData)

    await expect(pending).resolves.toBe(generationData)
    expect(store.planGenerationResult).toBeNull()
    expect(store.planGenerationError).toBeNull()
    expect(store.isGeneratingPlans).toBe(false)
  })

  test('blocks stale-session error writes while preserving the original rejected error', async () => {
    login(userA)
    const store = useRouteStore()
    const deferred = createDeferred()
    const backendError = {
      statusCode: 409,
      code: 'ROUTE_NOT_READY',
      message: 'Route not ready',
      details: {},
    }
    setRequestHandler((options) => deferred.promise.then(() => respondError(options, backendError)))

    const pending = store.generateExplorationPlans(12, 34, [82])
    await flushRuntimePromises()
    login(userB)
    store.resetSessionState()
    deferred.resolve()

    await expect(pending).rejects.toEqual(backendError)
    expect(store.planGenerationResult).toBeNull()
    expect(store.planGenerationError).toBeNull()
    expect(store.isGeneratingPlans).toBe(false)
  })

  test('does not couple generation to Plan or Task Stores, navigation, or Route mutation helpers', () => {
    expect(storeSource).not.toContain('usePlanStore')
    expect(storeSource).not.toContain('useTaskStore')
    expect(storeSource).not.toContain('uni.navigateTo')
    expect(storeSource).not.toContain('uni.redirectTo')
    expect(storeSource).not.toContain('uni.reLaunch')
    expect(storeSource).not.toContain('uni.switchTab')
  })
})
