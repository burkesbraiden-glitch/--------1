import { beforeEach, describe, expect, test } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import {
  createDeferred,
  flushRuntimePromises,
  resetUniRuntime,
  setRequestHandler,
} from './setup/uniRuntime.js'
import { useGuideStore } from '../../src/stores/guide.js'
import { useUserStore } from '../../src/stores/user.js'
import { endUserSession } from '../../src/utils/sessionBoundary.js'

const user = { id: 8305, nickname: 'P8.3E User' }
const planA = { id: 501, childId: 101 }
const planB = { id: 502, childId: 102 }

function login() {
  useUserStore().loginSuccess('p8-3e-token', user)
}

function respond(options, data, statusCode = 200) {
  options.success({ statusCode, data: { success: true, data } })
}

function respondGuideNotFound(options) {
  options.success({
    statusCode: 404,
    data: { success: false, error: { code: 'GUIDE_NOT_FOUND', message: 'missing guide' } },
  })
}

function guideFor(planId, version) {
  return {
    guide: {
      id: Number(planId) * 10 + Number(version),
      planId,
      destination: `目的地 ${version}`,
      childIntro: [`讲解 ${version}`],
      questions: [`问题 ${version}`],
      focusItems: [`重点 ${version}`],
      guideVersion: version,
      audioStatus: 'ready',
      audioUrl: `https://audio.example/${planId}-${version}.mp3`,
      audioDurationSec: Number(version) * 10,
    },
  }
}

function settleDeferredGuide(options, deferred) {
  deferred.promise.then(
    (data) => respond(options, data),
    () => options.fail({ errMsg: 'request:fail delayed guide error' }),
  )
}

beforeEach(() => {
  resetUniRuntime()
  setActivePinia(createPinia())
  login()
})

