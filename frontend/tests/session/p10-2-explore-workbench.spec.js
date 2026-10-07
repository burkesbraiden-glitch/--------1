import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const root = resolve(process.cwd(), '..')
const frontend = (...parts) => resolve(root, 'frontend', ...parts)
const workbenchPath = frontend('src', 'pages', 'explore', 'index.vue')
const source = readFileSync(workbenchPath, 'utf8')
const tabbar = readFileSync(frontend('src', 'components', 'AppTabbar.vue'), 'utf8')
const pages = readFileSync(frontend('src', 'pages.json'), 'utf8')

describe('P10.2 Explore workbench', () => {
  test('registers a Route → Day → Stop → Plan → Task workbench', () => {
    expect(existsSync(workbenchPath)).toBe(true)
    expect(pages).toContain('pages/explore/index')
    expect(source).toContain('useRouteStore')
    expect(source).toContain('usePlanStore')
    expect(source).toContain('useTaskStore')
    expect(source).toContain('currentRoute.days')
    expect(source).toContain('currentDay.stops')
    expect(source).toContain('plan.routeStopId')
    expect(source).toContain('displayTasksForPlan')
  })

  test('keeps tasks under the focused attraction and retains Task Detail as a child page', () => {
    expect(source).toContain('class="stop-detail"')
    expect(source).toContain('class="task-list"')
    expect(source).toContain('/pages/task-detail/index?id=')
    expect(source).toContain('uni.navigateTo')
  })

  test('supports route-scoped plan generation and lazy task preparation', () => {
    expect(source).toContain('generateExplorationPlans')
    expect(source).toContain('missingPlanStopIds')
    expect(source).toContain('generateTodayPlans')
    expect(source).toContain('ensureTasks')
  })

  test('preserves manual plans as a free-exploration group', () => {
    expect(source).toContain('freePlans')
    expect(source).toContain('自由探索')
    expect(source).toContain('!hasId(plan.routeStopId)')
  })

  test('uses a four-item bottom navigation with Explore as the merged entry', () => {
    expect(tabbar).toContain("{ key: 'home', label: '首页'")
    expect(tabbar).toContain("{ key: 'explore', label: '探索', icon: 'tasks', path: '/pages/explore/index' }")
    expect(tabbar).toContain("{ key: 'record', label: '记录'")
    expect(tabbar).toContain("{ key: 'profile', label: '我的'")
    expect(tabbar).not.toContain("{ key: 'route', label: '路线'")
  })
})
