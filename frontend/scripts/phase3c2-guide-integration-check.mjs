import { existsSync, readFileSync } from 'node:fs'
import { join } from 'node:path'
import { createPinia, setActivePinia } from 'pinia'

process.env.NODE_NO_WARNINGS = '1'

const root = process.cwd()
const src = join(root, 'src')

function read(relativePath) {
  return readFileSync(join(src, relativePath), 'utf8')
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message)
  }
}

const guidesApiPath = join(src, 'api/guides.js')
assert(existsSync(guidesApiPath), 'Missing src/api/guides.js')

const guidesApi = read('api/guides.js')
assert(guidesApi.includes("from '../utils/request.js'"), 'guides API must reuse unified request')
assert(guidesApi.includes('function getGuide'), 'guides API missing getGuide')
assert(guidesApi.includes('function generateGuide'), 'guides API missing generateGuide')
assert(guidesApi.includes('path: `/plans/${planId}/guide`'), 'getGuide path must be /plans/{id}/guide')
assert(guidesApi.includes('path: `/plans/${planId}/guide/generate`'), 'generateGuide path must be /plans/{id}/guide/generate')
assert((guidesApi.match(/auth:\s*true/g) || []).length >= 2, 'guide API calls must use auth=true')
assert(!guidesApi.includes('uni.request'), 'guides API must not call uni.request directly')

const guideStorePath = join(src, 'stores/guide.js')
assert(existsSync(guideStorePath), 'Missing src/stores/guide.js')
const guideStoreSource = read('stores/guide.js')
assert(guideStoreSource.includes("from '../api/guides.js'"), 'guideStore must import guides API')
assert(guideStoreSource.includes('currentGuide'), 'guideStore must keep currentGuide')
assert(guideStoreSource.includes('isLoading'), 'guideStore must keep isLoading')
assert(guideStoreSource.includes('isGenerating'), 'guideStore must keep isGenerating')
assert(guideStoreSource.includes('loadedForPlanId'), 'guideStore must keep loadedForPlanId')
assert(guideStoreSource.includes('ensurePromise'), 'guideStore must dedupe ensureGuide calls')
assert(guideStoreSource.includes('fetchGuide'), 'guideStore must expose fetchGuide')
assert(guideStoreSource.includes('generateGuide'), 'guideStore must expose generateGuide')
assert(guideStoreSource.includes('ensureGuide'), 'guideStore must expose ensureGuide')
assert(guideStoreSource.includes("error?.code === 'GUIDE_NOT_FOUND'"), 'only GUIDE_NOT_FOUND may trigger generate')
assert(!guideStoreSource.includes('setStorageSync') && !guideStoreSource.includes('getStorageSync'), 'guideStore must not persist guide or audio state')

const guidePage = read('pages/guide/index.vue')
assert(guidePage.includes('useGuideStore'), 'Guide page must use guideStore')
assert(guidePage.includes('ensureCurrentPlanReady'), 'Guide page must restore currentPlan first')
assert(guidePage.includes('ensureGuide'), 'Guide page must ensure real guide')
assert(guidePage.includes('currentGuide.childIntro'), 'Guide page must display real childIntro')
assert(guidePage.includes('currentGuide.questions'), 'Guide page must display real questions')
assert(guidePage.includes('currentGuide.focusItems'), 'Guide page must display real focusItems')
assert(guidePage.includes('currentGuide.destination'), 'Guide page must display real guide destination')
assert(!guidePage.includes('mockPlans[0]'), 'Guide page must not use mockPlans fallback')
assert(!guidePage.includes("questions: ['"), 'Guide page must not keep local questions as business data')
assert(!guidePage.includes("focusItems: ['"), 'Guide page must not keep local focusItems as business data')
assert(!guidePage.includes('Mock 闊抽'), 'Guide page must not pretend mock audio is real playback')
assert(!guidePage.includes('/plans/undefined/guide'), 'Guide page must not request guide without currentPlan')

