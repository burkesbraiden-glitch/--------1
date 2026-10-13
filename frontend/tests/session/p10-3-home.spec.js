import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const root = resolve(process.cwd(), '..')
const frontendFile = (...segments) => resolve(root, 'frontend', ...segments)
const readFrontendFile = (...segments) => readFileSync(frontendFile(...segments), 'utf8')
const homeSource = readFrontendFile('src', 'pages', 'home', 'index.vue')
const exploreSource = readFrontendFile('src', 'pages', 'explore', 'index.vue')
const tabbarSource = readFrontendFile('src', 'components', 'AppTabbar.vue')

function blockSource(source, tag) {
  const match = source.match(new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`))
  expect(match).toBeTruthy()
  return match[1]
}

const homeTemplate = blockSource(homeSource, 'template')
const homeScript = blockSource(homeSource, 'script')

describe('P10.3 Home summary and navigation', () => {
  test('keeps the supplied Logo safely on Home only', () => {
    expect(existsSync(frontendFile('src', 'assets', 'brand', 'tonglvji-logo.png'))).toBe(true)
    expect(homeScript).toContain("import.meta.glob('../../assets/brand/tonglvji-logo.png'")
    expect(homeTemplate).toContain('v-if="brandLogoPath"')
    expect(homeTemplate).toContain(':src="brandLogoPath"')
    expect(exploreSource).not.toContain('tonglvji-logo.png')
  })

  test('removes obsolete child management and static route-planning UI from Home', () => {
    for (const marker of [
      'home-child-context', '切换孩子', '当前孩子', 'home-age', 'selectedAgeGroup',
      '路线规划', 'home-entry-grid', 'home-learn', 'home-hero-watercolor.webp',
    ]) {
      expect(homeSource).not.toContain(marker)
    }
  })

  test('loads the active-child route and Plan projections without selecting a global Plan or loading Tasks', () => {
    expect(homeScript).toContain('this.childStore.activeChild')
    expect(homeScript).toContain('await this.childStore.fetchChildren(userId)')
    expect(homeScript).toContain('this.routeStore.fetchRoutes(userId, { force })')
    expect(homeScript).toContain("this.planStore.fetchPlans(userId, { selectionPolicy: 'none' })")
    expect(homeScript).not.toContain('selectPlanById(')
    expect(homeScript).not.toContain('ensureTasks(')
    expect(homeScript).not.toContain('generateExplorationPlans(')
  })

  test('uses an in-progress active-child Plan first and carries its full Explore context', () => {
    expect(homeScript).toContain("plan.status === 'in-progress'")
    expect(homeScript).toContain('plan.routeStopId')
    expect(homeScript).toContain('plan.sourceSnapshot')
    expect(homeScript).toContain('routeId')
    expect(homeScript).toContain('dayId')
    expect(homeScript).toContain('stopId')
    expect(homeScript).toContain('planId')
    expect(homeScript).toContain('/pages/explore/index?')
  })

  test('uses honest empty, recommendation, search, and message states', () => {
    expect(homeScript).toContain('开始一次新的亲子旅程')
    expect(homeScript).toContain('getAttractions')
    expect(homeTemplate).toContain('推荐目的地')
    expect(homeTemplate).toContain('本期推荐')
    expect(homeTemplate).toContain('更多探索灵感')
    for (const marker of ['人看过', '本周Top', '1280', '3条消息', 'home-header__dot']) {
      expect(homeSource).not.toContain(marker)
    }
  })

  test('preserves the four-item application tab contract', () => {
    const entries = tabbarSource.match(/\{\s*key:\s*'[^']+',\s*label:\s*'[^']+',\s*icon:\s*'[^']+',\s*path:\s*'[^']+'\s*\}/g) || []
    expect(entries).toHaveLength(4)
    for (const path of ['/pages/home/index', '/pages/explore/index', '/pages/record/index', '/pages/profile/index']) {
      expect(tabbarSource).toContain(path)
    }
  })
})
