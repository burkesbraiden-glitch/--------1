import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { beforeEach, describe, expect, test } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import {
  getRequestCalls,
  resetUniRuntime,
  setRequestHandler,
} from './setup/uniRuntime.js'
import { useUserStore } from '../../src/stores/user.js'

const workspaceRoot = resolve(process.cwd(), '..')
const frontendFile = (...segments) => resolve(workspaceRoot, 'frontend', ...segments)
const attractionApiPath = frontendFile('src', 'api', 'attractions.js')
const detailPagePath = frontendFile('src', 'pages', 'attraction-detail', 'index.vue')
const pagesConfigPath = frontendFile('src', 'pages.json')

const user = { id: 703, nickname: 'Attraction Detail User' }
const attraction = {
  id: 91,
  name: '故宫博物院',
  city: '北京',
  district: '东城区',
  address: '景山前街4号',
  summary: '在宏大的宫殿建筑里观察颜色、屋顶和古代礼仪。',
  tags: ['历史', '古建筑'],
  recommendedDurationMinutes: 180,
  coverImage: '/images/forbidden-city.webp',
}
const guide = {
  id: 910,
  attractionId: attraction.id,
  overview: '从门、殿和屋顶开始阅读这座古代城市。',
  highlights: ['屋顶小兽', '红墙黄瓦'],
  visitTips: ['为观察和休息预留时间'],
  familyTips: ['请孩子挑选一处建筑细节，说出自己的发现'],
}

function login() {
  useUserStore().loginSuccess('p7f3-attraction-token', user)
}

function respond(options, data) {
  options.success({ statusCode: 200, data: { success: true, data } })
}

function respondError(options, statusCode, code, message = '请求失败') {
  options.success({
    statusCode,
    data: { success: false, error: { code, message } },
  })
}

async function getAttractionsApi() {
  return import('../../src/api/attractions.js')
}

function readDetailPageSource() {
  const exists = existsSync(detailPagePath)
  expect(exists).toBe(true)
  return exists ? readFileSync(detailPagePath, 'utf8') : ''
}

async function loadDetailPageOptions() {
  const source = readDetailPageSource()
  if (!source) return null

  const script = source.match(/<script>([\s\S]*?)<\/script>/)?.[1]
  expect(script).toBeTruthy()
  if (!script) return null

  const api = await getAttractionsApi()
  const executable = script
    .replace(/^import[^\n]*\n/gm, '')
    .replace('export default {', 'return {')

  return new Function(
    'AppTabbar',
    'getAttractionDetail',
    'getAttractionGuide',
    'resolveBackendResourceUrl',
    'isAuthenticationError',
    'endUserSession',
    executable,
  )(
    {},
    api.getAttractionDetail,
    api.getAttractionGuide,
    (value) => value,
    () => false,
    async () => {},
  )
}

function createDetailVm(options) {
  const vm = { ...(options.data?.call({}) || {}) }
  Object.assign(vm, options.methods || {})
  return vm
}

async function loadAttractionDetail(options, attractionId) {
  const vm = createDetailVm(options)
  expect(typeof options.onLoad).toBe('function')
  if (typeof options.onLoad !== 'function') return vm
  await options.onLoad.call(vm, { attractionId })
  return vm
}

describe('P7F-3 Attraction API wrappers', () => {
  beforeEach(() => {
    resetUniRuntime()
    setActivePinia(createPinia())
  })

  test('gets one Attraction detail through the authenticated request contract', async () => {
    login()
    const api = await getAttractionsApi()

    expect(typeof api.getAttractionDetail).toBe('function')
    if (typeof api.getAttractionDetail !== 'function') return

    setRequestHandler((options) => respond(options, { attraction }))

    await expect(api.getAttractionDetail(attraction.id)).resolves.toEqual({ attraction })
    expect(getRequestCalls()).toEqual([expect.objectContaining({
      method: 'GET',
      url: 'http://session.test/api/v1/attractions/91',
      header: expect.objectContaining({ Authorization: 'Bearer p7f3-attraction-token' }),
    })])
  })

  test('gets one static AttractionGuide through the authenticated request contract', async () => {
    login()
    const api = await getAttractionsApi()

    expect(typeof api.getAttractionGuide).toBe('function')
    if (typeof api.getAttractionGuide !== 'function') return

    setRequestHandler((options) => respond(options, { guide }))

    await expect(api.getAttractionGuide(attraction.id)).resolves.toEqual({ guide })
    expect(getRequestCalls()).toEqual([expect.objectContaining({
      method: 'GET',
      url: 'http://session.test/api/v1/attractions/91/guide',
      header: expect.objectContaining({ Authorization: 'Bearer p7f3-attraction-token' }),
    })])
  })
})

