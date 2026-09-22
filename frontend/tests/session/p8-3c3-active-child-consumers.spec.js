import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test, vi } from 'vitest'

const root = resolve(process.cwd(), '..')
const recordSource = readFileSync(resolve(root, 'frontend/src/pages/record/index.vue'), 'utf8')
const homeSource = readFileSync(resolve(root, 'frontend/src/pages/home/index.vue'), 'utf8')
const routeDetailSource = readFileSync(resolve(root, 'frontend/src/pages/route-detail/index.vue'), 'utf8')

const childA = {
  id: 101,
  name: '小宁',
  age: 8,
  city: '北京',
  ageGroup: '7-12',
  interests: ['古建筑'],
  isDefault: true,
}
const childB = {
  id: 102,
  name: '小安',
  age: 6,
  city: '西安',
  ageGroup: '3-6',
  interests: ['博物馆', '自然观察'],
  isDefault: false,
}

function methodFrom(source, name, dependencies = {}) {
  const match = source.match(new RegExp(`(?:async )?${name}\\(([^)]*)\\) \\{[\\s\\S]*?\\n    \\},`))
  if (!match) {
    throw new Error(`Missing ${name} method`)
  }
  const functionSource = (match[0].startsWith(`async ${name}(`)
    ? match[0].replace(`async ${name}(`, `async function ${name}(`)
    : match[0].replace(`${name}(`, `function ${name}(`))
    .replace(/,\s*$/, '')
  return Function(...Object.keys(dependencies), `return (${functionSource})`)(...Object.values(dependencies))
}

const recordLoadRecords = methodFrom(recordSource, 'loadRecords', {
  isAuthenticationError: () => false,
})
const recordRetryRecords = methodFrom(recordSource, 'retryRecords')
const openPlanSheet = methodFrom(homeSource, 'openPlanSheet')
const submitPlan = methodFrom(homeSource, 'submitPlan')
const openPlanGenerationSheet = methodFrom(routeDetailSource, 'openPlanGenerationSheet')
const submitPlanGeneration = methodFrom(routeDetailSource, 'submitPlanGeneration', {
  isAuthenticationError: () => false,
  endUserSession: vi.fn(),
})

function recordContext({ activeChild = childB, currentChild = childA } = {}) {
  const childStore = {
    activeChild,
    currentChild,
    error: null,
    fetchChildren: vi.fn().mockResolvedValue({}),
    hasRemoteChild: true,
    isLoaded: true,
    loadedForUserId: 8303,
  }
  const recordStore = { loadJourneyRecords: vi.fn().mockResolvedValue([]) }
  return {
    childStore,
    recordStore,
    hasActiveChild: Boolean(activeChild),
    hasCurrentChild: Boolean(currentChild),
    handleAuthExpired: vi.fn(),
    userStore: {
      isAuthReady: true,
      isLoggedIn: true,
      isRestoring: false,
      userInfo: { id: 8303 },
    },
  }
}

function homeContext(activeChild = childB) {
  const context = {
    child: {
      activeChild,
      currentChild: childA,
      hasRemoteChild: true,
      fetchChildren: vi.fn().mockResolvedValue({}),
      setAgeGroup: vi.fn(),
    },
    isCreatingPlan: false,
    plan: { createPlan: vi.fn().mockResolvedValue({ id: 7001 }) },
    planErrorMessage: vi.fn(() => '创建失败'),
    planForm: {
      title: '',
      destination: '西安城墙',
      ageGroup: activeChild?.ageGroup || '3-6',
      duration: '2小时',
      interests: activeChild ? [...activeChild.interests] : ['博物馆'],
    },
    planSheetOpen: true,
    searchKeyword: '',
    showToast: vi.fn(),
    handleAuthExpired: vi.fn(),
    user: {
      isAuthReady: true,
      isLoggedIn: true,
      isRestoring: false,
      userInfo: { id: 8303 },
    },
  }
  Object.defineProperty(context, 'activeChild', {
    get() {
      return context.child.activeChild
    },
  })
  return context
}

function routeContext() {
  return {
    childStore: { activeChild: childB, currentChild: childA },
    currentRoute: { id: 901, status: 'ready' },
    realChildren: [childA, childB],
    selectedChildId: null,
    selectedRouteStopIds: [81],
    showPlanGenerationSheet: false,
    hasSubmittedGeneration: true,
    planGenerationError: '旧错误',
    canSubmitPlanGeneration: true,
    routeStore: {
      isGeneratingPlans: false,
      generateExplorationPlans: vi.fn().mockResolvedValue({ results: [] }),
    },
  }
}

