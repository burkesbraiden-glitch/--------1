import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const workspaceRoot = resolve(process.cwd(), '..')
const frontendFile = (...segments) => resolve(workspaceRoot, 'frontend', ...segments)
const planPageSource = readFileSync(frontendFile('src', 'pages', 'plan', 'index.vue'), 'utf8')

function methodSource(name) {
  return planPageSource.match(new RegExp(`async ${name}\\([^)]*\\) \\{[\\s\\S]*?\\n    \\},`))?.[0] || ''
}

describe('P7F-2 Explore Center', () => {
  test('uses the Plan list as the Explore Center data source', () => {
    expect(planPageSource).toContain('planStore.plans')
    expect(planPageSource).toContain('v-for="plan in')
  })

  test('keeps Center browsing free of Task, Guide, Route, and Record creation flows', () => {
    expect(planPageSource).not.toContain('useTaskStore')
    expect(planPageSource).not.toContain('useGuideStore')
    expect(planPageSource).not.toContain('useRouteStore')
    expect(planPageSource).not.toMatch(/\bensureTasks\b/)
    expect(planPageSource).not.toMatch(/\bgenerateTasks\b/)
    expect(planPageSource).not.toMatch(/\bensureGuide\b/)
    expect(planPageSource).not.toMatch(/\b(?:createJourneyRecord|ensureJourneyRecord)\b/)
  })

  test('recovers the Center without tasks and refreshes its Plan list whenever the tab becomes visible', () => {
    const onShowSource = planPageSource.match(/async onShow\(\) \{[\s\S]*?\n  \},/)?.[0] || ''
    const loadPlansSource = methodSource('loadPlans')

    expect(onShowSource).toContain('await this.loadPlans(true)')
    expect(loadPlansSource).toContain('ensureCurrentPlanReady({ withTasks: false, force })')
  })

  test('renders each Plan title, destination, status, progress, and route-source summary', () => {
    expect(planPageSource).toMatch(/plan\.title/)
    expect(planPageSource).toMatch(/plan\.destination/)
    expect(planPageSource).toMatch(/plan\.status/)
    expect(planPageSource).toMatch(/plan\.progress\?\.total/)
    expect(planPageSource).toMatch(/plan\.progress\?\.completed/)
    expect(planPageSource).toMatch(/plan\.sourceSnapshot\?\./)
  })

  test('renders a safe manual-Plan fallback when route provenance is null', () => {
    expect(planPageSource).toMatch(/(?:无路线来源|手工创建|手动创建)/)
    expect(planPageSource).not.toMatch(/plan\.sourceSnapshot\.(?!\?)/)
  })

  test('selects the clicked Plan by ID and navigates to an explicit Explore Detail URL', () => {
    expect(planPageSource).toContain('selectPlanById(plan.id)')
    expect(planPageSource).toMatch(/url:\s*`\/pages\/explore-detail\/index\?planId=\$\{plan\.id\}`/)
  })
})