describe('P8.3E Guide same-session stale-response isolation', () => {
  test('1. a delayed Plan A success cannot overwrite the later Plan B success', async () => {
    const responseA = createDeferred()
    const responseB = createDeferred()
    setRequestHandler((options) => {
      if (options.url.endsWith(`/plans/${planA.id}/guide`)) return settleDeferredGuide(options, responseA)
      if (options.url.endsWith(`/plans/${planB.id}/guide`)) return settleDeferredGuide(options, responseB)
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    const guideStore = useGuideStore()
    const pendingA = guideStore.ensureGuide(planA.id)
    await flushRuntimePromises()
    const pendingB = guideStore.ensureGuide(planB.id)
    await flushRuntimePromises()

    responseB.resolve(guideFor(planB.id, 2))
    await pendingB
    responseA.resolve(guideFor(planA.id, 1))
    await pendingA

    expect(guideStore.currentGuide).toMatchObject(guideFor(planB.id, 2).guide)
    expect(guideStore.loadedForPlanId).toBe(planB.id)
    expect(guideStore.error).toBeNull()
  })

  test('2. a Plan A success cannot become visible while Plan B is still loading', async () => {
    const responseA = createDeferred()
    const responseB = createDeferred()
    setRequestHandler((options) => {
      if (options.url.endsWith(`/plans/${planA.id}/guide`)) return settleDeferredGuide(options, responseA)
      if (options.url.endsWith(`/plans/${planB.id}/guide`)) return settleDeferredGuide(options, responseB)
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    const guideStore = useGuideStore()
    const pendingA = guideStore.ensureGuide(planA.id)
    await flushRuntimePromises()
    const pendingB = guideStore.ensureGuide(planB.id)
    await flushRuntimePromises()

    responseA.resolve(guideFor(planA.id, 1))
    await pendingA

    expect(guideStore.currentGuide).toBeNull()
    expect(guideStore.loadedForPlanId).toBeNull()
    expect(guideStore.isLoading).toBe(true)

    responseB.resolve(guideFor(planB.id, 2))
    await pendingB
    expect(guideStore.currentGuide?.planId).toBe(planB.id)
  })

  test('3. an older same-Plan B refresh cannot overwrite newer text or audio metadata', async () => {
    const responseB1 = createDeferred()
    const responseB2 = createDeferred()
    let requestCount = 0
    setRequestHandler((options) => {
      if (!options.url.endsWith(`/plans/${planB.id}/guide`)) {
        throw new Error(`Unexpected request: ${options.method} ${options.url}`)
      }
      requestCount += 1
      return settleDeferredGuide(options, requestCount === 1 ? responseB1 : responseB2)
    })

    const guideStore = useGuideStore()
    const pendingB1 = guideStore.fetchGuide(planB.id)
    await flushRuntimePromises()
    const pendingB2 = guideStore.fetchGuide(planB.id)
    await flushRuntimePromises()

    responseB2.resolve(guideFor(planB.id, 2))
    await pendingB2
    responseB1.resolve(guideFor(planB.id, 1))
    await pendingB1

    expect(guideStore.currentGuide).toMatchObject(guideFor(planB.id, 2).guide)
    expect(guideStore.currentGuide.childIntro).toEqual(['讲解 2'])
    expect(guideStore.currentGuide.audioUrl).toBe('https://audio.example/502-2.mp3')
    expect(guideStore.currentGuide.audioDurationSec).toBe(20)
  })

  test('4. a stale Plan A error cannot clear Plan B or replace its error state', async () => {
    const responseA = createDeferred()
    const responseB = createDeferred()
    setRequestHandler((options) => {
      if (options.url.endsWith(`/plans/${planA.id}/guide`)) return settleDeferredGuide(options, responseA)
      if (options.url.endsWith(`/plans/${planB.id}/guide`)) return settleDeferredGuide(options, responseB)
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    const guideStore = useGuideStore()
    const pendingA = guideStore.fetchGuide(planA.id)
    await flushRuntimePromises()
    const pendingB = guideStore.fetchGuide(planB.id)
    await flushRuntimePromises()

    responseB.resolve(guideFor(planB.id, 2))
    await pendingB
    responseA.reject(new Error('late A error'))
    await expect(pendingA).resolves.toBeNull()

    expect(guideStore.currentGuide).toMatchObject(guideFor(planB.id, 2).guide)
    expect(guideStore.error).toBeNull()
    expect(guideStore.isLoading).toBe(false)
  })

  test('5. a stale Plan A finally cannot end the pending Plan B loading state', async () => {
    const responseA = createDeferred()
    const responseB = createDeferred()
    setRequestHandler((options) => {
      if (options.url.endsWith(`/plans/${planA.id}/guide`)) return settleDeferredGuide(options, responseA)
      if (options.url.endsWith(`/plans/${planB.id}/guide`)) return settleDeferredGuide(options, responseB)
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    const guideStore = useGuideStore()
    const pendingA = guideStore.fetchGuide(planA.id)
    await flushRuntimePromises()
    const pendingB = guideStore.fetchGuide(planB.id)
    await flushRuntimePromises()

    responseA.resolve(guideFor(planA.id, 1))
    await pendingA

    expect(guideStore.isLoading).toBe(true)
    expect(guideStore.currentGuide).toBeNull()

    responseB.resolve(guideFor(planB.id, 2))
    await pendingB
    expect(guideStore.isLoading).toBe(false)
  })

  test('6. a stale guide-generation success cannot overwrite Plan B', async () => {
    const generatedA = createDeferred()
    const responseB = createDeferred()
    setRequestHandler((options) => {
      if (options.url.endsWith(`/plans/${planA.id}/guide`) && options.method === 'GET') {
        return respondGuideNotFound(options)
      }
      if (options.url.endsWith(`/plans/${planA.id}/guide/generate`) && options.method === 'POST') {
        return settleDeferredGuide(options, generatedA)
      }
      if (options.url.endsWith(`/plans/${planB.id}/guide`) && options.method === 'GET') {
        return settleDeferredGuide(options, responseB)
      }
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    const guideStore = useGuideStore()
    const pendingA = guideStore.ensureGuide(planA.id)
    await flushRuntimePromises()
    const pendingB = guideStore.ensureGuide(planB.id)
    await flushRuntimePromises()

    responseB.resolve(guideFor(planB.id, 2))
    await pendingB
    generatedA.resolve(guideFor(planA.id, 1))
    await pendingA

    expect(guideStore.currentGuide).toMatchObject(guideFor(planB.id, 2).guide)
    expect(guideStore.loadedForPlanId).toBe(planB.id)
  })

  test('7. a pending guide response cannot restore state after logout', async () => {
    const responseA = createDeferred()
    setRequestHandler((options) => {
      if (options.url.endsWith(`/plans/${planA.id}/guide`)) return settleDeferredGuide(options, responseA)
      if (options.url.endsWith('/auth/logout')) return respond(options, {})
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    const guideStore = useGuideStore()
    const pendingA = guideStore.ensureGuide(planA.id)
    await flushRuntimePromises()
    await endUserSession()
    responseA.resolve(guideFor(planA.id, 1))
    await pendingA

    expect(guideStore.currentGuide).toBeNull()
    expect(guideStore.loadedForPlanId).toBeNull()
    expect(guideStore.isLoading).toBe(false)
  })
})
