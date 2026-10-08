import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const root = resolve(process.cwd(), '..')
const frontendFile = (...segments) => resolve(root, 'frontend', ...segments)
const workbenchPath = frontendFile('src', 'pages', 'explore', 'index.vue')
const workbench = readFileSync(workbenchPath, 'utf8')
const pages = readFileSync(frontendFile('src', 'pages.json'), 'utf8')
const tabbar = readFileSync(frontendFile('src', 'components', 'AppTabbar.vue'), 'utf8')

describe('P10.2 Explore Workbench', () => {
  test('registers the Explore Workbench without removing compatibility pages', () => {
    expect(existsSync(workbenchPath)).toBe(true)
    expect(pages).toContain('"path": "pages/explore/index"')
    for (const legacyPath of [
      '"path": "pages/route/index"',
      '"path": "pages/plan/index"',
      '"path": "pages/explore-detail/index"',
      '"path": "pages/tasks/index"',
    ]) {
      expect(pages).toContain(legacyPath)
    }
  })

  test('uses the Route, Plan, and Task stores for one connected workbench', () => {
    for (const store of ['useRouteStore', 'usePlanStore', 'useTaskStore']) {
      expect(workbench).toContain(store)
    }
    expect(workbench).toContain("selectionPolicy: 'none'")
  })

  test('starts with the current Route instead of a duplicated brand header or homepage tools', () => {
    expect(workbench).toContain('class="route-overview"')
    expect(workbench).toContain("'route-overview--with-image': Boolean(routeHeroImage)")
    expect(workbench).toContain('v-if="routeHeroImage" class="route-overview__shade"')
    expect(workbench).toContain('min-height: 206rpx;')
    expect(workbench).toContain('切换路线')
    expect(workbench).toContain('编辑路线')
    for (const removedHeaderMarker of [
      'tonglvji-logo.png', 'brandLogo', 'workbench-header', 'workbench-brand', 'tool-icon', '童旅记',
    ]) {
      expect(workbench).not.toContain(removedHeaderMarker)
    }
  })

  test('keeps the Route → Day → Stop → Plan → Task hierarchy', () => {
    expect(workbench).toContain('currentRoute?.days')
    expect(workbench).toContain('day.stops')
    expect(workbench).toContain('planForStop(stop.id)')
    expect(workbench).toContain('activeTasks')
    expect(workbench).toContain('hasMultipleDays()')
    expect(workbench).toContain('activeDayLabel()')
    expect(workbench).toContain('hasDistinctActiveDayTitle()')
    expect(workbench.indexOf('class="stop-expanded"')).toBeLessThan(workbench.indexOf('class="task-list"'))
    expect(workbench).toContain('class="stop-block"')
    expect(workbench).toContain('class="task-row"')
    expect(workbench).toContain('class="stop-summary__meta"')
    expect(workbench).toContain('class="stop-summary__summary"')
    expect(workbench).toContain("task.status === 'completed'\">✓")
    expect(workbench).not.toContain("task.status === 'completed' ? '✓' : '○'")
    expect(workbench).not.toContain('class="plan-card"')
    expect(workbench).not.toContain('class="task-card"')
  })

  test('matches plans to Stops through routeStopId and selects only after focus is known', () => {
    expect(workbench).toContain('sameId(plan.routeStopId, stopId)')
    expect(workbench).toContain('this.planStore.selectPlanById(plan.id, this.userStore.userInfo?.id)')
    expect(workbench).toContain('await this.taskStore.ensureTasks(plan.id, plan.status)')
  })

  test('opens a Task Detail with navigateTo from the focused Stop', () => {
    expect(workbench).toContain('uni.navigateTo({')
    expect(workbench).toContain('/pages/task-detail/index?id=${encodeURIComponent(String(task.id))}&planId=')
  })

  test('preserves a Free Exploration fallback for plans without route provenance', () => {
    expect(workbench).toContain('!validId(plan.routeStopId)')
    expect(workbench).toContain('自由探索')
  })

  test('reduces the tabbar to four destinations and makes Explore the workbench', () => {
    const expectedTabs = [
      "{ key: 'home', label: '首页', icon: 'home', path: '/pages/home/index' }",
      "{ key: 'explore', label: '探索', icon: 'explore', path: '/pages/explore/index' }",
      "{ key: 'record', label: '记录', icon: 'record', path: '/pages/record/index' }",
      "{ key: 'profile', label: '我的', icon: 'profile', path: '/pages/profile/index' }",
    ]
    for (const tab of expectedTabs) {
      expect(tabbar).toContain(tab)
    }
    expect(tabbar).not.toContain("key: 'route'")
    expect(tabbar).not.toContain("path: '/pages/route/index'")
  })

})
