import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useChildStore } from '../../src/stores/child.js'
import { useUserStore } from '../../src/stores/user.js'
import {
  resetUniRuntime,
  setRequestHandler,
} from './setup/uniRuntime.js'

const root = resolve(process.cwd(), '..')
const readFrontendFile = (path) => readFileSync(resolve(root, 'frontend', path), 'utf8')
const childSource = readFrontendFile('src/stores/child.js')
const homeSource = readFrontendFile('src/pages/home/index.vue')
const routeSource = readFrontendFile('src/pages/route-detail/index.vue')
const recordSource = readFrontendFile('src/pages/record/index.vue')
const tasksSource = readFrontendFile('src/pages/tasks/index.vue')
const guideSource = readFrontendFile('src/pages/guide/index.vue')

const user = { id: 8405, nickname: 'P8.4D Parent' }
const childA = { id: 101, name: '小宁', age: 8, ageGroup: '7-12', city: '北京', interests: ['古建筑'], isDefault: true }
const childB = { id: 102, name: '小安', age: 6, ageGroup: '3-6', city: '西安', interests: ['博物馆'], isDefault: false }

function respond(options, data, statusCode = 200) {
  options.success({ statusCode, data: { success: true, data } })
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

const loadRecords = pageMethod(recordSource, 'loadRecords', {
  isAuthenticationError: () => false,
})

function login() {
  useUserStore().loginSuccess('p8-4d-token', user)
}

function recordWithoutChildContext() {
  return {
    childStore: {
      activeChild: null,
      hasRemoteChild: false,
      isLoaded: true,
      error: null,
      loadedForUserId: user.id,
      fetchChildren: vi.fn(),
    },
    recordStore: { loadJourneyRecords: vi.fn() },
    hasActiveChild: false,
    hasCurrentChild: false,
    handleAuthExpired: vi.fn(),
    userStore: {
      isAuthReady: true,
      isRestoring: false,
      isLoggedIn: true,
      userInfo: user,
    },
  }
}

describe('P8.4D FALLBACK_CHILD cleanup contract', () => {
  beforeEach(() => {
    resetUniRuntime()
    setActivePinia(createPinia())
  })

  test('initial, successful-empty, and reset states have no active or current fake child', async () => {
    const child = useChildStore()
    expect(child.activeChild).toBeNull()
    expect(child.currentChild).toBeNull()

    login()
    setRequestHandler((options) => respond(options, { children: [], currentChild: null }))
    await child.fetchChildren(user.id)

    expect(child.activeChild).toBeNull()
    expect(child.currentChild).toBeNull()

    child.resetSessionState()
    expect(child.activeChild).toBeNull()
    expect(child.currentChild).toBeNull()
  })

  test('a first children fetch error cannot create a fallback child', async () => {
    login()
    setRequestHandler((options) => options.fail({ errMsg: 'request:fail offline' }))

    const child = useChildStore()
    await expect(child.fetchChildren(user.id)).rejects.toMatchObject({ code: 'NETWORK_ERROR' })

    expect(child.activeChild).toBeNull()
    expect(child.currentChild).toBeNull()
  })

  test('Home routes into Route planning without a Child fallback or manual Plan creation path', () => {
    expect(homeSource).toContain('goToRoutePlanning()')
    expect(homeSource).toContain("uni.reLaunch({ url: '/pages/route/index' })")
    expect(homeSource).not.toContain('createPlan(')
    expect(homeSource).not.toContain('currentChild.id')
  })

  test('Home reflects only the real active Child age group without writing a Child profile', () => {
    expect(homeSource).toContain('activeChildAgeGroup')
    expect(homeSource).toContain('this.activeChild?.ageGroup')
    expect(homeSource).not.toContain('children[0]')
    expect(homeSource).not.toContain('updateChild(')
    expect(homeSource).not.toContain('createChild(')
    expect(homeSource).toContain('selectedAgeGroup')
  })

  test('Route generation requires real children and only accepts a real active child ID', () => {
    expect(routeSource).toContain('realChildren() { return this.childStore.children.filter')
    expect(routeSource).toContain('canOpenPlanGenerationSheet() { return this.isRouteReady && this.hasRealChildren')
    expect(routeSource).toContain('this.realChildren.some((child) => String(child.id) === String(activeChildId)) ? activeChildId : null')
  })

  test('Records does not request unscoped data without an active child', async () => {
    const context = recordWithoutChildContext()

    await loadRecords.call(context)

    expect(context.recordStore.loadJourneyRecords).not.toHaveBeenCalled()
  })

  test('Tasks and Guide have no fallback-child path and retain their current-plan empty handling', () => {
    expect(tasksSource).not.toContain('FALLBACK_CHILD')
    expect(tasksSource).toContain('当前孩子还没有探索计划')
    expect(guideSource).not.toContain('FALLBACK_CHILD')
    expect(guideSource).toContain('当前孩子暂无可用探索计划')
  })

  test('a real active child retains its own age group and interests through a switch', () => {
    login()
    const child = useChildStore()
    child.applyChildrenPayload({ children: [childA, childB], currentChild: childA }, user.id)

    expect(child.activeChild).toMatchObject({ id: childA.id, ageGroup: childA.ageGroup, interests: childA.interests })
    expect(child.setActiveChild(childB.id)).toBe(true)
    expect(child.activeChild).toMatchObject({ id: childB.id, ageGroup: childB.ageGroup, interests: childB.interests })
  })

  test('the production Child Store contains no static fallback child', () => {
    expect(childSource).not.toContain('FALLBACK_CHILD')
    expect(childSource).not.toContain('fallbackChild')
  })
})
