import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const workspaceRoot = resolve(process.cwd(), '..')
const routeDetailPath = resolve(workspaceRoot, 'frontend', 'src', 'pages', 'route-detail', 'index.vue')
const routeDetailSource = () => readFileSync(routeDetailPath, 'utf8')

describe('P7D-4 Route Detail and Day management contracts', () => {
  test('keeps Route Detail independent from exploration domains and reuses session safety', () => {
    const source = routeDetailSource()
    expect(source).toContain('useRouteStore')
    expect(source).toContain('isAuthenticationError')
    expect(source).toContain('endUserSession')
    expect(source).not.toContain('usePlanStore')
    expect(source).not.toContain('useTaskStore')
    expect(source).not.toContain('useGuideStore')
    expect(source).not.toContain('useRecordStore')
    expect(source).not.toContain('useAttraction')
  })

  test('provides validated Route editing, an explicit ready action, and confirmed deletion', () => {
    const source = routeDetailSource()
    expect(source).toContain('showRouteEditSheet')
    expect(source).toContain('routeEditForm')
    expect(source).toContain('isUpdatingRoute')
    expect(source).toContain('routeEditError')
    expect(source).toContain('routeStore.updateRoute(this.routeId, payload)')
    expect(source).toContain("status: 'ready'")
    expect(source).toContain('标记为已准备')
    expect(source).toContain('uni.showModal')
    expect(source).toContain('routeStore.deleteRoute(this.routeId)')
    expect(source).toContain("url: '/pages/route/index'")
    expect(source).toContain('结束日期不能早于开始日期')
    expect(source).not.toContain('in-progress')
    expect(source).not.toContain('completed')
  })

  test('renders server Route days and preserves server-owned day sequencing', () => {
    const source = routeDetailSource()
    expect(source).toContain('v-for="day in currentRoute.days"')
    expect(source).toContain('day.dayNumber')
    expect(source).toContain('day.date')
    expect(source).toContain('day.title')
    expect(source).toContain('+ 添加一天')
    expect(source).toContain('showDaySheet')
    expect(source).toContain('dayFormMode')
    expect(source).toContain('dayForm')
    expect(source).toContain('routeStore.createDay(this.routeId, payload)')
    expect(source).toContain('routeStore.updateDay(this.routeId, this.dayForm.id, payload)')
    expect(source).toContain('routeStore.deleteDay(this.routeId, day.id)')
    expect(source).toContain('删除第')
    expect(source).not.toContain('v-model="day.dayNumber"')
    expect(source).not.toContain('currentRoute.days.splice')
    expect(source).not.toContain('day.dayNumber = index + 1')
  })
})
