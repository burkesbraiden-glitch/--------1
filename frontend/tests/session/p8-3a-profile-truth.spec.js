import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { beforeEach, describe, expect, test } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { getRequestCalls, resetUniRuntime, setRequestHandler } from './setup/uniRuntime.js'
import { useChildStore } from '../../src/stores/child.js'
import { useUserStore } from '../../src/stores/user.js'

const root = resolve(process.cwd(), '..')
const profileSource = readFileSync(resolve(root, 'frontend/src/pages/profile/index.vue'), 'utf8')
const userId = 8301

function login() {
  const user = useUserStore()
  user.loginSuccess('profile-truth-token', { id: userId, nickname: 'Profile Parent' })
  return user
}

function respond(options, data, statusCode = 200) {
  options.success({ statusCode, data: { success: true, data } })
}

function childRequestCount() {
  return getRequestCalls().filter((request) => request.url.endsWith('/children')).length
}

describe('P8.3A Profile data-truth contract', () => {
  beforeEach(() => {
    resetUniRuntime()
    setActivePinia(createPinia())
  })

  test('does not expose mock or unavailable profile capabilities', () => {
    expect(profileSource).not.toContain('mockFavorites')
    expect(profileSource).not.toContain('我的收藏')
    expect(profileSource).not.toContain('消息通知')
    expect(profileSource).not.toContain('帮助与反馈')
    expect(profileSource).not.toContain("key: 'settings'")
    expect(profileSource).not.toContain('当前阶段使用 Mock')
  })

  test('replaces the stale count with a real JourneyRecord navigation entry', () => {
    expect(profileSource).not.toContain('learningRecordCount')
    expect(profileSource).not.toContain('learningRecords')
    expect(profileSource).not.toContain('loadJourneyRecords(')
    expect(profileSource).toContain('成长记录')
    expect(profileSource).toContain('查看探索中的任务、照片与笔记')
    expect(profileSource).toContain('openJourneyRecords()')
    expect(profileSource).toContain("url: '/pages/record/index'")
    expect(profileSource).toContain('uni.navigateTo({')
  })

  test('orders child loading, request failure, and successful-empty states distinctly', () => {
    const loadingIndex = profileSource.indexOf('v-if="child.isLoading"')
    const errorIndex = profileSource.indexOf('v-else-if="child.error"')
    const emptyIndex = profileSource.indexOf('v-else-if="child.isLoaded && child.children.length === 0"')

    expect(loadingIndex).toBeGreaterThanOrEqual(0)
    expect(errorIndex).toBeGreaterThan(loadingIndex)
    expect(emptyIndex).toBeGreaterThan(errorIndex)
    expect(profileSource).toContain('孩子资料加载失败，请重试')
    expect(profileSource).toContain('尚未添加孩子')
    expect(profileSource).toContain('@click="loadChildren"')
    expect(profileSource).toContain('child.currentChild.name')
  })

  test('keeps the real child editor and session logout boundaries', () => {
    expect(profileSource).toContain('openChildForm()')
    expect(profileSource).toContain('this.child.createChild(payload)')
    expect(profileSource).toContain('this.child.updateChild(this.child.currentChild.id, payload)')
    expect(profileSource).toContain("key: 'logout'")
    expect(profileSource).toContain('endUserSession()')
  })

  test('keeps a successful empty child response distinct from a failed request', async () => {
    const user = login()
    setRequestHandler((options) => {
      if (!options.url.endsWith('/children')) throw new Error(`Unexpected request: ${options.url}`)
      respond(options, { children: [], currentChild: null })
    })

    const child = useChildStore()
    await child.fetchChildren(user.userInfo.id)

    expect(child.isLoaded).toBe(true)
    expect(child.error).toBeNull()
    expect(child.children).toEqual([])
    expect(child.hasRemoteChild).toBe(false)
  })

  test('keeps a failed child request in the error state rather than treating it as an empty result', async () => {
    const user = login()
    setRequestHandler((options) => {
      if (!options.url.endsWith('/children')) throw new Error(`Unexpected request: ${options.url}`)
      options.fail({ errMsg: 'network unavailable' })
    })

    const child = useChildStore()
    await expect(child.fetchChildren(user.userInfo.id)).rejects.toMatchObject({ code: 'NETWORK_ERROR' })

    expect(child.isLoaded).toBe(false)
    expect(child.error).toMatchObject({ code: 'NETWORK_ERROR' })
    expect(child.hasRemoteChild).toBe(false)
  })

  test('allows the child error state to retry the same real children request', async () => {
    const user = login()
    let attempts = 0
    setRequestHandler((options) => {
      if (!options.url.endsWith('/children')) throw new Error(`Unexpected request: ${options.url}`)
      attempts += 1
      if (attempts === 1) {
        options.fail({ errMsg: 'temporary failure' })
        return
      }
      respond(options, {
        children: [{ id: 203, name: '小小探索家', age: 8, city: '北京', interests: ['古建筑'], isDefault: true }],
        currentChild: { id: 203, name: '小小探索家', age: 8, city: '北京', interests: ['古建筑'], isDefault: true },
      })
    })

    const child = useChildStore()
    await expect(child.fetchChildren(user.userInfo.id)).rejects.toMatchObject({ code: 'NETWORK_ERROR' })
    await child.fetchChildren(user.userInfo.id)

    expect(childRequestCount()).toBe(2)
    expect(child.error).toBeNull()
    expect(child.hasRemoteChild).toBe(true)
    expect(child.currentChild).toMatchObject({ id: 203, name: '小小探索家', age: 8 })
  })

  test('keeps the existing child create and edit API flow available', async () => {
    login()
    setRequestHandler((options) => {
      if (options.method === 'POST' && options.url.endsWith('/children')) {
        respond(options, {
          child: { id: 204, name: '小小探索家', age: 7, city: '北京', interests: ['历史故事'], isDefault: true },
        })
        return
      }
      if (options.method === 'PATCH' && options.url.endsWith('/children/204')) {
        respond(options, {
          child: { id: 204, name: '小小探索家', age: 8, city: '西安', interests: ['古建筑'], isDefault: true },
        })
        return
      }
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    const child = useChildStore()
    await child.createChild({ name: '小小探索家', age: 7, city: '北京', interests: ['历史故事'] })
    await child.updateChild(204, { name: '小小探索家', age: 8, city: '西安', interests: ['古建筑'] })

    expect(getRequestCalls().map((request) => request.method)).toEqual(['POST', 'PATCH'])
    expect(child.currentChild).toMatchObject({ id: 204, age: 8, city: '西安', interests: ['古建筑'] })
  })
})
