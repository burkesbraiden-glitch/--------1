import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test, vi } from 'vitest'
import { createDeferred, flushRuntimePromises } from './setup/uniRuntime.js'

const root = resolve(process.cwd(), '..')
const source = readFileSync(resolve(root, 'frontend/src/pages/route-detail/index.vue'), 'utf8')

const childA = { id: 101, name: '小宁', age: 8, isDefault: true }
const childB = { id: 102, name: '小安', age: 6, isDefault: false }

function asyncMethod(name) {
  const match = source.match(new RegExp(`async ${name}\\(\\) \\{[\\s\\S]*?\\n    \\},`))
  if (!match) return null
  const functionSource = match[0]
    .replace(`async ${name}(`, `async function ${name}(`)
    .replace(/,\s*$/, '')
  return Function('isAuthenticationError', 'endUserSession', `return (${functionSource})`)(() => false, vi.fn())
}

function loadContext({ childFetch, routeFetch } = {}) {
  return {
    routeId: '901',
    pageError: '',
    routeStore: {
      fetchRoute: routeFetch || vi.fn().mockResolvedValue({ id: 901 }),
      isLoading: false,
    },
    childStore: {
      activeChild: childB,
      children: [childA, childB],
      error: null,
      hasRemoteChild: true,
      isLoaded: true,
      isLoading: false,
      fetchChildren: childFetch || vi.fn().mockResolvedValue({ children: [childA, childB] }),
    },
    userStore: {
      isAuthReady: true,
      isLoggedIn: true,
      isRestoring: false,
      userInfo: { id: 8304 },
    },
  }
}

