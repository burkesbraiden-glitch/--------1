import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { beforeEach, describe, expect, test } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useGuideStore } from '../../src/stores/guide.js'
import { useUserStore } from '../../src/stores/user.js'
import {
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

beforeEach(() => {
  resetUniRuntime()
  setActivePinia(createPinia())
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

  test('2. no Plan opens the Sheet in no-plan state instead of creating a Plan', () => {
    const home = source(paths.home)
    const sheet = source(paths.sheet)
    const openAudioGuideSource = home.match(/async openAudioGuide\(\) \{[\s\S]*?\n    \},/)?.[0] || ''

    expect(home).toMatch(/audioGuidePlanId\s*=\s*null/)
    expect(home).toContain('audioGuideOpen = true')
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

  test('17. the P8.2A Sheet contains no audio playback API or fake progress state', () => {
    const sheet = source(paths.sheet)

    expect(sheet).not.toMatch(/createInnerAudioContext|InnerAudioContext|\.play\(|\.pause\(|\.seek\(|playbackRate/)
    expect(sheet).not.toMatch(/fakeDuration|currentTime|progressValue|audioState:\s*['"]playing/)
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
