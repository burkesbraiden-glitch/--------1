import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { proxyRefs, shallowRef } from 'vue'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { useGuideStore } from '../../src/stores/guide.js'
import { usePlanStore } from '../../src/stores/plan.js'
import { useUserStore } from '../../src/stores/user.js'
import { endUserSession, getCurrentSession, isCurrentSession } from '../../src/utils/sessionBoundary.js'
import {
  createDeferred,
  flushRuntimePromises,
  getReLaunchCalls,
  getRequestCalls,
  resetUniRuntime,
  setRequestHandler,
} from './setup/uniRuntime.js'

const workspaceRoot = resolve(process.cwd(), '..')
const sheetPath = resolve(workspaceRoot, 'frontend', 'src', 'components', 'AudioGuideSheet.vue')
const userA = { id: 8401, nickname: 'P8.4A User A' }
const userB = { id: 8402, nickname: 'P8.4A User B' }
const planA = { id: 841, destination: 'Plan A' }
const planB = { id: 842, destination: 'Plan B' }

function login(user = userA) {
  useUserStore().loginSuccess(`p8-4a-token-${user.id}`, user)
}

function respond(options, data, statusCode = 200) {
  options.success({ statusCode, data: { success: true, data } })
}

function respondError(options, statusCode, code = 'HTTP_ERROR', message = 'request failed') {
  options.success({
    statusCode,
    data: { success: false, error: { code, message } },
  })
}

function guideFor(planId, overrides = {}) {
  return {
    id: `guide-${planId}`,
    planId,
    destination: `Destination ${planId}`,
    childIntro: [`Intro ${planId}`],
    questions: [`Question ${planId}`],
    focusItems: [`Focus ${planId}`],
    audioStatus: 'ready',
    audioUrl: `https://signed.example/${planId}.mp3`,
    audioDurationSec: 30,
    ...overrides,
  }
}

function logoutSuccess(options) {
  if (options.url.endsWith('/auth/logout')) {
    respond(options, {})
    return true
  }
  return false
}

function guideRequests() {
  return getRequestCalls().filter((call) => call.url.includes('/guide'))
}

function logoutRequests() {
  return getRequestCalls().filter((call) => call.url.endsWith('/auth/logout'))
}

function loadAudioGuideSheetOptions() {
  const source = readFileSync(sheetPath, 'utf8')
  const script = source.match(/<script>\s*([\s\S]*?)<\/script>/)?.[1]
  expect(script).toBeTruthy()
  const executable = script
    .replace(/^import .+$/gm, '')
    .replace(/export default\s+/, 'return ')

  return new Function(
    'useGuideStore',
    'usePlanStore',
    'shallowRef',
    'getCurrentSession',
    'isCurrentSession',
    executable,
  )(useGuideStore, usePlanStore, shallowRef, getCurrentSession, isCurrentSession)
}

function createAudioGuideSheetVm({ planId = planA.id, open = true } = {}) {
  const options = loadAudioGuideSheetOptions()
  const vm = proxyRefs({
    ...(options.data?.() || {}),
    planId,
    open,
    componentOptions: options,
    emitted: [],
    $emit(...args) {
      this.emitted.push(args)
    },
  })

  for (const [name, getter] of Object.entries(options.computed || {})) {
    Object.defineProperty(vm, name, {
      configurable: true,
      get: () => getter.call(vm),
    })
  }
  for (const [name, method] of Object.entries(options.methods || {})) {
    vm[name] = method.bind(vm)
  }

  return vm
}

