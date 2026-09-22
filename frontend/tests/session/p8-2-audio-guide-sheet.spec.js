import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { isProxy, proxyRefs, reactive, shallowRef } from 'vue'
import { useGuideStore } from '../../src/stores/guide.js'
import { usePlanStore } from '../../src/stores/plan.js'
import { useUserStore } from '../../src/stores/user.js'
import { getCurrentSession, isCurrentSession } from '../../src/utils/sessionBoundary.js'
import {
  createDeferred,
  flushRuntimePromises,
  getRequestCalls,
  resetUniRuntime,
  setRequestHandler,
} from './setup/uniRuntime.js'

const workspaceRoot = resolve(process.cwd(), '..')
const frontendFile = (...segments) => resolve(workspaceRoot, 'frontend', ...segments)

const paths = {
  sheet: frontendFile('src', 'components', 'AudioGuideSheet.vue'),
  home: frontendFile('src', 'pages', 'home', 'index.vue'),
  exploreDetail: frontendFile('src', 'pages', 'explore-detail', 'index.vue'),
  tasks: frontendFile('src', 'pages', 'tasks', 'index.vue'),
  taskDetail: frontendFile('src', 'pages', 'task-detail', 'index.vue'),
}

const user = { id: 820, nickname: 'P8.2A Runtime User' }
const planA = { id: 401, destination: 'Plan A' }
const planB = { id: 402, destination: 'Plan B' }

function source(path) {
  return existsSync(path) ? readFileSync(path, 'utf8') : ''
}

function respond(options, data, statusCode = 200) {
  options.success({ statusCode, data: { success: true, data } })
}

function guideFor(planId, overrides = {}) {
  return {
    id: `guide-${planId}`,
    planId,
    destination: `Destination ${planId}`,
    childIntro: [`Intro ${planId}`],
    questions: [`Question ${planId}`],
    focusItems: [`Focus ${planId}`],
    audioUrl: null,
    ...overrides,
  }
}

function guideRequests() {
  return getRequestCalls().filter((call) => call.url.includes('/guide'))
}

function login() {
  useUserStore().loginSuccess('p8-2a-token', user)
}

function loadAudioGuideSheetOptions() {
  const sheetSource = source(paths.sheet)
  const script = sheetSource.match(/<script>\s*([\s\S]*?)<\/script>/)?.[1]
  expect(script).toBeTruthy()

  const executable = script
    .replace(/^import .+$/gm, '')
    .replace(/export default\s+/, 'return ')

  return new Function('useGuideStore', 'usePlanStore', 'shallowRef', 'getCurrentSession', 'isCurrentSession', executable)(
    useGuideStore,
    usePlanStore,
    shallowRef,
    getCurrentSession,
    isCurrentSession,
  )
}

