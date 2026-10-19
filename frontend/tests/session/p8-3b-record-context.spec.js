import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { beforeEach, describe, expect, test, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { flushRuntimePromises, resetUniRuntime } from './setup/uniRuntime.js'

const root = resolve(process.cwd(), '..')
const recordPageSource = readFileSync(resolve(root, 'frontend/src/pages/record/index.vue'), 'utf8')
const recordStoreSource = readFileSync(resolve(root, 'frontend/src/stores/record.js'), 'utf8')

function pageMethod(name) {
  const match = recordPageSource.match(new RegExp(`async ${name}\\(\\) \\{[\\s\\S]*?\\n    \\},`))
  if (!match) {
    throw new Error(`Missing ${name} method`)
  }
  return Function('isAuthenticationError', `return (${match[0].replace(`async ${name}()`, `async function ${name}()`).replace(/,\s*$/, '')})`)(() => false)
}

function pageContext({ childStore, recordStore }) {
  const childId = Number(childStore.activeChild?.id)
  return {
    childStore,
    handleAuthExpired: vi.fn(),
    hasActiveChild: (
      childStore.isLoaded
      && !childStore.error
      && childStore.hasRemoteChild
      && String(childStore.loadedForUserId) === '8302'
      && Number.isInteger(childId)
      && childId > 0
    ),
    recordStore,
    userStore: {
      isAuthReady: true,
      isLoggedIn: true,
      isRestoring: false,
      userInfo: { id: 8302 },
    },
  }
}

describe('P8.3B Records child-context contract', () => {
  beforeEach(() => {
    resetUniRuntime()
    setActivePinia(createPinia())
  })

  test('does not request Records while child loading is still pending', async () => {
    let releaseChildren
    const childStore = {
      currentChild: { id: 203, name: '小宇' },
      activeChild: { id: 203, name: '小宇' },
      fetchChildren: vi.fn(() => new Promise((resolve) => { releaseChildren = resolve })),
      hasRemoteChild: true,
      isLoaded: true,
      loadedForUserId: 8302,
    }
    const recordStore = { loadJourneyRecords: vi.fn() }

    const loading = pageMethod('loadRecords').call(pageContext({ childStore, recordStore }))
    await flushRuntimePromises()

    expect(recordStore.loadJourneyRecords).not.toHaveBeenCalled()
    releaseChildren()
    await loading
  })

  test('keeps a child request failure visible and never falls back to unscoped Records', async () => {
    const childStore = {
      currentChild: { name: '旧孩子' },
      activeChild: null,
      error: { code: 'NETWORK_ERROR' },
      fetchChildren: vi.fn().mockRejectedValue({ code: 'NETWORK_ERROR' }),
      hasRemoteChild: false,
      isLoaded: false,
      loadedForUserId: 8302,
    }
    const recordStore = { loadJourneyRecords: vi.fn() }

    await pageMethod('loadRecords').call(pageContext({ childStore, recordStore }))

    expect(recordStore.loadJourneyRecords).not.toHaveBeenCalled()
  })

  test('does not request all Records after a successful empty child response', async () => {
    const childStore = {
      currentChild: { name: '小小探索家' },
      activeChild: null,
      error: null,
      fetchChildren: vi.fn().mockResolvedValue({ children: [], currentChild: null }),
      hasRemoteChild: false,
      isLoaded: true,
      loadedForUserId: 8302,
    }
    const recordStore = { loadJourneyRecords: vi.fn() }

    await pageMethod('loadRecords').call(pageContext({ childStore, recordStore }))

    expect(recordStore.loadJourneyRecords).not.toHaveBeenCalled()
  })

  test('loads only the active child Records after a successful child response', async () => {
    const childStore = {
      currentChild: { id: 203, name: '小宇' },
      activeChild: { id: 203, name: '小宇' },
      error: null,
      fetchChildren: vi.fn().mockResolvedValue({}),
      hasRemoteChild: true,
      isLoaded: true,
      loadedForUserId: 8302,
    }
    const recordStore = { loadJourneyRecords: vi.fn().mockResolvedValue([]) }

    await pageMethod('loadRecords').call(pageContext({ childStore, recordStore }))

    expect(recordStore.loadJourneyRecords).toHaveBeenCalledWith({ childId: 203, limit: 20, offset: 0 })
  })

  test('retries through child-context loading instead of Record Store retry alone', async () => {
    const context = {
      handleAuthExpired: vi.fn(),
      loadRecords: vi.fn(),
      recordStore: { retryJourneyRecords: vi.fn().mockResolvedValue([]) },
    }

    await pageMethod('retryRecords').call(context)

    expect(context.loadRecords).toHaveBeenCalledOnce()
  })

  test('renders children loading, children failure, and no-child states before Records states', () => {
    const childLoading = recordPageSource.indexOf('v-if="isChildLoading"')
    const childError = recordPageSource.indexOf('v-else-if="showChildError"')
    const noChild = recordPageSource.indexOf('v-else-if="showNoChild"')
    const recordLoading = recordPageSource.indexOf('v-else-if="isInitialLoading"')

    expect(childLoading).toBeGreaterThanOrEqual(0)
    expect(childError).toBeGreaterThan(childLoading)
    expect(noChild).toBeGreaterThan(childError)
    expect(recordLoading).toBeGreaterThan(noChild)
    expect(recordPageSource).toContain('孩子资料加载失败')
    expect(recordPageSource).toContain('还没有选择孩子')
  })

  test('keeps the Records heading product-focused while child context stays in the request boundary', () => {
    expect(recordPageSource).toContain('探索记录')
    expect(recordPageSource).toContain('记录孩子的每一次探索与成长')
    expect(recordPageSource).toContain('childId: this.childStore.activeChild.id')
  })

  test('keeps the successful-empty Records state and offers a go-explore action', () => {
    expect(recordPageSource).toContain('v-else-if="isEmpty"')
    expect(recordPageSource).toContain('type="empty"')
    expect(recordPageSource).toContain('去探索')
    expect(recordPageSource).toContain('@action="goExplore"')
  })

  test('routes the empty-state action to the Explore workbench with reLaunch', () => {
    const goExplore = recordPageSource.match(/goExplore\(\) \{[\s\S]*?\n    \},/)?.[0] || ''

    expect(goExplore).toContain('uni.reLaunch')
    expect(goExplore).toContain("url: '/pages/explore/index'")
  })

  test('keeps a real record date in the information body instead of fabricating a photo caption', () => {
    expect(recordPageSource).toContain('class="record-card__date"')
    expect(recordPageSource).toContain('{{ record.recordDateLabel }}')
    expect(recordPageSource).toContain('formatRecordDate')
    expect(recordPageSource).not.toContain('recordWatercolorFallback')
  })

  test('uses a real Record timestamp when a finalized timestamp is unavailable', () => {
    expect(recordPageSource).toContain('record?.finalizedAt || record?.updatedAt || record?.createdAt')
  })

  test('preserves finalizedAt as a finalized-time label when it is available', () => {
    expect(recordStoreSource).toContain("`封存于 ${displayFinalizedAt}`")
  })

  test('keeps Record detail navigation on the existing explicit planId route', () => {
    expect(recordPageSource).toContain('openRecordDetail(record)')
    expect(recordPageSource).toContain('url: `/pages/record-detail/index?planId=${planId}`')
  })

  test('retains Record Store loading, error, and successful-list state protection', () => {
    expect(recordStoreSource).toContain('this.loading = true')
    expect(recordStoreSource).toContain('this.error = error')
    expect(recordStoreSource).toContain('this.hasLoaded = true')
    expect(recordStoreSource).toContain('this.records = records')
  })
})
