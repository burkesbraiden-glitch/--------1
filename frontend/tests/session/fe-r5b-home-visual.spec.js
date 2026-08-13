import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const root = resolve(process.cwd(), '..')
const readFrontendFile = (path) => readFileSync(resolve(root, 'frontend', path), 'utf8')
const homeSource = readFrontendFile('src/pages/home/index.vue')
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

describe('FE-R5B home visual and business contract', () => {
  test('preserves the existing home business bindings and plan creation boundary', () => {
    expect(scriptSource).toContain("import { useChildStore } from '../../stores/child'")
    expect(scriptSource).toContain("import { usePlanStore } from '../../stores/plan'")
    expect(scriptSource).toContain("import { useUserStore } from '../../stores/user'")
    expect(scriptSource).toContain("import { endUserSession } from '../../utils/sessionBoundary'")
    expect(scriptSource).toContain("searchKeyword: ''")
    expect(scriptSource).toContain('selectAge(ageGroup)')
    expect(scriptSource).toContain('this.child.setAgeGroup(ageGroup)')
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

  test('preserves exactly the three primary entry routes and the shared tabbar', () => {
    expect(scriptSource).toContain("path: '/pages/plan/index'")
    expect(scriptSource).toContain("path: '/pages/guide/index'")
    expect(scriptSource).toContain("path: '/pages/tasks/index'")
    expect(templateSource).toContain('<AppTabbar active="home" />')
    expect(templateSource).toContain("child.ageGroup === option.value")
    expect(templateSource).toContain('@click="selectAge(option.value)"')
    expect(templateSource).toContain('class="home-hero__cta" @click="openPlanSheet"')
  })

  test('preserves the approved rounded Hero structure and watercolor asset', () => {
    for (const marker of [
      'class="home-hero"',
      'class="home-hero__book"',
      'class="home-hero__illustration"',
      'class="home-hero__content"',
    ]) {
      expect(templateSource).toContain(marker)
    }
    expect(templateSource).toMatch(
      /class="home-hero"[\s\S]*?class="home-hero__book"[\s\S]*?home-hero__illustration[\s\S]*?home-hero__content[\s\S]*?home-hero__tags[\s\S]*?home-hero__cta/
    )
    expect(templateSource).toContain('src="../../assets/home/home-hero-watercolor.webp"')
    expect(templateSource).toContain('mode="aspectFill"')
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
