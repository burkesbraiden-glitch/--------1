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
import { useUserStore } from '../../src/stores/user.js'
import { endUserSession } from '../../src/utils/sessionBoundary.js'

const userA = { id: 8101, nickname: 'Active Child Parent A' }
const userB = { id: 8102, nickname: 'Active Child Parent B' }

const childrenA = [
  { id: 101, name: '小宁', age: 8, city: '北京', interests: ['古建筑'], isDefault: true },
  { id: 102, name: '小安', age: 6, city: '西安', interests: ['博物馆'], isDefault: false },
]

const childrenB = [
  { id: 201, name: '小北', age: 9, city: '南京', interests: ['历史故事'], isDefault: true },
]

function login(user) {
  useUserStore().loginSuccess(`active-child-token-${user.id}`, user)
}

function respond(options, data, statusCode = 200) {
  options.success({ statusCode, data: { success: true, data } })
}

function respondLogout(options) {
  if (options.url.endsWith('/auth/logout')) {
    respond(options, {})
    return true
  }
  return false
}

function childrenPayload(children, currentChild = children[0] || null) {
  return { children, currentChild }
}

function seedChildren(store, children = childrenA, currentChild = children[0] || null) {
  store.applyChildrenPayload(childrenPayload(children, currentChild), useUserStore().userInfo.id)
}

