import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const root = resolve(process.cwd(), '..')
const readFrontendFile = (path) => readFileSync(resolve(root, 'frontend', path), 'utf8')
const homeSource = readFrontendFile('src/pages/home/index.vue')
const tabbarSource = readFrontendFile('src/components/AppTabbar.vue')
const planStoreSource = readFrontendFile('src/stores/plan.js')
const plansApiSource = readFrontendFile('src/api/plans.js')

function blockSource(source, tag) {
  const match = source.match(new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`))
  expect(match).toBeTruthy()
  return match[1]
}

const templateSource = blockSource(homeSource, 'template')
const scriptSource = blockSource(homeSource, 'script')
const styleSource = blockSource(homeSource, 'style')
const tabbarTemplateSource = blockSource(tabbarSource, 'template')
const tabbarScriptSource = blockSource(tabbarSource, 'script')

describe('FE-R5B home visual and business contract', () => {
  test('preserves the existing home business bindings and plan creation boundary', () => {
    expect(scriptSource).toContain("import { useChildStore } from '../../stores/child'")
    expect(scriptSource).toContain("import { usePlanStore } from '../../stores/plan'")
    expect(scriptSource).toContain("import { useUserStore } from '../../stores/user'")
    expect(scriptSource).toContain("import { endUserSession } from '../../utils/sessionBoundary'")
    expect(scriptSource).toContain("searchKeyword: ''")
    expect(scriptSource).toContain('selectAge(ageGroup)')
    expect(scriptSource).toContain('this.planForm.ageGroup = ageGroup')
    expect(scriptSource).toContain('openPlanSheet()')
    expect(scriptSource).toContain("destination: this.searchKeyword.trim() || '故宫博物院'")
    expect(scriptSource).toContain('async submitPlan()')
    expect(scriptSource).toContain('await this.child.fetchChildren(this.user.userInfo.id)')
    expect(scriptSource).toContain('await this.plan.createPlan(')
    expect(scriptSource).toContain('const normalizedTitle = this.planForm.title.trim()')
    expect(scriptSource).toContain('if (normalizedTitle)')
    expect(scriptSource).toContain('payload.title = normalizedTitle')
    expect(scriptSource).toContain('await endUserSession()')
    expect(scriptSource).toContain('goEntry(entry)')
    expect(planStoreSource).toContain('plansApi.createPlan(payload)')
    expect(plansApiSource).toContain("path: '/plans'")
    expect(plansApiSource).toContain("method: 'POST'")
  })

  test('preserves the formal Home routes, upgrades Guide entry to the shared Sheet, and keeps the shared tabbar', () => {
    expect(scriptSource).toContain("path: '/pages/plan/index'")
    expect(scriptSource).toContain("path: '/pages/tasks/index'")
    expect(scriptSource).toContain("action: 'audio-guide'")
    expect(scriptSource).toContain("import AudioGuideSheet from '../../components/AudioGuideSheet.vue'")
    expect(templateSource).toContain('<AudioGuideSheet v-model:open="audioGuideOpen" :plan-id="audioGuidePlanId" />')
    expect(scriptSource).not.toContain("path: '/pages/guide/index'")
    expect(templateSource).toContain('<AppTabbar active="home" />')
    expect(templateSource).toContain("planForm.ageGroup === option.value")
    expect(templateSource).toContain('@click="selectAge(option.value)"')
    expect(templateSource).toContain('class="home-hero__cta" @click="openPlanSheet"')
  })

  test('renders the Hero as a left text page and a right watercolor illustration page', () => {
    for (const marker of [
      'class="home-hero"',
      'class="home-hero__book"',
      'class="home-hero__illustration"',
      'class="home-hero__content"',
    ]) {
      expect(templateSource).toContain(marker)
    }
    expect(templateSource).toMatch(
      /class="home-hero"[\s\S]*?class="home-hero__book"[\s\S]*?home-hero__content[\s\S]*?home-hero__tags[\s\S]*?home-hero__cta[\s\S]*?home-hero__illustration/
    )
    expect(templateSource).toContain('src="../../assets/home/home-hero-watercolor.webp"')
    expect(templateSource).toContain('mode="aspectFill"')
    expect(templateSource).not.toContain('home-hero__title-line')
  })

  test('uses the approved home illustrations instead of CSS geometric placeholders', () => {
    const homeAssets = [
      'home-paper-fiber.webp',
      'home-entry-plan-map.webp',
      'home-entry-guide-cards.webp',
      'home-entry-observation-notebook.webp',
      'home-learning-ancient-life.webp',
      'home-learning-architecture-ritual.webp',
      'home-learning-observation-expression.webp',
    ]

    for (const asset of homeAssets) {
      expect(existsSync(resolve(root, 'frontend', 'src', 'assets', 'home', asset))).toBe(true)
    }

    for (const asset of homeAssets.slice(1)) {
      expect(homeSource).toContain(asset)
    }

    for (const placeholder of [
      'home-entry__art-paper',
      'home-entry__art-mark',
      'home-learn-card__shape',
      'home-learn-card__tape',
      'home-learn-card__badge',
    ]) {
      expect(homeSource).not.toContain(placeholder)
    }
  })

  test('keeps visual card density responsive for 360, 390, and 430 widths', () => {
    expect(styleSource).toContain('grid-template-columns: repeat(3, minmax(0, 1fr));')
    expect(styleSource).toContain('@media (max-width: 360px)')
    expect(styleSource).toContain('grid-template-columns: repeat(2, minmax(0, 1fr));')
    expect(styleSource).toContain('grid-column: span 2;')
    expect(styleSource).toContain('home-paper-fiber.webp')
  })

  test('replaces only the Tabbar icon artwork while preserving its formal navigation contract', () => {
    const tabIcons = [
      'tab-home-idle.svg', 'tab-home-active.svg',
      'tab-route-idle.svg', 'tab-route-active.svg',
      'tab-explore-idle.svg', 'tab-explore-active.svg',
      'tab-record-idle.svg', 'tab-record-active.svg',
      'tab-profile-idle.svg', 'tab-profile-active.svg',
    ]

    for (const asset of tabIcons) {
      expect(existsSync(resolve(root, 'frontend', 'src', 'assets', 'navigation', asset))).toBe(true)
      expect(tabbarSource).toContain(asset)
    }

    for (const item of [
      "{ key: 'home', label: '首页', icon: 'home', path: '/pages/home/index' }",
      "{ key: 'route', label: '路线', icon: 'plan', path: '/pages/route/index' }",
      "{ key: 'explore', label: '探索', icon: 'tasks', path: '/pages/plan/index' }",
      "{ key: 'record', label: '记录', icon: 'record', path: '/pages/record/index' }",
      "{ key: 'profile', label: '我的', icon: 'profile', path: '/pages/profile/index' }",
    ]) {
      expect(tabbarScriptSource).toContain(item)
    }

    expect(tabbarTemplateSource).toContain('class="app-tabbar__icon-image"')
  })

  test('consumes the FE-R5A foundation bridge for the home shell', () => {
    for (const token of [
      'var(--tl-content-max-width)',
      'var(--tl-bg)',
      'var(--tl-paper)',
      'var(--tl-text-main)',
      'var(--tl-text-secondary)',
      'var(--tl-primary)',
      'var(--tl-tabbar-height)',
      'var(--tl-safe-bottom)',
    ]) {
      expect(styleSource).toContain(token)
    }
  })

  test('does not restore removed AI-pet runtime references', () => {
    for (const forbiddenReference of [
      'AiPet',
      'AiChatSheet',
      'usePetStore',
      'stores/pet',
      'mock/ai',
      '小旅',
    ]) {
      expect(homeSource).not.toContain(forbiddenReference)
    }
  })
})
