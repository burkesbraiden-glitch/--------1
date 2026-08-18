import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const workspaceRoot = resolve(process.cwd(), '..')
const frontendPath = (...parts) => resolve(workspaceRoot, 'frontend', ...parts)
const sourceOf = (...parts) => readFileSync(frontendPath(...parts), 'utf8')

describe('P7D-7 atomic navigation migration contracts', () => {
  test('exposes exactly the Route and Explore business tabs while preserving Tabbar navigation guards', () => {
    const source = sourceOf('src', 'components', 'AppTabbar.vue')

    expect(source).toContain("{ key: 'home', label: '首页', icon: 'home', path: '/pages/home/index' }")
    expect(source).toContain("{ key: 'route', label: '路线', icon: 'plan', path: '/pages/route/index' }")
    expect(source).toContain("{ key: 'explore', label: '探索', icon: 'tasks', path: '/pages/plan/index' }")
    expect(source).toContain("{ key: 'record', label: '记录', icon: 'record', path: '/pages/record/index' }")
    expect(source).toContain("{ key: 'profile', label: '我的', icon: 'profile', path: '/pages/profile/index' }")
    expect(source).not.toMatch(/\{\s*key:\s*'plan'/)
    expect(source).not.toMatch(/\{\s*key:\s*'tasks'/)
    expect(source).toContain('if (this.active === item.key)')
    expect(source).toContain("if (item.key === 'profile')")
    expect(source).toContain('await userStore.restoreSession()')
    expect(source).toContain("'/pages/profile/index' : '/pages/login/index'")
    expect(source).toContain('uni.reLaunch')
  })

  test('assigns Route and Explore active states without changing compatible page paths or domains', () => {
    const routeList = sourceOf('src', 'pages', 'route', 'index.vue')
    const routeDetail = sourceOf('src', 'pages', 'route-detail', 'index.vue')
    const plan = sourceOf('src', 'pages', 'plan', 'index.vue')
    const guide = sourceOf('src', 'pages', 'guide', 'index.vue')
    const tasks = sourceOf('src', 'pages', 'tasks', 'index.vue')
    const taskDetail = sourceOf('src', 'pages', 'task-detail', 'index.vue')

    for (const source of [routeList, routeDetail]) {
      expect(source).toContain("import AppTabbar from '../../components/AppTabbar.vue'")
      expect(source).toContain('<AppTabbar active="route" />')
      expect(source).toContain('var(--tl-tabbar-height)')
      expect(source).toContain('var(--tl-safe-bottom)')
    }
    for (const source of [plan, guide, tasks, taskDetail]) {
      expect(source).toContain('<AppTabbar active="explore" />')
    }
    expect(plan).toContain('usePlanStore')
    expect(tasks).toContain('useTaskStore')
    expect(routeList).not.toContain('usePlanStore')
    expect(routeDetail).not.toContain('usePlanStore')
  })

  test('leaves Home Record Profile and registered compatibility pages intact without an Explore Center', () => {
    expect(sourceOf('src', 'pages', 'home', 'index.vue')).toContain('<AppTabbar active="home" />')
    expect(sourceOf('src', 'pages', 'record', 'index.vue')).toContain('<AppTabbar active="record" />')
    expect(sourceOf('src', 'pages', 'profile', 'index.vue')).toContain('<AppTabbar active="profile" />')

    const pagesJson = sourceOf('src', 'pages.json')
    expect(pagesJson).toContain('pages/plan/index')
    expect(pagesJson).toContain('pages/guide/index')
    expect(pagesJson).toContain('pages/tasks/index')
    expect(pagesJson).toContain('pages/task-detail/index')
    expect(existsSync(frontendPath('src', 'pages', 'explore', 'index.vue'))).toBe(false)
  })
})
