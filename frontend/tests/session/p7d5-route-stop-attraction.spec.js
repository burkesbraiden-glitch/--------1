import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { beforeEach, describe, expect, test } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { getRequestCalls, resetUniRuntime, setRequestHandler } from './setup/uniRuntime.js'
import { useUserStore } from '../../src/stores/user.js'

const workspaceRoot = resolve(process.cwd(), '..')
const attractionsApiPath = resolve(workspaceRoot, 'frontend', 'src', 'api', 'attractions.js')
const routeDetailPath = resolve(workspaceRoot, 'frontend', 'src', 'pages', 'route-detail', 'index.vue')

function respond(options, data) {
  options.success({ statusCode: 200, data: { success: true, data } })
}

function login() {
  useUserStore().loginSuccess('attraction-token', { id: 505, nickname: '景点搜索用户' })
}

async function getAttractionsApi() {
  return import('../../src/api/attractions.js')
}

describe('P7D-5 Attraction search and RouteStop contracts', () => {
  beforeEach(() => {
    resetUniRuntime()
    setActivePinia(createPinia())
  })

  test('requires the Attraction API client before runtime requests can run', () => {
    expect(existsSync(attractionsApiPath)).toBe(true)
  })

  test('sends an authenticated empty Attraction query without a trailing question mark', async () => {
    if (!existsSync(attractionsApiPath)) return
    const { getAttractions } = await getAttractionsApi()
    login()
    const result = { items: [], total: 0, limit: 20, offset: 0 }
    setRequestHandler((options) => respond(options, result))

    await expect(getAttractions()).resolves.toEqual(result)
    expect(getRequestCalls()).toEqual([expect.objectContaining({
      method: 'GET',
      url: 'http://session.test/api/v1/attractions',
      header: expect.objectContaining({ Authorization: 'Bearer attraction-token' }),
    })])
  })

  test('encodes only supported Attraction query fields and returns the server list envelope', async () => {
    if (!existsSync(attractionsApiPath)) return
    const { getAttractions } = await getAttractionsApi()
    login()
    const result = { items: [{ id: 7, name: '故宫' }], total: 1, limit: 100, offset: 0 }
    setRequestHandler((options) => respond(options, result))

    await expect(getAttractions({ city: '北京 西城', keyword: '宫殿 & 亲子', limit: 100, offset: 0, tag: '历史' })).resolves.toEqual(result)
    expect(getRequestCalls()[0]).toMatchObject({
      method: 'GET',
      url: `http://session.test/api/v1/attractions?city=${encodeURIComponent('北京 西城')}&keyword=${encodeURIComponent('宫殿 & 亲子')}&limit=100&offset=0`,
    })
  })

  test('keeps attraction search and Stop CRUD in Route Detail without extra stores or N+1 detail fetches', () => {
    const source = readFileSync(routeDetailPath, 'utf8')
    expect(source).toContain("from '../../api/attractions'")
    expect(source).toContain('showAttractionSheet')
    expect(source).toContain('attractionDayId = day.id')
    expect(source).toContain('city: this.currentRoute.city')
    expect(source).toContain('attractionKeyword')
    expect(source).toContain('isLoadingAttractions')
    expect(source).toContain('attractionError')
    expect(source).toContain('没有找到符合条件的景点')
    expect(source).toContain('attraction.name')
    expect(source).toContain('attraction.district')
    expect(source).toContain('attraction.summary')
    expect(source).toContain('attraction.recommendedDurationMinutes')
    expect(source).toContain('routeStore.createStop(this.routeId, this.attractionDayId, { attractionId: attraction.id })')
    expect(source).toContain('v-for="stop in day.stops"')
    expect(source).toContain('stop.attraction.name')
    expect(source).toContain('showStopNoteSheet')
    expect(source).toContain('routeStore.updateStop(this.routeId, this.editingStopDayId, this.editingStopId, { note })')
    expect(source).toContain('routeStore.deleteStop(this.routeId, day.id, stop.id)')
    expect(source).toContain('确认移除这个景点？')
    expect(source).not.toContain('useAttractionStore')
    expect(source).not.toContain('day.stops.splice')
    expect(source).not.toContain('stop.sortOrder = index + 1')
    expect(source).not.toContain('getAttractionGuide')
    expect(source).not.toContain('usePlanStore')
    expect(source).not.toContain('useTaskStore')
    expect(source).not.toContain('useGuideStore')
    expect(source).not.toContain('useRecordStore')
  })
})