function installInnerAudioContextFake() {
  const contexts = []
  globalThis.uni.createInnerAudioContext = vi.fn(() => {
    const listeners = {}
    const context = {
      autoplay: undefined,
      src: '',
      duration: 0,
      currentTime: 0,
      play: vi.fn(),
      pause: vi.fn(),
      stop: vi.fn(),
      destroy: vi.fn(),
      onPlay: vi.fn((callback) => { listeners.play = callback }),
      onPause: vi.fn((callback) => { listeners.pause = callback }),
      onCanplay: vi.fn((callback) => { listeners.canplay = callback }),
      onTimeUpdate: vi.fn((callback) => { listeners.timeupdate = callback }),
      onEnded: vi.fn((callback) => { listeners.ended = callback }),
      onError: vi.fn((callback) => { listeners.error = callback }),
      offPlay: vi.fn(),
      offPause: vi.fn(),
      offCanplay: vi.fn(),
      offTimeUpdate: vi.fn(),
      offEnded: vi.fn(),
      offError: vi.fn(),
      emit(name, detail) { return listeners[name]?.(detail) },
    }
    contexts.push(context)
    return context
  })
  return contexts
}

function expectSessionEnded() {
  const guideStore = useGuideStore()
  const userStore = useUserStore()
  expect(userStore.isLoggedIn).toBe(false)
  expect(userStore.token).toBe('')
  expect(guideStore.currentGuide).toBeNull()
  expect(guideStore.error).toBeNull()
  expect(guideStore.isLoading).toBe(false)
  expect(guideStore.isGenerating).toBe(false)
  expect(logoutRequests()).toHaveLength(1)
  expect(getReLaunchCalls()).toEqual([{ url: '/pages/login/index' }])
}

beforeEach(() => {
  resetUniRuntime()
  setActivePinia(createPinia())
  login()
})

afterEach(() => {
  delete globalThis.uni.createInnerAudioContext
})

