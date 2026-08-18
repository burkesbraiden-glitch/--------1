import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const workspaceRoot = resolve(process.cwd(), '..')
const routeDetailPath = resolve(workspaceRoot, 'frontend', 'src', 'pages', 'route-detail', 'index.vue')
const packagePath = resolve(workspaceRoot, 'frontend', 'package.json')

describe('P7D-6 Route and Stop reorder contracts', () => {
  test('keeps Day ordering in page-local edit state and submits a temporary adjacent-swap id list', () => {
    const source = readFileSync(routeDetailPath, 'utf8')

    expect(source).toContain('isDayOrderEditing')
    expect(source).toContain('isReorderingDays')
    expect(source).toContain('调整天数顺序')
    expect(source).toContain('moveDay(day.id, -1)')
    expect(source).toContain('moveDay(day.id, 1)')
    expect(source).toContain('const dayIds = this.currentRoute.days.map((day) => day.id)')
    expect(source).toContain('routeStore.reorderDays(this.routeId, dayIds)')
    expect(source).toContain('currentRoute.days.indexOf(day) === 0')
    expect(source).toContain('currentRoute.days.indexOf(day) === currentRoute.days.length - 1')
    expect(source).not.toContain('currentRoute.days.splice')
    expect(source).not.toContain('currentRoute.days =')
    expect(source).not.toContain('day.dayNumber =')
    expect(source).toContain("await this.handleRequestError(error, 'mutationError')")
    expect(source).toContain('isAuthenticationError(error)')
    expect(source).toContain('await endUserSession()')
  })

  test('keeps Stop ordering within one Day and submits a temporary adjacent-swap id list', () => {
    const source = readFileSync(routeDetailPath, 'utf8')

    expect(source).toContain('stopOrderDayId')
    expect(source).toContain('reorderingStopsDayId')
    expect(source).toContain('day.stops.length > 1')
    expect(source).toContain('调整景点顺序')
    expect(source).toContain('moveStop(day, stop.id, -1)')
    expect(source).toContain('moveStop(day, stop.id, 1)')
    expect(source).toContain('const stopIds = day.stops.map((stop) => stop.id)')
    expect(source).toContain('routeStore.reorderStops(this.routeId, day.id, stopIds)')
    expect(source).toContain('day.stops.indexOf(stop) === 0')
    expect(source).toContain('day.stops.indexOf(stop) === day.stops.length - 1')
    expect(source).not.toContain('day.stops.splice')
    expect(source).not.toContain('day.stops =')
    expect(source).not.toContain('stop.sortOrder =')
    expect(source).not.toContain('移动到第')
    expect(source).not.toContain('draggable=')
    expect(source).not.toContain('dragstart')
  })

  test('preserves the existing Route edit and Stop CRUD responsibilities', () => {
    const source = readFileSync(routeDetailPath, 'utf8')

    expect(source).toContain('routeStore.updateRoute')
    expect(source).toContain("routeStore.updateRoute(this.routeId, { status: 'ready' })")
    expect(source).toContain('routeStore.deleteRoute')
    expect(source).toContain('routeStore.createStop')
    expect(source).toContain('routeStore.updateStop')
    expect(source).toContain('routeStore.deleteStop')
    expect(source).toContain('routeStore.createDay')
    expect(source).toContain('routeStore.updateDay')
    expect(source).toContain('routeStore.deleteDay')
    expect(source).toContain('currentRoute() { return this.routeStore.currentRoute }')
    expect(source).not.toContain('usePlanStore')
    expect(source).not.toContain('useTaskStore')
    expect(source).not.toContain('useGuideStore')
    expect(source).not.toContain('useRecordStore')

    const packageJson = readFileSync(packagePath, 'utf8')
    expect(packageJson).not.toContain('sortablejs')
    expect(packageJson).not.toContain('vuedraggable')
    expect(packageJson).not.toContain('dragula')
  })
})