describe('P7F-3 Attraction Detail runtime', () => {
  beforeEach(() => {
    resetUniRuntime()
    setActivePinia(createPinia())
  })

  test('registers Attraction Detail as a non-tab page', () => {
    const pagesConfig = readFileSync(pagesConfigPath, 'utf8')

    expect(pagesConfig).toContain('pages/attraction-detail/index')
    expect(readDetailPageSource()).toContain('<AppTabbar active="route" />')
  })

  test('loads the explicit Attraction and its static guide into normal state', async () => {
    login()
    setRequestHandler((options) => {
      if (options.url.endsWith('/attractions/91')) return respond(options, { attraction })
      if (options.url.endsWith('/attractions/91/guide')) return respond(options, { guide })
      throw new Error(`Unexpected request: ${options.url}`)
    })

    const options = await loadDetailPageOptions()
    if (!options) return
    const vm = await loadAttractionDetail(options, attraction.id)

    expect(vm.attraction).toEqual(attraction)
    expect(vm.guide).toEqual(guide)
    expect(vm.attractionState).toBe('normal')
    expect(vm.guideState).toBe('normal')
    expect(getRequestCalls().map((call) => call.url)).toEqual([
      'http://session.test/api/v1/attractions/91',
      'http://session.test/api/v1/attractions/91/guide',
    ])
  })

  test('keeps a valid Attraction visible when its static guide is absent', async () => {
    login()
    setRequestHandler((options) => {
      if (options.url.endsWith('/attractions/91')) return respond(options, { attraction })
      if (options.url.endsWith('/attractions/91/guide')) {
        return respondError(options, 404, 'ATTRACTION_GUIDE_NOT_FOUND', 'Attraction guide not found')
      }
      throw new Error(`Unexpected request: ${options.url}`)
    })

    const options = await loadDetailPageOptions()
    if (!options) return
    const vm = await loadAttractionDetail(options, attraction.id)

    expect(vm.attraction).toEqual(attraction)
    expect(vm.attractionState).toBe('normal')
    expect(vm.guide).toBeNull()
    expect(vm.guideState).toBe('no-guide')
  })

  test('marks a missing Attraction unavailable without requesting its guide', async () => {
    login()
    setRequestHandler((options) => respondError(options, 404, 'ATTRACTION_NOT_FOUND', 'Attraction not found'))

    const options = await loadDetailPageOptions()
    if (!options) return
    const vm = await loadAttractionDetail(options, attraction.id)

    expect(vm.attraction).toBeNull()
    expect(vm.attractionState).toBe('unavailable')
    expect(getRequestCalls().map((call) => call.url)).toEqual([
      'http://session.test/api/v1/attractions/91',
    ])
  })

  test.each([undefined, '', 'not-an-id'])('rejects invalid attractionId %j without a request', async (attractionId) => {
    login()
    setRequestHandler(() => {
      throw new Error('Invalid attractionId must not request the backend')
    })

    const options = await loadDetailPageOptions()
    if (!options) return
    const vm = await loadAttractionDetail(options, attractionId)

    expect(vm.attraction).toBeNull()
    expect(vm.attractionState).toBe('unavailable')
    expect(getRequestCalls()).toEqual([])
  })

  test('keeps a detail request failure distinct from not-found and exposes retry', async () => {
    login()
    setRequestHandler((options) => respondError(options, 500, 'DATABASE_ERROR', 'Database error'))

    const options = await loadDetailPageOptions()
    if (!options) return
    const vm = await loadAttractionDetail(options, attraction.id)

    expect(vm.attraction).toBeNull()
    expect(vm.attractionState).toBe('error')
    expect(typeof vm.reloadAttraction).toBe('function')
  })

  test('keeps a loaded Attraction when its guide request has a non-404 error', async () => {
    login()
    setRequestHandler((options) => {
      if (options.url.endsWith('/attractions/91')) return respond(options, { attraction })
      if (options.url.endsWith('/attractions/91/guide')) return respondError(options, 503, 'SERVICE_UNAVAILABLE')
      throw new Error(`Unexpected request: ${options.url}`)
    })

    const options = await loadDetailPageOptions()
    if (!options) return
    const vm = await loadAttractionDetail(options, attraction.id)

    expect(vm.attraction).toEqual(attraction)
    expect(vm.attractionState).toBe('normal')
    expect(vm.guide).toBeNull()
    expect(vm.guideState).toBe('error')
  })

  test('uses only Attraction reads and leaves every Plan, Task, GuideCard, Record, and Route mutation boundary untouched', () => {
    const source = readDetailPageSource()

    for (const forbidden of [
      'usePlanStore', 'useTaskStore', 'useGuideStore', 'useRecordStore', 'useRouteStore',
      'ensureGuide', 'generateGuide', 'ensureTasks', 'generateTasks',
      'createJourneyRecord', 'ensureJourneyRecord', 'createExplorationPlan',
      'createStop', 'updateStop',
    ]) {
      expect(source).not.toContain(forbidden)
    }
    expect(source).toContain('getAttractionDetail')
    expect(source).toContain('getAttractionGuide')
    expect(source).toContain('resolveBackendResourceUrl')
    expect(source).not.toContain('downloadAuthenticatedFile')
    expect(source).not.toContain('uploadAuthenticatedFile')
  })
})