describe('P8.4A AudioGuideSheet 401 session cleanup', () => {
  test('1. a current Guide GET 401 ends the current user session', async () => {
    setRequestHandler((options) => {
      if (logoutSuccess(options)) return
      if (options.url.endsWith(`/plans/${planA.id}/guide`)) {
        respondError(options, 401, 'INVALID_TOKEN', 'expired')
        return
      }
      throw new Error(`Unexpected request: ${options.url}`)
    })

    await expect(useGuideStore().fetchGuide(planA.id)).resolves.toBeNull()
    expectSessionEnded()
  })

  test('2. a current Guide generate 401 ends the current user session', async () => {
    setRequestHandler((options) => {
      if (logoutSuccess(options)) return
      if (options.url.endsWith(`/plans/${planA.id}/guide/generate`)) {
        respondError(options, 401, 'TOKEN_EXPIRED', 'expired')
        return
      }
      throw new Error(`Unexpected request: ${options.url}`)
    })

    await expect(useGuideStore().generateGuide(planA.id)).resolves.toBeNull()
    expectSessionEnded()
  })

  test('3. a current signed-URL refresh 401 ends the current user session', async () => {
    const contexts = installInnerAudioContextFake()
    let guideRequestCount = 0
    setRequestHandler((options) => {
      if (logoutSuccess(options)) return
      if (options.url.endsWith(`/plans/${planA.id}/guide`)) {
        guideRequestCount += 1
        if (guideRequestCount === 1) {
          respond(options, { guide: guideFor(planA.id) })
          return
        }
        respondError(options, 401, 'INVALID_TOKEN', 'expired')
        return
      }
      throw new Error(`Unexpected request: ${options.url}`)
    })

    const vm = createAudioGuideSheetVm()
    await vm.openForPlan()
    await vm.playAudio()
    await contexts[0].emit('error')

    expectSessionEnded()
    expect(vm.displayGuide).toBeNull()
    expect(vm.error).toBeNull()
    expect(vm.audioError).toBe('')
    expect(vm.isRefreshingAudioUrl).toBe(false)
  })

  test('4. a Sheet guide retry 401 ends the current user session', async () => {
    let guideRequestCount = 0
    setRequestHandler((options) => {
      if (logoutSuccess(options)) return
      if (options.url.endsWith(`/plans/${planA.id}/guide`)) {
        guideRequestCount += 1
        if (guideRequestCount === 1) {
          respondError(options, 500, 'GUIDE_UNAVAILABLE', 'temporary failure')
          return
        }
        respondError(options, 401, 'INVALID_TOKEN', 'expired')
        return
      }
      throw new Error(`Unexpected request: ${options.url}`)
    })

    const vm = createAudioGuideSheetVm()
    await vm.openForPlan()
    expect(vm.sheetState).toBe('guide-error')

    vm.retryGuide()
    await flushRuntimePromises()
    await flushRuntimePromises()
    await flushRuntimePromises()

    expectSessionEnded()
    expect(vm.displayGuide).toBeNull()
    expect(vm.error).toBeNull()
  })

  test('5. a signed-URL refresh 401 never starts another automatic retry or leaves an audio error', async () => {
    const contexts = installInnerAudioContextFake()
    let guideRequestCount = 0
    setRequestHandler((options) => {
      if (logoutSuccess(options)) return
      if (options.url.endsWith(`/plans/${planA.id}/guide`)) {
        guideRequestCount += 1
        if (guideRequestCount === 1) {
          respond(options, { guide: guideFor(planA.id) })
          return
        }
        respondError(options, 401, 'HTTP_ERROR', 'unauthorized')
        return
      }
      throw new Error(`Unexpected request: ${options.url}`)
    })

    const vm = createAudioGuideSheetVm()
    await vm.openForPlan()
    await vm.playAudio()
    await contexts[0].emit('error')
    await contexts[0].emit('error')

    expect(guideRequests()).toHaveLength(2)
    expect(vm.audioError).toBe('')
    expect(vm.sheetState).toBe('closed')
    expectSessionEnded()
  })

  test('6. a 500 remains a normal Guide error and does not logout', async () => {
    setRequestHandler((options) => {
      if (options.url.endsWith(`/plans/${planA.id}/guide`)) {
        respondError(options, 500, 'GUIDE_UNAVAILABLE', 'temporary failure')
        return
      }
      throw new Error(`Unexpected request: ${options.url}`)
    })

    await expect(useGuideStore().fetchGuide(planA.id)).rejects.toMatchObject({ statusCode: 500, code: 'GUIDE_UNAVAILABLE' })
    expect(useUserStore().isLoggedIn).toBe(true)
    expect(useGuideStore().error).toMatchObject({ statusCode: 500, code: 'GUIDE_UNAVAILABLE' })
    expect(logoutRequests()).toEqual([])
  })

  test('7. a network failure remains a normal Guide error and does not logout', async () => {
    setRequestHandler((options) => {
      if (options.url.endsWith(`/plans/${planA.id}/guide`)) {
        options.fail({ errMsg: 'request:fail network down' })
        return
      }
      throw new Error(`Unexpected request: ${options.url}`)
    })

    await expect(useGuideStore().fetchGuide(planA.id)).rejects.toMatchObject({ statusCode: 0, code: 'NETWORK_ERROR' })
    expect(useUserStore().isLoggedIn).toBe(true)
    expect(useGuideStore().error).toMatchObject({ statusCode: 0, code: 'NETWORK_ERROR' })
    expect(logoutRequests()).toEqual([])
  })

  test('8. an old-user 401 cannot logout the new user session', async () => {
    const delayedUnauthorized = createDeferred()
    setRequestHandler((options) => {
      if (logoutSuccess(options)) return
      if (options.url.endsWith(`/plans/${planA.id}/guide`)) {
        delayedUnauthorized.promise.then(() => respondError(options, 401, 'INVALID_TOKEN', 'expired'))
        return
      }
      throw new Error(`Unexpected request: ${options.url}`)
    })

    const pendingA = useGuideStore().fetchGuide(planA.id)
    await flushRuntimePromises()
    await endUserSession()
    login(userB)
    delayedUnauthorized.resolve()
    await expect(pendingA).resolves.toBeNull()

    expect(useUserStore().isLoggedIn).toBe(true)
    expect(useUserStore().userInfo.id).toBe(userB.id)
    expect(logoutRequests()).toHaveLength(1)
    expect(getReLaunchCalls()).toHaveLength(1)
  })

  test('9. a 401 arriving after logout cannot perform a second cleanup', async () => {
    const delayedUnauthorized = createDeferred()
    setRequestHandler((options) => {
      if (logoutSuccess(options)) return
      if (options.url.endsWith(`/plans/${planA.id}/guide`)) {
        delayedUnauthorized.promise.then(() => respondError(options, 401, 'INVALID_TOKEN', 'expired'))
        return
      }
      throw new Error(`Unexpected request: ${options.url}`)
    })

    const pendingGuide = useGuideStore().fetchGuide(planA.id)
    await flushRuntimePromises()
    await endUserSession()
    delayedUnauthorized.resolve()
    await expect(pendingGuide).resolves.toBeNull()

    expect(useUserStore().isLoggedIn).toBe(false)
    expect(logoutRequests()).toHaveLength(1)
    expect(getReLaunchCalls()).toHaveLength(1)
  })

  test('10. a same-session stale Guide request 401 still ends that current session', async () => {
    const delayedA = createDeferred()
    const delayedB = createDeferred()
    setRequestHandler((options) => {
      if (logoutSuccess(options)) return
      if (options.url.endsWith(`/plans/${planA.id}/guide`)) {
        delayedA.promise.then(() => respondError(options, 401, 'INVALID_TOKEN', 'expired'))
        return
      }
      if (options.url.endsWith(`/plans/${planB.id}/guide`)) {
        delayedB.promise.then((data) => respond(options, data))
        return
      }
      throw new Error(`Unexpected request: ${options.url}`)
    })

    const guideStore = useGuideStore()
    const pendingA = guideStore.fetchGuide(planA.id)
    await flushRuntimePromises()
    const pendingB = guideStore.fetchGuide(planB.id)
    await flushRuntimePromises()

    delayedA.resolve()
    await expect(pendingA).resolves.toBeNull()
    delayedB.resolve({ guide: guideFor(planB.id) })
    await expect(pendingB).resolves.toBeNull()

    expectSessionEnded()
  })

  test('11. audio callbacks after a 401 session cleanup are no-ops', async () => {
    const contexts = installInnerAudioContextFake()
    let guideRequestCount = 0
    setRequestHandler((options) => {
      if (logoutSuccess(options)) return
      if (options.url.endsWith(`/plans/${planA.id}/guide`)) {
        guideRequestCount += 1
        if (guideRequestCount === 1) {
          respond(options, { guide: guideFor(planA.id) })
          return
        }
        respondError(options, 401, 'INVALID_TOKEN', 'expired')
        return
      }
      throw new Error(`Unexpected request: ${options.url}`)
    })

    const vm = createAudioGuideSheetVm()
    await vm.openForPlan()
    await vm.playAudio()
    await contexts[0].emit('error')
    await contexts[0].emit('play')
    await contexts[0].emit('timeupdate')
    await contexts[0].emit('error')

    expect(vm.displayGuide).toBeNull()
    expect(vm.isPlaying).toBe(false)
    expect(vm.currentTime).toBe(0)
    expect(vm.duration).toBe(0)
    expect(guideRequests()).toHaveLength(2)
    expectSessionEnded()
  })

  test('12. a closed Sheet still ends the current session when its in-flight Guide request returns 401', async () => {
    const delayedUnauthorized = createDeferred()
    setRequestHandler((options) => {
      if (logoutSuccess(options)) return
      if (options.url.endsWith(`/plans/${planA.id}/guide`)) {
        delayedUnauthorized.promise.then(() => respondError(options, 401, 'INVALID_TOKEN', 'expired'))
        return
      }
      throw new Error(`Unexpected request: ${options.url}`)
    })

    const vm = createAudioGuideSheetVm()
    const pendingGuide = vm.openForPlan()
    await flushRuntimePromises()
    vm.closeSheet()
    delayedUnauthorized.resolve()
    await pendingGuide

    expect(vm.sheetState).toBe('closed')
    expectSessionEnded()
  })
})