const profilePage = read('pages/profile/index.vue')
assert(profilePage.includes('useGuideStore'), 'profile logout must import guideStore')
assert(profilePage.includes('guide.resetSessionState'), 'logout must clear guideStore')

for (const forbidden of ['api/records.js']) {
  assert(!existsSync(join(src, forbidden)), `phase 3C-2 must not add ${forbidden}`)
}

const storage = new Map()
const requests = []
globalThis.uni = {
  getStorageSync(key) {
    return storage.get(key) || null
  },
  setStorageSync(key, value) {
    storage.set(key, value)
  },
  removeStorageSync(key) {
    storage.delete(key)
  },
  request(options) {
    const url = options.url || ''
    requests.push({ url, method: options.method })

    if (url.endsWith('/plans/101/guide') && options.method === 'GET') {
      options.success({
        statusCode: 404,
        data: { success: false, error: { code: 'GUIDE_NOT_FOUND', message: 'Guide not found' } },
      })
      return
    }

    if (url.endsWith('/plans/101/guide/generate') && options.method === 'POST') {
      options.success({
        statusCode: 201,
        data: {
          success: true,
          data: {
            guide: {
              id: 501,
              planId: 101,
              destination: 'Plan A Destination',
              childIntro: ['A intro'],
              questions: ['A question'],
              focusItems: ['A focus'],
              audioUrl: null,
              createdAt: '2026-01-01T00:00:00Z',
              updatedAt: '2026-01-01T00:00:00Z',
            },
          },
        },
      })
      return
    }

    if (url.endsWith('/plans/202/guide') && options.method === 'GET') {
      options.success({
        statusCode: 200,
        data: {
          success: true,
          data: {
            guide: {
              id: 602,
              planId: 202,
              destination: 'Plan B Destination',
              childIntro: ['B intro'],
              questions: ['B question'],
              focusItems: ['B focus'],
              audioUrl: null,
              createdAt: '2026-01-02T00:00:00Z',
              updatedAt: '2026-01-02T00:00:00Z',
            },
          },
        },
      })
      return
    }

    if (url.endsWith('/plans/303/guide') && options.method === 'GET') {
      options.fail({ errMsg: 'network down' })
      return
    }

    if (url.includes('/plans/undefined/guide')) {
      throw new Error('must not request undefined guide')
    }

    options.fail({ errMsg: `unexpected request: ${url}` })
  },
}

setActivePinia(createPinia())
const { useGuideStore } = await import('../src/stores/guide.js')
const guideStore = useGuideStore()

await guideStore.ensureGuide(101)
assert(guideStore.currentGuide.id === 501, 'GUIDE_NOT_FOUND must generate guide')
assert(requests.filter((item) => item.url.endsWith('/plans/101/guide/generate')).length === 1, 'missing guide must generate once')

const dedupe = await Promise.all([guideStore.ensureGuide(202), guideStore.ensureGuide(202)])
assert(dedupe[0].id === 602 && dedupe[1].id === 602, 'same plan ensure calls must resolve same guide')
assert(requests.filter((item) => item.url.endsWith('/plans/202/guide')).length === 1, 'same plan ensure must dedupe GET')
assert(requests.filter((item) => item.url.endsWith('/plans/202/guide/generate')).length === 0, 'existing guide must not generate')

guideStore.clearGuideForPlanChange(303)
assert(guideStore.currentGuide === null, 'plan change must clear old guide before loading new one')
try {
  await guideStore.ensureGuide(303)
} catch (error) {
  assert(error.code === 'NETWORK_ERROR', 'network failure must stay a network error')
}
assert(requests.filter((item) => item.url.endsWith('/plans/303/guide/generate')).length === 0, 'network failure must not generate')

await guideStore.ensureGuide(null)
assert(!requests.some((item) => item.url.includes('/plans/undefined/guide')), 'empty currentPlan must not request guide')

guideStore.resetSessionState()
assert(guideStore.currentGuide === null && guideStore.loadedForPlanId === null, 'resetSessionState must clear guide session')

console.log('phase3c2 guide integration checks passed')
