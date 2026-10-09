import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const root = resolve(process.cwd(), '..')
const readFrontendFile = (path) => readFileSync(resolve(root, 'frontend', path), 'utf8')
const homeSource = readFrontendFile('src/pages/home/index.vue')
const tabbarSource = readFrontendFile('src/components/AppTabbar.vue')

function blockSource(source, tag) {
  const match = source.match(new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`))
  expect(match).toBeTruthy()
  return match[1]
}

const templateSource = blockSource(homeSource, 'template')
const scriptSource = blockSource(homeSource, 'script')
const styleSource = blockSource(homeSource, 'style')

describe('FE-R5B Home visual and business contract', () => {
  test('uses the Home shell as a read-only Route and Plan summary', () => {
    for (const store of ['useChildStore', 'useRouteStore', 'usePlanStore', 'useUserStore']) {
      expect(scriptSource).toContain(store)
    }
    expect(scriptSource).toContain("selectionPolicy: 'none'")
    expect(scriptSource).not.toContain('ensureTasks(')
    expect(scriptSource).not.toContain('generateExplorationPlans(')
    expect(scriptSource).not.toContain('createPlan(')
    expect(scriptSource).toContain('await endUserSession()')
  })

  test('uses current Route data rather than the retired child toolbar and static palace Hero', () => {
    for (const marker of [
      'home-child-context', '切换孩子', 'home-search-row', 'home-age',
      'home-hero-watercolor.webp', '故宫文化探索', '故宫亲子探索', 'home-entry-grid',
    ]) {
      expect(homeSource).not.toContain(marker)
    }
    expect(templateSource).toContain('class="current-exploration"')
    expect(templateSource).toContain('@click="openCurrentExploration"')
    expect(scriptSource).toContain('plan.sourceSnapshot')
    expect(scriptSource).toContain('attraction?.coverImage')
  })

  test('keeps the supplied Home-only Logo safe when its image is unavailable', () => {
    expect(existsSync(resolve(root, 'frontend/src/assets/brand/tonglvji-logo.png'))).toBe(true)
    expect(scriptSource).toContain("import.meta.glob('../../assets/brand/tonglvji-logo.png'")
    expect(templateSource).toContain('v-if="brandLogoPath"')
    expect(templateSource).not.toContain('童旅记')
  })

  test('uses real attractions for recommendations without popularity claims', () => {
    expect(scriptSource).toContain('getAttractions({ limit: 20 })')
    expect(templateSource).toContain('推荐目的地')
    expect(templateSource).toContain('本期推荐')
    expect(templateSource).toContain('更多探索灵感')
    for (const marker of ['大家都在看', '人看过', '本周Top', '热门']) {
      expect(homeSource).not.toContain(marker)
    }
  })

  test('keeps recommendation links on the existing Attraction Detail route', () => {
    expect(scriptSource).toContain('/pages/attraction-detail/index?attractionId=')
    expect(scriptSource).not.toContain('/pages/search/index')
    expect(scriptSource).not.toContain('/pages/message/index')
  })

  test('keeps visual density responsive without restoring old visual cards', () => {
    expect(styleSource).toContain('@media (max-width: 360px)')
    expect(styleSource).toContain('@media (min-width: 431px)')
    expect(styleSource).toContain('var(--tl-content-max-width)')
    expect(styleSource).toContain('var(--tl-divider)')
    expect(styleSource).not.toContain('box-shadow')
  })

  test('preserves the four-item AppTabbar navigation contract', () => {
    for (const item of [
      "{ key: 'home', label: '首页', icon: 'home', path: '/pages/home/index' }",
      "{ key: 'explore', label: '探索', icon: 'explore', path: '/pages/explore/index' }",
      "{ key: 'record', label: '记录', icon: 'record', path: '/pages/record/index' }",
      "{ key: 'profile', label: '我的', icon: 'profile', path: '/pages/profile/index' }",
    ]) {
      expect(tabbarSource).toContain(item)
    }
    expect(homeSource).toContain('<AppTabbar active="home" />')
  })

  test('does not restore removed AI-pet runtime references', () => {
    for (const forbiddenReference of ['AiPet', 'AiChatSheet', 'usePetStore', 'stores/pet', 'mock/ai', '小旅']) {
      expect(homeSource).not.toContain(forbiddenReference)
    }
  })
})
