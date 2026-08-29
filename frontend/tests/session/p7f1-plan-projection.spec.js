import { beforeEach, describe, expect, test } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import {
  getRequestCalls,
  resetUniRuntime,
  setRequestHandler,
} from './setup/uniRuntime.js'
import { usePlanStore } from '../../src/stores/plan.js'
import { useUserStore } from '../../src/stores/user.js'

const user = { id: 701, nickname: 'Projection User' }

const routePlan = {
  id: 301,
  title: '故宫屋檐探索',
  destination: '故宫博物院',
  ageGroup: '7-12',
  duration: '3小时',
  interests: ['古建筑'],
  taskCount: 3,
  status: 'ready',
  routeStopId: 88,
  sourceSnapshot: {
    routeTitle: '北京文化路线',
    stopName: '故宫博物院',
  },
  progress: { total: 3, completed: 1 },
}

const manualPlan = {
  id: 302,
  title: '手工创建的自然观察',
  destination: '奥林匹克森林公园',
  ageGroup: '7-12',
  duration: '2小时',
  interests: ['自然'],
  taskCount: 0,
  status: 'ready',
  routeStopId: null,
  sourceSnapshot: null,
  progress: { total: 0, completed: 0 },
}

function login() {
  useUserStore().loginSuccess('p7f1-token', user)
}

function respond(options, data) {
  options.success({ statusCode: 200, data: { success: true, data } })
}

function legacyPlan(status) {
  return {
    id: routePlan.id,
    title: routePlan.title,
    destination: routePlan.destination,
    ageGroup: routePlan.ageGroup,
    duration: routePlan.duration,
    interests: routePlan.interests,
    taskCount: routePlan.taskCount,
    status,
  }
}

async function loadProjectedPlan(store) {
  setRequestHandler((options) => {
    expect(options.url.endsWith('/plans')).toBe(true)
    respond(options, { plans: [routePlan, manualPlan] })
  })
  await store.fetchPlans(user.id, { force: true })
}

describe('P7F-1 Plan projection preservation', () => {
  beforeEach(() => {
    resetUniRuntime()
    setActivePinia(createPinia())
  })

  test('keeps route provenance and server-side progress returned by the Plan list', async () => {
    login()
    const store = usePlanStore()

    await loadProjectedPlan(store)

    expect(store.plans.find((plan) => plan.id === routePlan.id)).toMatchObject({
      routeStopId: 88,
      sourceSnapshot: routePlan.sourceSnapshot,
      progress: { total: 3, completed: 1 },
    })
    expect(getRequestCalls()).toHaveLength(1)
  })

  test('keeps explicit null provenance for a manually created Plan', async () => {
    login()
    const store = usePlanStore()

    await loadProjectedPlan(store)

    expect(store.plans.find((plan) => plan.id === manualPlan.id)).toMatchObject({
      routeStopId: null,
      sourceSnapshot: null,
      progress: { total: 0, completed: 0 },
    })
  })

  test.each([
    ['update', 'PATCH', '/plans/301', 'ready', (store) => store.updatePlan(301, { title: '更新标题' }, user.id)],
    ['start', 'POST', '/plans/301/start', 'in-progress', (store) => store.startExploration(301, user.id)],
    ['complete', 'POST', '/plans/301/complete', 'completed', (store) => store.completeExploration(301, user.id)],
  ])('does not erase projection after a legacy-shaped %s response', async (action, method, suffix, status, run) => {
    login()
    const store = usePlanStore()
    await loadProjectedPlan(store)

    setRequestHandler((options) => {
      expect(options.method).toBe(method)
      expect(options.url.endsWith(suffix)).toBe(true)
      respond(options, action === 'complete'
        ? { plan: legacyPlan(status), completedNow: true }
        : { plan: legacyPlan(status) })
    })

    await run(store)

    expect(store.currentPlan).toMatchObject({
      id: routePlan.id,
      status,
      routeStopId: 88,
      sourceSnapshot: routePlan.sourceSnapshot,
      progress: { total: 3, completed: 1 },
    })
    expect(store.plans.find((plan) => plan.id === routePlan.id)).toMatchObject({
      routeStopId: 88,
      sourceSnapshot: routePlan.sourceSnapshot,
      progress: { total: 3, completed: 1 },
    })
  })
})
