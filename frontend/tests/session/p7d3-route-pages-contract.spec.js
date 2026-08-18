import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const workspaceRoot = resolve(process.cwd(), '..')
const frontendFile = (...segments) => resolve(workspaceRoot, 'frontend', ...segments)
const routeListPath = frontendFile('src', 'pages', 'route', 'index.vue')
const routeDetailPath = frontendFile('src', 'pages', 'route-detail', 'index.vue')
const pagesConfigPath = frontendFile('src', 'pages.json')

function readSource(filePath) {
  return readFileSync(filePath, 'utf8')
}

describe('P7D-3 Route page contracts', () => {
  test('registers the Route List and Route Detail pages without removing legacy pages', () => {
    expect(existsSync(routeListPath)).toBe(true)
    expect(existsSync(routeDetailPath)).toBe(true)

    if (!existsSync(routeListPath) || !existsSync(routeDetailPath)) return

    const pagesConfig = readSource(pagesConfigPath)
    expect(pagesConfig).toContain('pages/route/index')
    expect(pagesConfig).toContain('pages/route-detail/index')
    for (const legacyPage of [
      'pages/home/index',
      'pages/plan/index',
      'pages/guide/index',
      'pages/tasks/index',
      'pages/task-detail/index',
      'pages/record/index',
      'pages/record-detail/index',
      'pages/profile/index',
      'pages/login/index',
    ]) {
      expect(pagesConfig).toContain(legacyPage)
    }
  })

  test('keeps the Route List focused on real Route summaries and creation', () => {
    if (!existsSync(routeListPath)) return

    const source = readSource(routeListPath)
    expect(source).toContain("useRouteStore")
    expect(source).toContain("useUserStore")
    expect(source).toContain("restoreSession")
    expect(source).toContain("endUserSession")
    expect(source).toContain("isAuthenticationError")
    expect(source).toContain("isPageLoading")
    expect(source).toContain("routeStore.error")
    expect(source).toContain("还没有旅行路线")
    expect(source).toContain("创建第一条路线")
    expect(source).toContain("+ 新建路线")
    expect(source).toContain("route.title")
    expect(source).toContain("route.city")
    expect(source).toContain("route.startDate")
    expect(source).toContain("route.endDate")
    expect(source).toContain("route.status")
    expect(source).toContain("title")
    expect(source).toContain("city")
    expect(source).toContain("startDate")
    expect(source).toContain("endDate")
    expect(source).toContain("routeStore.createRoute")
    expect(source).toContain("pages/route-detail/index?id=")
    expect(source).not.toContain("usePlanStore")
    expect(source).not.toContain("useTaskStore")
    expect(source).not.toContain("useGuideStore")
    expect(source).not.toContain("useRecordStore")
    expect(source).not.toContain("days.length")
    expect(source).not.toContain("stops")
    expect(source).not.toContain("stopCount")
    expect(source).not.toContain("dayCount")
    expect(source).not.toContain("attractionCount")
    expect(source).not.toContain("useAttraction")
  })

  test('makes Route creation validated, protected against duplicate submits, and draft-preserving on failure', () => {
    if (!existsSync(routeListPath)) return

    const source = readSource(routeListPath)
    expect(source).toContain("if (this.isCreating) return")
    expect(source).toContain("结束日期不能早于开始日期")
    expect(source).toContain("this.formError")
    expect(source).toContain("this.closeCreateSheet()")
    expect(source).toContain("encodeURIComponent(String(createdRoute.id))")
    expect(source.indexOf('this.isCreating = false\n        this.closeCreateSheet()')).toBeGreaterThan(-1)
    expect(source).not.toMatch(/picker[^>]+status/)
  })

  test('loads a validated Route Detail through the Route Store only', () => {
    if (!existsSync(routeDetailPath)) return

    const source = readSource(routeDetailPath)
    expect(source).toContain("useRouteStore")
    expect(source).toContain("useUserStore")
    expect(source).toContain("restoreSession")
    expect(source).toContain("endUserSession")
    expect(source).toContain("isAuthenticationError")
    expect(source).toContain("routeStore.fetchRoute")
    expect(source).toContain("路线信息不存在")
    expect(source).toContain("currentRoute.days.length")
    expect(source).toContain("已安排")
    expect(source).toContain("这条路线还没有安排行程")
    expect(source).toContain("uni.navigateBack")
    expect(source).not.toContain("usePlanStore")
    expect(source).not.toContain("useTaskStore")
    expect(source).not.toContain("useGuideStore")
    expect(source).not.toContain("useRecordStore")
    expect(source).not.toContain("useAttraction")
  })
})