describe('P8.3C3 active-child safe consumers', () => {
  test('Records request uses active Child instead of backend current Child', async () => {
    const context = recordContext()

    await recordLoadRecords.call(context)

    expect(context.recordStore.loadJourneyRecords).toHaveBeenCalledWith({ childId: childB.id, limit: 20, offset: 0 })
  })

  test('Records title is sourced from active Child', () => {
    expect(recordSource).toContain('childStore.activeChild.name')
    expect(recordSource).not.toContain('childStore.currentChild.name')
  })

  test('Records retry delegates to active-context loading', async () => {
    const context = { loadRecords: vi.fn().mockResolvedValue() }

    await recordRetryRecords.call(context)

    expect(context.loadRecords).toHaveBeenCalledOnce()
  })

  test('Records never requests unscoped data when active Child is unavailable', async () => {
    const context = recordContext({ activeChild: null, currentChild: childA })

    await recordLoadRecords.call(context)

    expect(context.recordStore.loadJourneyRecords).not.toHaveBeenCalled()
  })

  test('Home opens a new-plan form from the current active Child context', () => {
    const context = homeContext(childA)

    openPlanSheet.call(context)
    expect(context.planForm).toMatchObject({ ageGroup: childA.ageGroup, interests: childA.interests })

    context.child.activeChild = childB
    openPlanSheet.call(context)

    expect(context.planForm).toMatchObject({ ageGroup: childB.ageGroup, interests: childB.interests })
  })

  test('Home creates a new Plan with active Child ID and active context', async () => {
    const context = homeContext(childB)

    await submitPlan.call(context)

    expect(context.plan.createPlan).toHaveBeenCalledWith(expect.objectContaining({
      childId: childB.id,
      ageGroup: childB.ageGroup,
      interests: childB.interests,
    }), 8303)
  })

  test('Home does not create a Plan when no active Child exists', async () => {
    const context = homeContext(null)

    await submitPlan.call(context)

    expect(context.plan.createPlan).not.toHaveBeenCalled()
    expect(context.showToast).toHaveBeenCalledWith('请先完善孩子档案')
  })

  test('Home AudioGuideSheet stays bound to its explicit existing plan ID', () => {
    const openAudioGuideSource = homeSource.match(/async openAudioGuide\(\) \{[\s\S]*?\n    \},/)?.[0] || ''

    expect(openAudioGuideSource).toContain('result.currentPlan.id')
    expect(openAudioGuideSource).not.toContain('activeChild')
  })

  test('Route generation Sheet defaults to active Child when backend current differs', () => {
    const context = routeContext()

    openPlanGenerationSheet.call(context)

    expect(context.selectedChildId).toBe(childB.id)
    expect(context.currentRoute).toEqual({ id: 901, status: 'ready' })
  })

  test('Route explicit selection remains authoritative until the Sheet is closed', () => {
    const context = routeContext()
    openPlanGenerationSheet.call(context)

    context.selectedChildId = childA.id

    expect(context.selectedChildId).toBe(childA.id)
    expect(routeDetailSource).toContain('selectGenerationChild(childId) { this.selectedChildId = childId }')
  })

  test('Route generation submits the explicit selected Child, not active Child', async () => {
    const context = routeContext()
    openPlanGenerationSheet.call(context)
    context.selectedChildId = childA.id
    context.selectedRouteStopIds = [81]

    await submitPlanGeneration.call(context)

    expect(context.routeStore.generateExplorationPlans).toHaveBeenCalledWith(901, childA.id, [81])
  })

  test('Route reopening retains existing reset semantics but uses the active default again', () => {
    const context = routeContext()
    openPlanGenerationSheet.call(context)
    context.selectedChildId = childA.id
    context.showPlanGenerationSheet = false

    openPlanGenerationSheet.call(context)

    expect(context.selectedChildId).toBe(childB.id)
  })

  test('Route itself remains independent of active Child ownership', () => {
    const loadRouteSource = routeDetailSource.match(/async loadRoute\(\) \{[\s\S]*?\n    \},\n    async handleRequestError/)?.[0] || ''

    expect(loadRouteSource).toContain('this.routeStore.fetchRoute(this.routeId)')
    expect(loadRouteSource).not.toContain('activeChild')
  })
})
