import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test, vi } from 'vitest'

const root = resolve(process.cwd(), '..')
const homeSource = readFileSync(resolve(root, 'frontend/src/pages/home/index.vue'), 'utf8')

function pageMethod(name, dependencies = {}) {
  const match = homeSource.match(new RegExp(`async ${name}\\(\\) \\{[\\s\\S]*?\\n    \\},`))
  if (!match) {
    throw new Error(`Missing ${name} method`)
  }
  const functionSource = match[0]
    .replace(`async ${name}()`, `async function ${name}()`)
    .replace(/,\s*$/, '')
  return Function(...Object.keys(dependencies), `return (${functionSource})`)(...Object.values(dependencies))
}

describe('P9-05 Home Active Child context', () => {
  test('restores the user session before loading the current user children', async () => {
    const loadHomeChildContext = pageMethod('loadHomeChildContext', {
      isAuthenticationError: () => false,
    })
    const userStore = {
      isAuthReady: false,
      isRestoring: false,
      isLoggedIn: true,
      userInfo: { id: 905 },
      restoreSession: vi.fn(async () => { userStore.isAuthReady = true }),
    }
    const context = {
      childStore: { fetchChildren: vi.fn().mockResolvedValue({}) },
      handleAuthExpired: vi.fn(),
      hasAuthenticatedUser: true,
      syncSelectedAgeGroup: vi.fn(),
      userStore,
    }

    await loadHomeChildContext.call(context)

    expect(userStore.restoreSession).toHaveBeenCalledOnce()
    expect(context.childStore.fetchChildren).toHaveBeenCalledWith(905)
    expect(context.syncSelectedAgeGroup).toHaveBeenCalledOnce()
  })

  test('renders active-child, loading, error, and no-child context locally above the Home search and Hero', () => {
    expect(homeSource).toContain("import { useChildStore } from '../../stores/child'")
    expect(homeSource).toContain("import { useUserStore } from '../../stores/user'")
    expect(homeSource).toContain('当前孩子')
    expect(homeSource).toContain('{{ activeChild.name }} · {{ activeChild.age }}岁')
    expect(homeSource).toContain('正在同步孩子档案')
    expect(homeSource).toContain('孩子资料暂时无法加载')
    expect(homeSource).toContain('完善孩子档案')
    expect(homeSource).toContain('home-child-context')
    expect(homeSource.indexOf('home-child-context')).toBeLessThan(homeSource.indexOf('home-search-row'))
    expect(homeSource).toContain('class="home-hero"')
  })

  test('uses only Child Store activeChild, offers Profile switching, and never writes child profile data from Home', () => {
    expect(homeSource).toContain('this.childStore.activeChild')
    expect(homeSource).not.toContain('children[0]')
    expect(homeSource).not.toContain('currentChild.id')
    expect(homeSource).toContain('切换孩子')
    expect(homeSource).toContain("url: '/pages/profile/index'")
    expect(homeSource).not.toContain('updateChild(')
    expect(homeSource).not.toContain('createChild(')
  })

  test('synchronizes the visible Home age context and Hero age tag from activeChild without restoring manual Plan creation', () => {
    expect(homeSource).toContain('activeChildAgeGroup')
    expect(homeSource).toContain('this.selectedAgeGroup = this.activeChildAgeGroup')
    expect(homeSource).toContain('{{ heroAgeLabel }}')
    expect(homeSource).toContain('规划亲子路线')
    expect(homeSource).toContain("uni.reLaunch({ url: '/pages/explore/index' })")
    expect(homeSource).not.toContain('createPlan(')
    expect(homeSource).not.toContain('planSheetOpen')
  })

  test('retains the shared AudioGuideSheet entry', () => {
    expect(homeSource).toContain('<AudioGuideSheet v-model:open="audioGuideOpen" :plan-id="audioGuidePlanId" />')
    expect(homeSource).toContain('await ensureCurrentPlanReady({ withTasks: false })')
  })
})
