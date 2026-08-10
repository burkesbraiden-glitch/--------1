import { spawnSync } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
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
assert(!guidePage.includes('Mock 音频'), 'Guide page must not pretend mock audio is real playback')
assert(!guidePage.includes('/plans/undefined/guide'), 'Guide page must not request guide without currentPlan')

const profilePage = read('pages/profile/index.vue')
const sessionBoundary = read('utils/sessionBoundary.js')
assert(/key\s*===\s*['"]logout['"][\s\S]*?endUserSession\s*\(/.test(profilePage), 'profile logout must delegate to endUserSession')
assert(/guideStore\.resetSessionState\s*\(/.test(sessionBoundary), 'shared session boundary must clear guideStore')

const vitest = join(root, 'node_modules', 'vitest', 'vitest.mjs')
const config = join(root, 'vitest.session.config.mjs')
const testFile = join(root, 'tests', 'session', 'stale-response.spec.js')
const result = spawnSync(process.execPath, [vitest, 'run', testFile, '--config', config], {
  cwd: root,
  stdio: 'inherit',
})

if (result.error) {
  throw result.error
}

if (result.status !== 0) {
  throw new Error(`guide behavior Vitest check failed with exit code ${result.status}`)
}

console.log('phase3c2 guide integration checks passed')