function createAudioGuideSheetVm({ planId = planA.id, open = true } = {}, { reactiveInstance = false } = {}) {
  const options = loadAudioGuideSheetOptions()
  const rawVm = {
    ...(options.data?.() || {}),
    planId,
    open,
    componentOptions: options,
    emitted: [],
    $emit(...args) {
      this.emitted.push(args)
    },
  }
  const vm = reactiveInstance ? reactive(rawVm) : proxyRefs(rawVm)

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

beforeEach(() => {
  resetUniRuntime()
  setActivePinia(createPinia())
})

afterEach(() => {
  delete globalThis.uni.createInnerAudioContext
})

describe('P8.2A Home entry', () => {
  test('1. current Plan A opens the shared Sheet for A after current-plan recovery', () => {
    const home = source(paths.home)

    expect(home).toContain("import AudioGuideSheet from '../../components/AudioGuideSheet.vue'")
    expect(home).toMatch(/ensureCurrentPlanReady\(\{\s*withTasks:\s*false\s*}\)/)
    expect(home).toContain('audioGuideOpen')
    expect(home).toMatch(/audioGuidePlanId\s*=\s*.*currentPlan.*\.id/)
    expect(home).toContain('<AudioGuideSheet')
  })

  test('2. no Plan keeps the Sheet closed instead of creating a Plan', () => {
    const home = source(paths.home)
    const sheet = source(paths.sheet)
    const openAudioGuideSource = home.match(/async openAudioGuide\(\) \{[\s\S]*?\n    \},/)?.[0] || ''

    expect(home).toMatch(/audioGuidePlanId\s*=\s*null/)
    expect(home).toContain('audioGuideOpen = false')
    expect(openAudioGuideSource).toContain('ensureCurrentPlanReady')
    expect(openAudioGuideSource).not.toContain('createPlan')
    expect(openAudioGuideSource).not.toContain('ensureGuide')
    expect(sheet).toContain('no-plan')
    expect(sheet).toContain('暂无可查看的景点讲解')
    expect(sheet).toContain('去探索')
  })

  test('3. Home does not directly load or generate a Guide before its explicit entry click', () => {
    const home = source(paths.home)

    expect(home).not.toContain('useGuideStore')
    expect(home).not.toContain('ensureGuide')
    expect(home).not.toContain("path: '/pages/guide/index'")
  })
})

describe('P8.2A Explore Detail entry', () => {
  test('4. explicit Plan A opens the shared Sheet and keeps Plan B out of the request path', () => {
    const detail = source(paths.exploreDetail)

    expect(detail).toContain("import AudioGuideSheet from '../../components/AudioGuideSheet.vue'")
    expect(detail).toContain('<AudioGuideSheet')
    expect(detail).toMatch(/audioGuidePlanId\s*=\s*this\.displayPlan\?\.id/)
    expect(detail).not.toContain('/pages/guide/index?planId=')
  })

  test('5. an invalid explicit plan stays unavailable and never falls back to persisted Plan B', () => {
    const detail = source(paths.exploreDetail)

    expect(detail).toMatch(/ensureCurrentPlanReady\(\{[\s\S]*planId:\s*this\.planId/)
    expect(detail).toContain('result.unavailable')
    expect(detail).toContain('audioGuidePlanId = null')
  })
})

describe('P8.2A Task route and entry', () => {
  test('6. Tasks includes both taskId and its exact planId in the detail URL', () => {
    const tasks = source(paths.tasks)

    expect(tasks).toMatch(/\/pages\/task-detail\/index\?id=\$\{item\.id}\&planId=\$\{encodeURIComponent\(String\(item\.planId\)\)\}/)
  })

  test('7. Task Detail strictly recovers the route Plan A instead of persisted Plan B', () => {
    const detail = source(paths.taskDetail)

    expect(detail).toMatch(/routePlanId:\s*['"]/)
    expect(detail).toMatch(/routePlanId\s*=\s*String\(options\?\.planId\s*\|\|\s*(?:''|"")\)/)
    expect(detail).toMatch(/ensureCurrentPlanReady\(\{[\s\S]*planId:\s*this\.routePlanId/)
  })

  test('8. a task whose planId mismatches the route planId cannot expose Guide entry', () => {
    const detail = source(paths.taskDetail)

    expect(detail).toMatch(/currentTask\.planId[\s\S]*routePlanId|routePlanId[\s\S]*currentTask\.planId/)
    expect(detail).toContain('isTaskPlanVerified')
    expect(detail).toMatch(/v-if="isTaskPlanVerified"[\s\S]*查看景点讲解/)
  })

  test('9. a verified Task A opens the shared Sheet for currentTask.planId', () => {
    const detail = source(paths.taskDetail)

    expect(detail).toContain("import AudioGuideSheet from '../../components/AudioGuideSheet.vue'")
    expect(detail).toContain('<AudioGuideSheet')
    expect(detail).toMatch(/audioGuidePlanId\s*=\s*this\.currentTask\.planId/)
    expect(detail).not.toContain('/pages/guide/index')
  })
})

describe('P8.2A preserved Guide contract', () => {
  test('10. an existing Guide uses GET only', async () => {
    login()
    setRequestHandler((options) => {
      if (options.url.endsWith(`/plans/${planA.id}/guide`) && options.method === 'GET') {
        respond(options, { guide: guideFor(planA.id) })
        return
      }
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    await expect(useGuideStore().ensureGuide(planA.id)).resolves.toMatchObject({ planId: planA.id })
    expect(guideRequests().map((request) => request.method)).toEqual(['GET'])
  })

  test('11. GUIDE_NOT_FOUND triggers exactly one generate request', async () => {
    login()
    setRequestHandler((options) => {
      if (options.url.endsWith(`/plans/${planA.id}/guide`) && options.method === 'GET') {
        options.success({
          statusCode: 404,
          data: { success: false, error: { code: 'GUIDE_NOT_FOUND', message: 'missing' } },
        })
        return
      }
      if (options.url.endsWith(`/plans/${planA.id}/guide/generate`) && options.method === 'POST') {
        respond(options, { guide: guideFor(planA.id) }, 201)
        return
      }
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    await expect(useGuideStore().ensureGuide(planA.id)).resolves.toMatchObject({ planId: planA.id })
    expect(guideRequests().map((request) => request.method)).toEqual(['GET', 'POST'])
  })

  test('12. a Guide network failure performs zero generate requests', async () => {
    login()
    setRequestHandler((options) => {
      if (options.url.endsWith(`/plans/${planA.id}/guide`) && options.method === 'GET') {
        options.fail({ errMsg: 'network down' })
        return
      }
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    await expect(useGuideStore().ensureGuide(planA.id)).rejects.toMatchObject({ code: 'NETWORK_ERROR' })
    expect(guideRequests().map((request) => request.method)).toEqual(['GET'])
  })
})

describe('P8.2A Sheet request isolation', () => {
  test('13. a late A response cannot overwrite visible B', () => {
    const sheet = source(paths.sheet)

    expect(sheet).toContain('requestSequence')
    expect(sheet).toContain('requestedPlanId')
    expect(sheet).toMatch(/requestSequence[\s\S]*requestedPlanId[\s\S]*guide\.planId/)
    expect(sheet).toMatch(/requestedPlanId[\s\S]*this\.planId/)
  })

  test('14. closing the Sheet makes a late response unable to update visible state', () => {
    const sheet = source(paths.sheet)

    expect(sheet).toMatch(/close[A-Za-z]*\(\)[\s\S]*requestSequence/)
    expect(sheet).toMatch(/if\s*\([^)]*!this\.open/)
    expect(sheet).toContain("emit('update:open', false)")
  })

  test('15. repeated clicks for the same plan reuse the existing ensureGuide de-duplication', async () => {
    login()
    setRequestHandler((options) => {
      if (options.url.endsWith(`/plans/${planB.id}/guide`) && options.method === 'GET') {
        respond(options, { guide: guideFor(planB.id) })
        return
      }
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    const guideStore = useGuideStore()
    await Promise.all([guideStore.ensureGuide(planB.id), guideStore.ensureGuide(planB.id)])
    expect(guideRequests()).toHaveLength(1)
  })
})

describe('P8.2A honest audio and related-image states', () => {
  test('16. a null audioUrl renders no-audio text rather than a playable control', () => {
    const sheet = source(paths.sheet)

    expect(sheet).toContain('audioUrl')
    expect(sheet).toContain('no-audio')
    expect(sheet).toContain('语音讲解暂未准备好')
  })

  test('17. the B3 Sheet permits real playback only from its explicit user action', () => {
    const sheet = source(paths.sheet)

    expect(sheet).toContain('createInnerAudioContext')
    expect(sheet).toMatch(/@click="playAudio"/)
    expect(sheet).not.toMatch(/setInterval|fakeDuration|playbackRate/)
  })

  test('18. a real sourceSnapshot attraction cover is the only related-image source', () => {
    const sheet = source(paths.sheet)

    expect(sheet).toContain('sourceSnapshot')
    expect(sheet).toContain('coverImage')
    expect(sheet).toContain('相关图片')
    expect(sheet).not.toMatch(/TaskSubmission|task\.record|record\.imageUrl|guide-palace-detail/)
  })

  test('19. no cover image has an explicit related-images-empty state', () => {
    const sheet = source(paths.sheet)

    expect(sheet).toContain('related-images-empty')
    expect(sheet).toMatch(/!.*coverImage|coverImage.*\?/) 
  })
})

describe('P8.2B3 strict Guide GET and real-player foundation', () => {
  test('24. a missing Guide remains unavailable after one GET and never generates audio or a Guide', async () => {
    login()
    const contexts = installInnerAudioContextFake()
    setRequestHandler((options) => {
      if (options.url.endsWith(`/plans/${planA.id}/guide`) && options.method === 'GET') {
        options.success({
          statusCode: 404,
          data: { success: false, error: { code: 'GUIDE_NOT_FOUND', message: 'missing' } },
        })
        return
      }
      if (options.url.endsWith(`/plans/${planA.id}/guide/generate`) && options.method === 'POST') {
        respond(options, { guide: guideFor(planA.id) }, 201)
        return
      }
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    const vm = createAudioGuideSheetVm()
    await vm.openForPlan()

    expect(guideRequests().map((request) => request.method)).toEqual(['GET'])
    expect(getRequestCalls().filter((request) => /\/guide\/audio\/(?:request|retry)$/.test(request.url))).toEqual([])
    expect(vm.sheetState).toBe('guide-unavailable')
    expect(vm.displayGuide).toBeNull()
    expect(globalThis.uni.createInnerAudioContext).not.toHaveBeenCalled()
    expect(contexts).toEqual([])
  })

  test('25. a ready Guide exposes a play entry without creating or playing audio on Sheet open', async () => {
    login()
    const contexts = installInnerAudioContextFake()
    const readyGuide = guideFor(planA.id, {
      audioStatus: 'ready',
      audioUrl: 'https://signed.example/audio.mp3',
      audioDurationSec: 34,
    })
    setRequestHandler((options) => {
      if (options.url.endsWith(`/plans/${planA.id}/guide`) && options.method === 'GET') {
        respond(options, { guide: readyGuide })
        return
      }
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    const vm = createAudioGuideSheetVm()
    await vm.openForPlan()

    expect(globalThis.uni.createInnerAudioContext).not.toHaveBeenCalled()
    expect(contexts).toEqual([])
    expect(vm.canPlayAudio).toBe(true)
    expect(source(paths.sheet)).toMatch(/v-if="canPlayAudio"[\s\S]*@click="playAudio"/)
  })

  test('26. a user play action creates the Context, sets a non-autoplay source, then plays', async () => {
    login()
    const contexts = installInnerAudioContextFake()
    const audioUrl = 'https://signed.example/audio.mp3'
    setRequestHandler((options) => {
      if (options.url.endsWith(`/plans/${planA.id}/guide`) && options.method === 'GET') {
        respond(options, {
          guide: guideFor(planA.id, { audioStatus: 'ready', audioUrl, audioDurationSec: 34 }),
        })
        return
      }
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    const vm = createAudioGuideSheetVm()
    await vm.openForPlan()
    expect(globalThis.uni.createInnerAudioContext).not.toHaveBeenCalled()
    expect(typeof vm.playAudio).toBe('function')
    if (typeof vm.playAudio !== 'function') return

    await vm.playAudio()

    expect(globalThis.uni.createInnerAudioContext).toHaveBeenCalledTimes(1)
    const [context] = contexts
    expect(context.autoplay).toBe(false)
    expect(context.src).toBe(audioUrl)
    expect(context.play).toHaveBeenCalledTimes(1)
    context.emit('play')
    expect(vm.isPlaying).toBe(true)
  })

  test('27. runtime duration and progress come only from InnerAudioContext events', async () => {
    login()
    const contexts = installInnerAudioContextFake()
    setRequestHandler((options) => {
      if (options.url.endsWith(`/plans/${planA.id}/guide`) && options.method === 'GET') {
        respond(options, {
          guide: guideFor(planA.id, {
            audioStatus: 'ready',
            audioUrl: 'https://signed.example/audio.mp3',
            audioDurationSec: 34,
          }),
        })
        return
      }
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    const vm = createAudioGuideSheetVm()
    await vm.openForPlan()
    expect(typeof vm.playAudio).toBe('function')
    if (typeof vm.playAudio !== 'function') return
    await vm.playAudio()

    const [context] = contexts
    context.duration = 33.7
    context.emit('canplay')
    expect(vm.duration).toBe(33.7)
    context.currentTime = 7.2
    context.emit('timeupdate')
    expect(vm.currentTime).toBe(7.2)
    expect(vm.audioProgressPercent).toBeCloseTo((7.2 / 33.7) * 100)
    expect(vm.duration).not.toBe(vm.displayGuide.audioDurationSec)
  })

  test.each([
    ['none', null],
    ['pending', null],
    ['failed', null],
    ['ready', null],
  ])('28. %s audio without a URL never creates an executable player', async (audioStatus, audioUrl) => {
    login()
    const contexts = installInnerAudioContextFake()
    const requestPlanId = `${planA.id}-${audioStatus}`
    setRequestHandler((options) => {
      if (options.url.endsWith(`/plans/${requestPlanId}/guide`) && options.method === 'GET') {
        respond(options, {
          guide: guideFor(requestPlanId, { audioStatus, audioUrl, audioDurationSec: null }),
        })
        return
      }
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    const vm = createAudioGuideSheetVm({ planId: requestPlanId })
    await vm.openForPlan()

    expect(vm.canPlayAudio).toBe(false)
    expect(globalThis.uni.createInnerAudioContext).not.toHaveBeenCalled()
    expect(contexts).toEqual([])
    expect(vm.isPlaying).toBe(false)
    expect(vm.currentTime).toBe(0)
    expect(vm.duration).toBe(0)
    expect(vm.displayGuide.childIntro).toEqual([`Intro ${requestPlanId}`])
  })

  test('29. reopening a Sheet performs another strict GET to obtain a fresh signed URL', async () => {
    login()
    const audioUrls = [
      'https://signed.example/audio-first.mp3',
      'https://signed.example/audio-second.mp3',
    ]
    let responseIndex = 0
    setRequestHandler((options) => {
      if (options.url.endsWith(`/plans/${planA.id}/guide`) && options.method === 'GET') {
        respond(options, {
          guide: guideFor(planA.id, {
            audioStatus: 'ready',
            audioUrl: audioUrls[responseIndex++],
            audioDurationSec: 34,
          }),
        })
        return
      }
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    const vm = createAudioGuideSheetVm()
    await vm.openForPlan()
    const firstAudioUrl = vm.displayGuide.audioUrl
    vm.open = false
    vm.resetAfterClose()
    vm.open = true
    await vm.openForPlan()

    expect(guideRequests().map((request) => request.method)).toEqual(['GET', 'GET'])
    expect(firstAudioUrl).toBe(audioUrls[0])
    expect(vm.displayGuide.audioUrl).toBe(audioUrls[1])
  })

  test('30. pause and resume reuse the current Context without another GET or signed URL', async () => {
    login()
    const contexts = installInnerAudioContextFake()
    const audioUrl = 'https://signed.example/audio.mp3'
    setRequestHandler((options) => {
      if (options.url.endsWith(`/plans/${planA.id}/guide`) && options.method === 'GET') {
        respond(options, { guide: guideFor(planA.id, { audioStatus: 'ready', audioUrl, audioDurationSec: 34 }) })
        return
      }
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    const vm = createAudioGuideSheetVm()
    await vm.openForPlan()
    await vm.playAudio()
    const [context] = contexts
    context.emit('play')
    expect(vm.isPlaying).toBe(true)

    vm.playAudio()
    expect(context.pause).toHaveBeenCalledTimes(1)
    context.emit('pause')
    expect(vm.isPlaying).toBe(false)

    vm.playAudio()
    expect(globalThis.uni.createInnerAudioContext).toHaveBeenCalledTimes(1)
    expect(context.play).toHaveBeenCalledTimes(2)
    expect(context.src).toBe(audioUrl)
    expect(guideRequests().map((request) => request.method)).toEqual(['GET'])
    context.emit('play')
    expect(vm.isPlaying).toBe(true)
  })

  test('31. ended resets the visible position to zero and never auto-replays', async () => {
    login()
    const contexts = installInnerAudioContextFake()
    setRequestHandler((options) => {
      if (options.url.endsWith(`/plans/${planA.id}/guide`) && options.method === 'GET') {
        respond(options, {
          guide: guideFor(planA.id, { audioStatus: 'ready', audioUrl: 'https://signed.example/audio.mp3', audioDurationSec: 34 }),
        })
        return
      }
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    const vm = createAudioGuideSheetVm()
    await vm.openForPlan()
    await vm.playAudio()
    const [context] = contexts
    context.duration = 33.7
    context.currentTime = 33.7
    context.emit('play')
    context.emit('canplay')
    context.emit('timeupdate')
    expect(vm.isPlaying).toBe(true)
    expect(vm.currentTime).toBe(33.7)

    context.emit('ended')

    expect(context.onEnded).toHaveBeenCalledTimes(1)
    expect(vm.isPlaying).toBe(false)
    expect(vm.currentTime).toBe(0)
    expect(context.play).toHaveBeenCalledTimes(1)
  })

  test('32. closing an active Sheet invalidates, unbinds, stops, and destroys its Context', async () => {
    login()
    const contexts = installInnerAudioContextFake()
    setRequestHandler((options) => {
      if (options.url.endsWith(`/plans/${planA.id}/guide`) && options.method === 'GET') {
        respond(options, {
          guide: guideFor(planA.id, { audioStatus: 'ready', audioUrl: 'https://signed.example/audio.mp3', audioDurationSec: 34 }),
        })
        return
      }
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    const vm = createAudioGuideSheetVm()
    await vm.openForPlan()
    await vm.playAudio()
    const [context] = contexts
    context.duration = 33.7
    context.currentTime = 7.2
    context.emit('play')
    context.emit('canplay')
    context.emit('timeupdate')
    vm.closeSheet()

    expect(context.stop).toHaveBeenCalledTimes(1)
    for (const method of ['offPlay', 'offPause', 'offCanplay', 'offTimeUpdate', 'offEnded', 'offError']) {
      expect(context[method]).toHaveBeenCalledTimes(1)
    }
    expect(context.destroy).toHaveBeenCalledTimes(1)
    expect(vm.audioContext).toBeNull()
    expect(vm.isPlaying).toBe(false)
    expect(vm.currentTime).toBe(0)
    expect(vm.duration).toBe(0)

    context.currentTime = 29
    await context.emit('timeupdate')
    await context.emit('ended')
    await context.emit('error')
    expect(vm.audioContext).toBeNull()
    expect(vm.isPlaying).toBe(false)
    expect(vm.currentTime).toBe(0)
    expect(vm.duration).toBe(0)
  })

  test('33. switching from A to B destroys A before B GET and stale A events cannot affect B', async () => {
    login()
    const contexts = installInnerAudioContextFake()
    setRequestHandler((options) => {
      if (options.url.endsWith(`/plans/${planA.id}/guide`) && options.method === 'GET') {
        respond(options, {
          guide: guideFor(planA.id, { audioStatus: 'ready', audioUrl: 'https://signed.example/audio-a.mp3', audioDurationSec: 34 }),
        })
        return
      }
      if (options.url.endsWith(`/plans/${planB.id}/guide`) && options.method === 'GET') {
        respond(options, {
          guide: guideFor(planB.id, { audioStatus: 'ready', audioUrl: 'https://signed.example/audio-b.mp3', audioDurationSec: 35 }),
        })
        return
      }
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    const vm = createAudioGuideSheetVm({ planId: planA.id })
    await vm.openForPlan()
    await vm.playAudio()
    const [contextA] = contexts
    contextA.emit('play')
    vm.planId = planB.id
    await vm.openForPlan()

    expect(contextA.stop).toHaveBeenCalledTimes(1)
    expect(contextA.destroy).toHaveBeenCalledTimes(1)
    expect(vm.displayGuide.planId).toBe(planB.id)
    expect(globalThis.uni.createInnerAudioContext).toHaveBeenCalledTimes(1)

    await vm.playAudio()
    const contextB = contexts[1]
    contextB.duration = 35.4
    contextB.currentTime = 4.1
    contextB.emit('play')
    contextB.emit('canplay')
    contextB.emit('timeupdate')
    const stateBeforeStaleA = {
      isPlaying: vm.isPlaying,
      currentTime: vm.currentTime,
      duration: vm.duration,
      displayGuide: vm.displayGuide,
      audioError: vm.audioError,
    }

    contextA.currentTime = 26
    await contextA.emit('timeupdate')
    await contextA.emit('ended')
    await contextA.emit('error')
    expect(vm.isPlaying).toBe(stateBeforeStaleA.isPlaying)
    expect(vm.currentTime).toBe(stateBeforeStaleA.currentTime)
    expect(vm.duration).toBe(stateBeforeStaleA.duration)
    expect(vm.displayGuide).toBe(stateBeforeStaleA.displayGuide)
    expect(vm.audioError).toBe(stateBeforeStaleA.audioError)
  })

  test('34. component unmount disposes an active Context', async () => {
    login()
    const contexts = installInnerAudioContextFake()
    setRequestHandler((options) => {
      if (options.url.endsWith(`/plans/${planA.id}/guide`) && options.method === 'GET') {
        respond(options, {
          guide: guideFor(planA.id, { audioStatus: 'ready', audioUrl: 'https://signed.example/audio.mp3', audioDurationSec: 34 }),
        })
        return
      }
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    const vm = createAudioGuideSheetVm()
    await vm.openForPlan()
    await vm.playAudio()
    const [context] = contexts
    vm.componentOptions.beforeUnmount.call(vm)

    expect(context.stop).toHaveBeenCalledTimes(1)
    expect(context.destroy).toHaveBeenCalledTimes(1)
    expect(vm.audioContext).toBeNull()
    expect(vm.isPlaying).toBe(false)
  })

  test('35. a current audio error refreshes its signed URL once, preserves text, and does not autoplay', async () => {
    login()
    const contexts = installInnerAudioContextFake()
    const originalGuide = guideFor(planA.id, {
      audioStatus: 'ready',
      audioUrl: 'https://signed.example/audio-old.mp3',
      audioDurationSec: 34,
    })
    const refreshedGuide = guideFor(planA.id, {
      audioStatus: 'ready',
      audioUrl: 'https://signed.example/audio-new.mp3',
      audioDurationSec: 34,
    })
    let requestCount = 0
    setRequestHandler((options) => {
      if (options.url.endsWith(`/plans/${planA.id}/guide`) && options.method === 'GET') {
        requestCount += 1
        respond(options, { guide: requestCount === 1 ? originalGuide : refreshedGuide })
        return
      }
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    const vm = createAudioGuideSheetVm()
    await vm.openForPlan()
    await vm.playAudio()
    const [context] = contexts
    context.emit('play')
    await context.emit('error')

    expect(guideRequests().map((request) => request.method)).toEqual(['GET', 'GET'])
    expect(getRequestCalls().filter((request) => request.method === 'POST')).toEqual([])
    expect(context.stop).toHaveBeenCalledTimes(1)
    expect(context.destroy).toHaveBeenCalledTimes(1)
    expect(vm.displayGuide.audioUrl).toBe(refreshedGuide.audioUrl)
    expect(vm.displayGuide.childIntro).toEqual(originalGuide.childIntro)
    expect(vm.displayGuide.questions).toEqual(originalGuide.questions)
    expect(vm.displayGuide.focusItems).toEqual(originalGuide.focusItems)
    expect(vm.audioContext).toBeNull()
    expect(vm.isPlaying).toBe(false)
    expect(globalThis.uni.createInnerAudioContext).toHaveBeenCalledTimes(1)
    expect(vm.audioError).toBe('音频地址已刷新，请重新播放')
  })

  test('36. a failed refresh preserves text and makes the current audio unavailable', async () => {
    login()
    const contexts = installInnerAudioContextFake()
    const originalGuide = guideFor(planA.id, {
      audioStatus: 'ready',
      audioUrl: 'https://signed.example/audio-old.mp3',
      audioDurationSec: 34,
    })
    let requestCount = 0
    setRequestHandler((options) => {
      if (options.url.endsWith(`/plans/${planA.id}/guide`) && options.method === 'GET') {
        requestCount += 1
        if (requestCount === 1) {
          respond(options, { guide: originalGuide })
          return
        }
        options.fail({ errMsg: 'network down' })
        return
      }
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    const vm = createAudioGuideSheetVm()
    await vm.openForPlan()
    await vm.playAudio()
    const [contextA] = contexts
    await contextA.emit('error')
    expect(vm.displayGuide).toMatchObject({ planId: planA.id, audioStatus: 'failed', audioUrl: null })
    expect(vm.displayGuide.childIntro).toEqual(originalGuide.childIntro)
    expect(vm.canPlayAudio).toBe(false)
    expect(globalThis.uni.createInnerAudioContext).toHaveBeenCalledTimes(1)
    expect(guideRequests().map((request) => request.method)).toEqual(['GET', 'GET'])
    expect(getRequestCalls().filter((request) => request.method === 'POST')).toEqual([])
  })

  test('37. a second error after a successful refresh never starts a second automatic URL refresh', async () => {
    login()
    const contexts = installInnerAudioContextFake()
    const firstGuide = guideFor(planA.id, {
      audioStatus: 'ready',
      audioUrl: 'https://signed.example/audio-old.mp3',
      audioDurationSec: 34,
    })
    const refreshedGuide = guideFor(planA.id, {
      audioStatus: 'ready',
      audioUrl: 'https://signed.example/audio-new.mp3',
      audioDurationSec: 34,
    })
    let requestCount = 0
    setRequestHandler((options) => {
      if (options.url.endsWith(`/plans/${planA.id}/guide`) && options.method === 'GET') {
        requestCount += 1
        respond(options, { guide: requestCount === 1 ? firstGuide : refreshedGuide })
        return
      }
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    const vm = createAudioGuideSheetVm()
    await vm.openForPlan()
    await vm.playAudio()
    await contexts[0].emit('error')

    await vm.playAudio()
    const contextB = contexts[1]
    await contextB.emit('error')
    expect(guideRequests().map((request) => request.method)).toEqual(['GET', 'GET'])
    expect(getRequestCalls().filter((request) => request.method === 'POST')).toEqual([])
    expect(vm.displayGuide).toMatchObject({ planId: planA.id, audioStatus: 'failed', audioUrl: null })
    expect(vm.displayGuide.childIntro).toEqual(firstGuide.childIntro)
  })

  test('38. an A signed-URL refresh that returns after B opens cannot overwrite B', async () => {
    login()
    const contexts = installInnerAudioContextFake()
    const delayedRefreshA = createDeferred()
    let aRequestCount = 0
    setRequestHandler((options) => {
      if (options.url.endsWith(`/plans/${planA.id}/guide`) && options.method === 'GET') {
        aRequestCount += 1
        if (aRequestCount === 1) {
          respond(options, {
            guide: guideFor(planA.id, { audioStatus: 'ready', audioUrl: 'https://signed.example/audio-a-old.mp3', audioDurationSec: 34 }),
          })
          return
        }
        delayedRefreshA.promise.then((data) => respond(options, data))
        return
      }
      if (options.url.endsWith(`/plans/${planB.id}/guide`) && options.method === 'GET') {
        respond(options, {
          guide: guideFor(planB.id, { audioStatus: 'ready', audioUrl: 'https://signed.example/audio-b.mp3', audioDurationSec: 35 }),
        })
        return
      }
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    const vm = createAudioGuideSheetVm({ planId: planA.id })
    await vm.openForPlan()
    await vm.playAudio()
    const [contextA] = contexts
    const refreshPromise = contextA.emit('error')
    await flushRuntimePromises()

    vm.planId = planB.id
    await vm.openForPlan()
    expect(vm.displayGuide.planId).toBe(planB.id)
    expect(globalThis.uni.createInnerAudioContext).toHaveBeenCalledTimes(1)

    delayedRefreshA.resolve({
      guide: guideFor(planA.id, { audioStatus: 'ready', audioUrl: 'https://signed.example/audio-a-new.mp3', audioDurationSec: 34 }),
    })
    await refreshPromise

    expect(vm.displayGuide.planId).toBe(planB.id)
    expect(vm.displayGuide.audioUrl).toBe('https://signed.example/audio-b.mp3')
    expect(vm.audioContext).toBeNull()
    expect(globalThis.uni.createInnerAudioContext).toHaveBeenCalledTimes(1)
  })

  test('39. a proxied Options API context must still accept current raw Context events', async () => {
    login()
    const contexts = installInnerAudioContextFake()
    setRequestHandler((options) => {
      if (options.url.endsWith(`/plans/${planA.id}/guide`) && options.method === 'GET') {
        respond(options, {
          guide: guideFor(planA.id, {
            audioStatus: 'ready',
            audioUrl: 'https://signed.example/audio.mp3',
            audioDurationSec: 34,
          }),
        })
        return
      }
      throw new Error(`Unexpected request: ${options.method} ${options.url}`)
    })

    const vm = createAudioGuideSheetVm({}, { reactiveInstance: true })
    await vm.openForPlan()
    await vm.playAudio()
    const [context] = contexts
    context.duration = 33.7
    context.currentTime = 7.2

    expect(isProxy(vm.audioContext)).toBe(false)
    expect(vm.audioContext).toBe(context)
    context.emit('play')
    context.emit('canplay')
    context.emit('timeupdate')

    expect(vm.isPlaying).toBe(true)
    expect(vm.duration).toBe(33.7)
    expect(vm.currentTime).toBe(7.2)
  })
})

describe('P8.2A responsive Bottom Sheet structure', () => {
  test('20. the Sheet is layered above AppTabbar', () => {
    const sheet = source(paths.sheet)

    expect(sheet).toMatch(/z-index:\s*(?:[6-9]\d|[1-9]\d{2,})/)
  })

  test('21. long content uses an internal scroll region', () => {
    const sheet = source(paths.sheet)

    expect(sheet).toMatch(/scroll-view|overflow-y:\s*auto/)
  })

  test('22. the Sheet reserves safe-area-bottom space', () => {
    const sheet = source(paths.sheet)

    expect(sheet).toMatch(/safe-area-inset-bottom|--tl-safe-bottom/)
  })

  test('23. the Sheet declares the 72–82dvh range and narrow/wide viewport rules', () => {
    const sheet = source(paths.sheet)

    expect(sheet).toMatch(/72dvh|82dvh/)
    expect(sheet).toMatch(/@media\s*\(max-width:\s*360px\)/)
    expect(sheet).toMatch(/@media\s*\(min-width:\s*431px\)/)
  })
})