describe('P8.3D Route Detail child-load decoupling', () => {
  test('Route success plus Child success keeps both normal data paths', async () => {
    const loadRoute = asyncMethod('loadRoute')
    const context = loadContext()
    if (loadRoute) context.loadChildren = asyncMethod('loadChildren')?.bind(context)

    await loadRoute.call(context)

    expect(context.routeStore.fetchRoute).toHaveBeenCalledWith('901')
    expect(context.childStore.fetchChildren).toHaveBeenCalledWith(8304)
    expect(context.pageError).toBe('')
  })

  test('Route success plus pending Child load leaves Route state available', async () => {
    const deferred = createDeferred()
    const loadRoute = asyncMethod('loadRoute')
    const context = loadContext({ childFetch: vi.fn(() => deferred.promise) })
    if (loadRoute) context.loadChildren = asyncMethod('loadChildren')?.bind(context)

    const pending = loadRoute.call(context)
    await flushRuntimePromises()

    expect(context.routeStore.fetchRoute).toHaveBeenCalledWith('901')
    expect(context.childStore.fetchChildren).toHaveBeenCalledWith(8304)
    expect(context.pageError).toBe('')
    deferred.resolve({ children: [childA, childB] })
    await pending
  })

  test('exposes a local Child loading state in the generation area', () => {
    expect(source).toContain('isChildLoading()')
    expect(source).toContain('正在加载孩子资料')
    expect(source).toContain('plan-generation-section__child-state')
  })

  test('Route success plus Child failure does not write the Route page error', async () => {
    const loadRoute = asyncMethod('loadRoute')
    const childError = { code: 'NETWORK_ERROR', message: 'children unavailable' }
    const context = loadContext({ childFetch: vi.fn().mockRejectedValue(childError) })
    if (loadRoute) context.loadChildren = asyncMethod('loadChildren')?.bind(context)

    await loadRoute.call(context)

    expect(context.routeStore.fetchRoute).toHaveBeenCalledWith('901')
    expect(context.pageError).toBe('')
  })

  test('renders a local Child failure instead of the Route failure state', () => {
    expect(source).toContain('hasChildLoadError()')
    expect(source).toContain('孩子资料加载失败')
    expect(source).toContain('v-else-if="pageError || (!currentRoute && routeStore.error)"')
  })

  test('offers a dedicated Child retry control', () => {
    expect(source).toContain('retryChildren')
    expect(source).toContain('重试加载孩子资料')
  })

  test('Child retry calls only Child loading and never refetches Route', async () => {
    const retryChildren = asyncMethod('retryChildren')
    const loadChildren = asyncMethod('loadChildren')
    expect(retryChildren).toBeTypeOf('function')
    expect(loadChildren).toBeTypeOf('function')
    if (!retryChildren || !loadChildren) return

    const context = loadContext()
    context.loadChildren = loadChildren.bind(context)
    await retryChildren.call(context)

    expect(context.childStore.fetchChildren).toHaveBeenCalledWith(8304)
    expect(context.routeStore.fetchRoute).not.toHaveBeenCalled()
  })

  test('renders a local no-child state and keeps generation unavailable', () => {
    expect(source).toContain('hasNoChildren()')
    expect(source).toContain('尚未添加孩子')
    expect(source).toContain('canOpenPlanGenerationSheet()')
  })

  test('does not open the generation Sheet without a valid Child context', () => {
    const openSource = source.match(/openPlanGenerationSheet\(\) \{[\s\S]*?\n    \},/)?.[0] || ''

    expect(openSource).toContain('canOpenPlanGenerationSheet')
    expect(openSource).not.toContain('children[0]')
  })

  test('keeps C3 active Child as the generation Sheet default', () => {
    expect(source).toContain('const activeChildId = this.childStore.activeChild?.id')
    expect(source).toContain('String(child.id) === String(activeChildId)')
  })

  test('keeps explicit Child selection as the generation request parameter', () => {
    expect(source).toContain('selectGenerationChild(childId) { this.selectedChildId = childId }')
    expect(source).toContain('this.selectedChildId,\n          this.selectedRouteStopIds,')
  })

  test('Route fetch failure still writes the Route page error without fetching Children', async () => {
    const loadRoute = asyncMethod('loadRoute')
    const context = loadContext({ routeFetch: vi.fn().mockRejectedValue({ code: 'ROUTE_NOT_FOUND', message: 'route missing' }) })
    if (loadRoute) context.loadChildren = asyncMethod('loadChildren')?.bind(context)

    await loadRoute.call(context)

    expect(context.pageError).toBe('route missing')
    expect(context.childStore.fetchChildren).not.toHaveBeenCalled()
  })

  test('Route error remains higher priority than any Child-local state', () => {
    const routeErrorState = source.indexOf('v-else-if="pageError || (!currentRoute && routeStore.error)"')
    const generationSection = source.indexOf('class="plan-generation-section"')

    expect(routeErrorState).toBeGreaterThanOrEqual(0)
    expect(generationSection).toBeGreaterThan(routeErrorState)
  })

  test('a recovered Child context restores capability without another Route fetch', async () => {
    const retryChildren = asyncMethod('retryChildren')
    const loadChildren = asyncMethod('loadChildren')
    expect(retryChildren).toBeTypeOf('function')
    expect(loadChildren).toBeTypeOf('function')
    if (!retryChildren || !loadChildren) return

    const context = loadContext()
    let childAttempt = 0
    context.childStore.fetchChildren = vi.fn(async () => {
      childAttempt += 1
      if (childAttempt === 1) {
        context.childStore.error = { code: 'NETWORK_ERROR' }
        context.childStore.isLoaded = false
        throw context.childStore.error
      }
      context.childStore.error = null
      context.childStore.isLoaded = true
      return { children: [childA, childB] }
    })
    context.loadChildren = loadChildren.bind(context)

    await context.loadChildren()
    await retryChildren.call(context)

    expect(context.childStore.fetchChildren).toHaveBeenCalledTimes(2)
    expect(context.routeStore.fetchRoute).not.toHaveBeenCalled()
    expect(context.childStore.error).toBeNull()
    expect(context.childStore.isLoaded).toBe(true)
  })

  test('Child auth errors remain routed through the existing session boundary', () => {
    const loadChildrenSource = source.match(/async loadChildren\(\) \{[\s\S]*?\n    \},/)?.[0] || ''

    expect(loadChildrenSource).toContain('isAuthenticationError(error)')
    expect(loadChildrenSource).toContain('endUserSession()')
  })
})
