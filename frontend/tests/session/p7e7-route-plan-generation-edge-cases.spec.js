import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const workspaceRoot = resolve(process.cwd(), '..')
const routeDetailSource = readFileSync(resolve(workspaceRoot, 'frontend', 'src', 'pages', 'route-detail', 'index.vue'), 'utf8')
const submitSource = routeDetailSource.match(/async submitPlanGeneration\(\) \{[\s\S]*?\n    \},\n    async submitRouteEdit/)?.[0] || ''
const openSource = routeDetailSource.match(/openPlanGenerationSheet\(\) \{[\s\S]*?\n    \},\n    closePlanGenerationSheet/)?.[0] || ''

describe('P7E-7 Route Detail generation edge cases', () => {
  test('blocks duplicate and draft-state submits before calling Route Store', () => {
    expect(submitSource).toContain('if (this.routeStore.isGeneratingPlans) return')
    expect(submitSource).toContain('if (!this.canSubmitPlanGeneration) return')
    expect(routeDetailSource).toContain("isRouteReady() { return this.currentRoute?.status === 'ready' }")
  })

  test('clears a prior sheet result on reopen and never turns a failed request into success', () => {
    expect(openSource).toContain('this.hasSubmittedGeneration = false')
    expect(submitSource).toContain('this.hasSubmittedGeneration = false')
    expect(submitSource).toContain('this.hasSubmittedGeneration = true')
  })

  test('keeps separate RouteStop IDs and ordered backend results while mapping UI-only labels', () => {
    expect(routeDetailSource).toContain(':key="stop.id"')
    expect(routeDetailSource).toContain('toggleRouteStopSelection(stop.id)')
    expect(routeDetailSource).toContain('(this.routeStore.planGenerationResult?.results || []).map')
    expect(routeDetailSource).not.toContain('planGenerationResult?.results || []).sort')
    expect(routeDetailSource).toContain("created: '已生成'")
    expect(routeDetailSource).toContain("existing: '已存在'")
  })

  test('keeps authentication cleanup separate from business error display and navigation', () => {
    expect(submitSource).toContain('if (isAuthenticationError(error)) { await endUserSession(); return }')
    expect(submitSource).toContain("this.planGenerationError = error?.message || '操作失败，请稍后重试'")
    expect(submitSource).not.toContain('uni.reLaunch')
    expect(submitSource).not.toContain('uni.navigateTo')
  })
})
