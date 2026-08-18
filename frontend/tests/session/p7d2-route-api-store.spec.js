import { existsSync } from 'node:fs'
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
import { useUserStore } from '../../src/stores/user.js'

const root = resolve(process.cwd(), '..')
const apiModulePath = resolve(root, 'frontend/src/api/routes.js')
const storeModulePath = resolve(root, 'frontend/src/stores/route.js')

const userA = { id: 101, nickname: 'Route User A' }
const userB = { id: 202, nickname: 'Route User B' }

function routeDetail(id = 1, title = '北京亲子路线') {
  return {
    id,
    title,
    city: '北京',
    status: 'draft',
    days: [
      {
        id: 12,
        dayNumber: 2,
        stops: [
          { id: 122, sortOrder: 2, attraction: { id: 22, name: '后海' } },
          { id: 121, sortOrder: 1, attraction: { id: 21, name: '故宫' } },
        ],
      },
      {
        id: 11,
        dayNumber: 1,
        stops: [
          { id: 111, sortOrder: 1, attraction: { id: 11, name: '天坛' } },
        ],
      },
    ],
  }
}

function login(user) {
  useUserStore().loginSuccess(`route-token-${user.id}`, user)
}

function respond(options, data, statusCode = 200) {
  options.success({ statusCode, data: { success: true, data } })
}

function hasRouteLayer() {
  return existsSync(apiModulePath) && existsSync(storeModulePath)
}

async function loadRouteLayer() {
  return {
    api: await import('../../src/api/routes.js'),
    useRouteStore: (await import('../../src/stores/route.js')).useRouteStore,
  }
}

