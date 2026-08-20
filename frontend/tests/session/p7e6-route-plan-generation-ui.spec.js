import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const workspaceRoot = resolve(process.cwd(), '..')
const routeDetailPath = resolve(workspaceRoot, 'frontend', 'src', 'pages', 'route-detail', 'index.vue')
const source = readFileSync(routeDetailPath, 'utf8')
const generationSubmitSource = source.match(/async submitPlanGeneration\(\) \{[\s\S]*?\n    \},\n    async submitRouteEdit/)?.[0] || ''

describe('P7E-6 Route Detail exploration-plan generation UI', () => {
  test('places an exploration-plan section and sheet between route actions and daily notes', () => {
    expect(source).toContain('探索计划')
    expect(source).toContain('showPlanGenerationSheet')
    expect(source.indexOf('ROUTE ACTIONS')).toBeLessThan(source.indexOf('探索计划'))
    expect(source.indexOf('探索计划')).toBeLessThan(source.indexOf('DAILY NOTES'))
  })

  test('uses only real Child data and preselects the real current Child', () => {
    expect(source).toContain("from '../../stores/child'")
    expect(source).toContain('childStore.children')
    expect(source).toContain('childStore.currentChild?.id')
    expect(source).toContain('hasRealChildren')
    expect(source).toContain('selectedChildId')
    expect(source).not.toContain('FALLBACK_CHILD')
  })

  test('selects RouteStops grouped by their RouteDay and keeps repeated Attractions separate', () => {
    expect(source).toContain('generationDays')
    expect(source).toContain('currentRoute.days')
    expect(source).toContain('day.stops')
    expect(source).toContain(':key="stop.id"')
    expect(source).toContain('selectedRouteStopIds')
    expect(source).toContain('toggleRouteStopSelection(stop.id)')
    expect(source).toContain('selectAllRouteStops')
    expect(source).toContain('clearRouteStopSelection')
  })

  test('gates generation on ready routes, a real Child, selected RouteStops, and in-flight work', () => {
    expect(source).toContain("currentRoute?.status === 'ready'")
    expect(source).toContain('请先完成路线安排，并标记为“已准备”。')
    expect(source).toContain('canSubmitPlanGeneration')
    expect(source).toContain('routeStore.isGeneratingPlans')
    expect(source).toContain('if (this.routeStore.isGeneratingPlans) return')
  })

  test('submits explicit RouteStop and Child identifiers only through Route Store', () => {
    expect(source).toContain('routeStore.generateExplorationPlans(\n          this.currentRoute.id,\n          this.selectedChildId,\n          this.selectedRouteStopIds,')
    expect(source).not.toContain('routesApi.generateRouteExplorationPlans')
    expect(source).not.toContain('usePlanStore')
    expect(source).not.toContain('useTaskStore')
    expect(generationSubmitSource).not.toContain('attractionId')
  })

  test('shows only this sheet run results in backend order without automatic navigation', () => {
    expect(source).toContain('hasSubmittedGeneration')
    expect(source).toContain('generationDisplayResults')
    expect(source).toContain("created: '已生成'")
    expect(source).toContain("existing: '已存在'")
    expect(source).toContain('result.routeStopId')
    expect(source).not.toContain("/pages/plan/index")
    expect(source).not.toContain("/pages/explore/index")
  })

  test('preserves authenticated session handling and reports business failures', () => {
    expect(source).toContain('isAuthenticationError(error)')
    expect(source).toContain('endUserSession()')
    expect(source).toContain('planGenerationError')
    expect(source).toContain("error?.message || '操作失败，请稍后重试'")
  })
})