describe('P8.3C1 Child Store active-context contract', () => {
  beforeEach(() => {
    resetUniRuntime()
    setActivePinia(createPinia())
  })

  test('initializes active child from the backend current child on the first successful load', async () => {
    login(userA)
    setRequestHandler((options) => {
      expect(options.method).toBe('GET')
      expect(options.url).toMatch(/\/children$/)
      respond(options, childrenPayload(childrenA, childrenA[0]))
    })

    const child = useChildStore()
    await child.fetchChildren(userA.id)

    expect(child.currentChild.id).toBe(101)
    expect(child.activeChildId).toBe(101)
    expect(child.activeChild).toMatchObject({ id: 101, name: '小宁' })
  })

  test('clears active context after a successful empty children response', async () => {
    login(userA)
    setRequestHandler((options) => respond(options, childrenPayload([])))

    const child = useChildStore()
    await child.fetchChildren(userA.id)

    expect(child.children).toEqual([])
    expect(child.activeChildId).toBeNull()
    expect(child.activeChild).toBeNull()
  })

  test('switches to a valid loaded child without changing backend current child', () => {
    login(userA)
    const child = useChildStore()
    seedChildren(child)

    expect(child.setActiveChild(102)).toBe(true)
    expect(child.activeChildId).toBe(102)
    expect(child.activeChild).toMatchObject({ id: 102, name: '小安' })
    expect(child.currentChild.id).toBe(101)
  })

  test('does not make a PATCH request when switching active child', () => {
    login(userA)
    const child = useChildStore()
    seedChildren(child)

    const requestsBeforeSwitch = getRequestCalls()
    child.setActiveChild(102)

    expect(getRequestCalls()).toEqual(requestsBeforeSwitch)
    expect(getRequestCalls().some((request) => request.method === 'PATCH')).toBe(false)
  })

  test('rejects an unknown active child without changing the existing active context', () => {
    login(userA)
    const child = useChildStore()
    seedChildren(child)

    expect(child.activeChildId).toBe(101)
    expect(child.setActiveChild(999)).toBe(false)
    expect(child.activeChildId).toBe(101)
    expect(child.activeChild.id).toBe(101)
  })

  test('preserves a still-valid active child across a refresh with another backend default', async () => {
    login(userA)
    const responses = [
      childrenPayload(childrenA, childrenA[0]),
      childrenPayload(childrenA, childrenA[0]),
    ]
    setRequestHandler((options) => respond(options, responses.shift()))

    const child = useChildStore()
    await child.fetchChildren(userA.id)
    child.setActiveChild(102)
    await child.fetchChildren(userA.id)

    expect(child.currentChild.id).toBe(101)
    expect(child.activeChildId).toBe(102)
    expect(child.activeChild.id).toBe(102)
  })

  test('falls back to backend current child when the previous active child disappears on refresh', async () => {
    login(userA)
    const responses = [
      childrenPayload(childrenA, childrenA[0]),
      childrenPayload([childrenA[0]], childrenA[0]),
    ]
    setRequestHandler((options) => respond(options, responses.shift()))

    const child = useChildStore()
    await child.fetchChildren(userA.id)
    child.setActiveChild(102)
    await child.fetchChildren(userA.id)

    expect(child.activeChildId).toBe(101)
    expect(child.activeChild.id).toBe(101)
  })

  test('clears active context when the shared logout boundary ends the session', async () => {
    login(userA)
    const child = useChildStore()
    seedChildren(child)
    child.setActiveChild(102)
    setRequestHandler((options) => {
      expect(respondLogout(options)).toBe(true)
    })

    await endUserSession()

    expect(child.children).toEqual([])
    expect(child.activeChildId).toBeNull()
    expect(child.activeChild).toBeNull()
    expect(child.loadedForUserId).toBeNull()
  })

  test('does not leak User A active context into User B', async () => {
    login(userA)
    const child = useChildStore()
    seedChildren(child)
    child.setActiveChild(102)
    setRequestHandler((options) => {
      if (respondLogout(options)) return
      respond(options, childrenPayload(childrenB, childrenB[0]))
    })

    await endUserSession()
    login(userB)
    await child.fetchChildren(userB.id)

    expect(child.loadedForUserId).toBe(userB.id)
    expect(child.activeChildId).toBe(201)
    expect(child.activeChild).toMatchObject({ id: 201, name: '小北' })
  })

  test('does not let a stale User A children response restore User A active context', async () => {
    const deferredA = createDeferred()
    const deferredB = createDeferred()
    let childrenRequestCount = 0
    setRequestHandler((options) => {
      if (respondLogout(options)) return
      childrenRequestCount += 1
      const deferred = childrenRequestCount === 1 ? deferredA : deferredB
      deferred.promise.then((data) => respond(options, data))
    })

    login(userA)
    const child = useChildStore()
    const pendingA = child.fetchChildren(userA.id)
    await flushRuntimePromises()
    await endUserSession()
    login(userB)
    const pendingB = child.fetchChildren(userB.id)
    await flushRuntimePromises()

    deferredB.resolve(childrenPayload(childrenB, childrenB[0]))
    await pendingB
    deferredA.resolve(childrenPayload(childrenA, childrenA[0]))
    await pendingA

    expect(child.loadedForUserId).toBe(userB.id)
    expect(child.activeChildId).toBe(201)
    expect(child.activeChild.id).toBe(201)
  })

  test('establishes active context when the first child is created', async () => {
    login(userA)
    setRequestHandler((options) => {
      expect(options.method).toBe('POST')
      respond(options, { child: childrenA[0] }, 201)
    })

    const child = useChildStore()
    await child.createChild({ name: '小宁', age: 8, city: '北京', interests: ['古建筑'] })

    expect(child.activeChildId).toBe(101)
    expect(child.activeChild).toMatchObject({ id: 101, name: '小宁' })
  })

  test('does not let a second non-default child take over active context', async () => {
    login(userA)
    const responses = [childrenA[0], childrenA[1]]
    setRequestHandler((options) => {
      expect(options.method).toBe('POST')
      respond(options, { child: responses.shift() }, 201)
    })

    const child = useChildStore()
    await child.createChild({ name: '小宁', age: 8, city: '北京', interests: ['古建筑'] })
    await child.createChild({ name: '小安', age: 6, city: '西安', interests: ['博物馆'] })

    expect(child.activeChildId).toBe(101)
    expect(child.activeChild.id).toBe(101)
    expect(child.children.map((item) => item.id)).toEqual([101, 102])
  })

  test('updates derived active child data without changing its active ID', async () => {
    login(userA)
    const child = useChildStore()
    seedChildren(child)
    const updatedActiveChild = { ...childrenA[0], age: 9, city: '南京', interests: ['城墙'], isDefault: true }
    setRequestHandler((options) => {
      expect(options.method).toBe('PATCH')
      expect(options.url).toMatch(/\/children\/101$/)
      respond(options, { child: updatedActiveChild })
    })

    await child.updateChild(101, { age: 9, city: '南京', interests: ['城墙'] })

    expect(child.activeChildId).toBe(101)
    expect(child.activeChild).toMatchObject({ id: 101, age: 9, city: '南京', interests: ['城墙'] })
  })

  test('does not change active ID when another child is updated', async () => {
    login(userA)
    const child = useChildStore()
    seedChildren(child)
    const updatedInactiveChild = { ...childrenA[1], age: 7, city: '洛阳', interests: ['石窟'], isDefault: false }
    setRequestHandler((options) => {
      expect(options.method).toBe('PATCH')
      expect(options.url).toMatch(/\/children\/102$/)
      respond(options, { child: updatedInactiveChild })
    })

    await child.updateChild(102, { age: 7, city: '洛阳', interests: ['石窟'] })

    expect(child.activeChildId).toBe(101)
    expect(child.activeChild).toMatchObject({ id: 101, name: '小宁' })
    expect(child.children.find((item) => item.id === 102)).toMatchObject({ age: 7, city: '洛阳' })
  })
})