describe('P7D-2 Route API client and independent Store', () => {
  beforeEach(() => {
    resetUniRuntime()
    setActivePinia(createPinia())
  })

  test('requires the Route API and Store modules before runtime contracts can run', () => {
    expect(existsSync(apiModulePath)).toBe(true)
    expect(existsSync(storeModulePath)).toBe(true)
  })

  test('sends authenticated Route list requests with no empty query or unsupported filters', async () => {
    if (!hasRouteLayer()) return
    const { api } = await loadRouteLayer()
    login(userA)
    setRequestHandler((options) => respond(options, { items: [], total: 0, limit: 20, offset: 0 }))

    await api.getRoutes()

    expect(getRequestCalls()).toEqual([expect.objectContaining({
      method: 'GET',
      url: 'http://session.test/api/v1/routes',
      header: expect.objectContaining({ Authorization: 'Bearer route-token-101' }),
    })])
  })

  test('encodes only supported Route list pagination parameters', async () => {
    if (!hasRouteLayer()) return
    const { api } = await loadRouteLayer()
    login(userA)
    setRequestHandler((options) => respond(options, { items: [], total: 0, limit: 7, offset: 12 }))

    await api.getRoutes({ limit: 7, offset: 12, city: '北京', status: 'ready' })

    expect(getRequestCalls()[0]).toMatchObject({
      method: 'GET',
      url: 'http://session.test/api/v1/routes?limit=7&offset=12',
    })
  })

  test('preserves Route CRUD paths and payloads through the shared request client', async () => {
    if (!hasRouteLayer()) return
    const { api } = await loadRouteLayer()
    login(userA)
    setRequestHandler((options) => respond(options, options.method === 'DELETE' ? {} : { route: routeDetail() }))
    const payload = { title: '周末路线', city: '北京', startDate: '2026-08-20' }

    await api.createRoute(payload)
    await api.getRoute(1)
    await api.updateRoute(1, { title: '更新路线' })
    await api.deleteRoute(1)

    expect(getRequestCalls().map(({ method, url, data }) => ({ method, url, data }))).toEqual([
      { method: 'POST', url: 'http://session.test/api/v1/routes', data: payload },
      { method: 'GET', url: 'http://session.test/api/v1/routes/1', data: undefined },
      { method: 'PATCH', url: 'http://session.test/api/v1/routes/1', data: { title: '更新路线' } },
      { method: 'DELETE', url: 'http://session.test/api/v1/routes/1', data: undefined },
    ])
  })

  test('preserves Route day and stop CRUD plus reorder paths and payloads', async () => {
    if (!hasRouteLayer()) return
    const { api } = await loadRouteLayer()
    login(userA)
    setRequestHandler((options) => respond(options, { route: routeDetail() }))

    await api.createRouteDay(1, { date: '2026-08-20' })
    await api.updateRouteDay(1, 11, { title: '第一天' })
    await api.deleteRouteDay(1, 11)
    await api.reorderRouteDays(1, [12, 11])
    await api.createRouteStop(1, 11, { attractionId: 11 })
    await api.updateRouteStop(1, 11, 111, { note: '上午抵达' })
    await api.deleteRouteStop(1, 11, 111)
    await api.reorderRouteStops(1, 11, [122, 121])

    expect(getRequestCalls().map(({ method, url, data }) => ({ method, url, data }))).toEqual([
      { method: 'POST', url: 'http://session.test/api/v1/routes/1/days', data: { date: '2026-08-20' } },
      { method: 'PATCH', url: 'http://session.test/api/v1/routes/1/days/11', data: { title: '第一天' } },
      { method: 'DELETE', url: 'http://session.test/api/v1/routes/1/days/11', data: undefined },
      { method: 'PATCH', url: 'http://session.test/api/v1/routes/1/days/reorder', data: { dayIds: [12, 11] } },
      { method: 'POST', url: 'http://session.test/api/v1/routes/1/days/11/stops', data: { attractionId: 11 } },
      { method: 'PATCH', url: 'http://session.test/api/v1/routes/1/days/11/stops/111', data: { note: '上午抵达' } },
      { method: 'DELETE', url: 'http://session.test/api/v1/routes/1/days/11/stops/111', data: undefined },
      { method: 'PATCH', url: 'http://session.test/api/v1/routes/1/days/11/stops/reorder', data: { stopIds: [122, 121] } },
    ])
  })

  test('normalizes list and nested ordering while using returned Routes as create and update truth', async () => {
    if (!hasRouteLayer()) return
    const { useRouteStore } = await loadRouteLayer()
    login(userA)
    const store = useRouteStore()
    let requestIndex = 0
    const initialRoute = routeDetail(1, '初始路线')
    const createdRoute = { ...routeDetail(2, '服务器创建路线'), status: 'draft' }
    const updatedRoute = { ...routeDetail(2, '服务器更新路线'), status: 'ready' }
    setRequestHandler((options) => {
      requestIndex += 1
      if (requestIndex === 1) {
        respond(options, { items: [initialRoute], total: 1, limit: 20, offset: 0 })
        return
      }
      respond(options, { route: requestIndex === 2 ? createdRoute : updatedRoute })
    })

    await store.fetchRoutes(userA.id)
    expect(store.routes[0].days.map((day) => day.dayNumber)).toEqual([1, 2])
    expect(store.routes[0].days[1].stops.map((stop) => stop.sortOrder)).toEqual([1, 2])

    await store.createRoute({ title: '客户端不应成为真相', city: '北京' })
    expect(store.currentRoute.title).toBe('服务器创建路线')

    await store.updateRoute(2, { title: '客户端不应成为真相' })
    expect(store.currentRoute.title).toBe('服务器更新路线')
    expect(store.currentRoute.status).toBe('ready')
    expect(store.routes.find((route) => route.id === 2).title).toBe('服务器更新路线')
  })

  test('applies returned full Routes for day and stop mutations and clears deleted Routes', async () => {
    if (!hasRouteLayer()) return
    const { useRouteStore } = await loadRouteLayer()
    login(userA)
    const store = useRouteStore()
    const returnedRoute = routeDetail(1, '服务端完整路线')
    setRequestHandler((options) => {
      if (options.method === 'DELETE' && options.url.endsWith('/routes/1')) {
        respond(options, {})
        return
      }
      respond(options, { route: returnedRoute })
    })

    await store.createDay(1, {})
    await store.updateDay(1, 11, {})
    await store.deleteDay(1, 11)
    await store.reorderDays(1, [11, 12])
    await store.createStop(1, 11, { attractionId: 11 })
    await store.updateStop(1, 11, 111, { note: '备注' })
    await store.deleteStop(1, 11, 111)
    await store.reorderStops(1, 11, [111])
    expect(store.currentRoute.title).toBe('服务端完整路线')

    await store.deleteRoute(1)
    expect(store.routes).toEqual([])
    expect(store.currentRoute).toBeNull()
  })

  test('resets Route state and ignores a late User A response after User B signs in', async () => {
    if (!hasRouteLayer()) return
    const { useRouteStore } = await loadRouteLayer()
    const routesA = createDeferred()
    const routesB = createDeferred()
    let routeRequestCount = 0
    setRequestHandler((options) => {
      routeRequestCount += 1
      const pending = routeRequestCount === 1 ? routesA : routesB
      pending.promise.then((data) => respond(options, data))
    })

    const store = useRouteStore()
    login(userA)
    const pendingA = store.fetchRoutes(userA.id)
    await flushRuntimePromises()
    login(userB)
    const pendingB = store.fetchRoutes(userB.id)
    await flushRuntimePromises()

    routesB.resolve({ items: [routeDetail(2, '用户 B 路线')], total: 1, limit: 20, offset: 0 })
    await pendingB
    routesA.resolve({ items: [routeDetail(1, '用户 A 路线')], total: 1, limit: 20, offset: 0 })
    await pendingA

    expect(store.loadedForUserId).toBe(userB.id)
    expect(store.routes.map((route) => route.id)).toEqual([2])

    store.resetSessionState()
    expect(store.routes).toEqual([])
    expect(store.currentRoute).toBeNull()
    expect(store.isLoading).toBe(false)
    expect(store.error).toBeNull()
    expect(store.isLoaded).toBe(false)
    expect(store.loadedForUserId).toBeNull()
  })
})
