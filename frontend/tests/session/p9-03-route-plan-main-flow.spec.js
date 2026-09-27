import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test, vi } from 'vitest'

const workspaceRoot = resolve(process.cwd(), '..')
const frontendFile = (...segments) => resolve(workspaceRoot, 'frontend', ...segments)

const homeSource = readFileSync(frontendFile('src', 'pages', 'home', 'index.vue'), 'utf8')
const routeDetailSource = readFileSync(frontendFile('src', 'pages', 'route-detail', 'index.vue'), 'utf8')
const routesApiSource = readFileSync(frontendFile('src', 'api', 'routes.js'), 'utf8')

function blockSource(source, tag) {
  const match = source.match(new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`))
  expect(match).toBeTruthy()
  return match[1]
}

function pageMethod(source, name) {
  const match = source.match(new RegExp(`(?:async )?${name}\\(([^)]*)\\) \\{[\\s\\S]*?\\n    \\},`))
  if (!match) throw new Error(`Missing ${name} method`)
  const matchedSource = match[0]
  const functionSource = matchedSource
    .replace(
      matchedSource.startsWith(`async ${name}(`) ? `async ${name}(` : `${name}(`,
      matchedSource.startsWith(`async ${name}(`) ? `async function ${name}(` : `function ${name}(`,
    )
    .replace(/,\s*$/, '')
  return Function(`return (${functionSource})`)()
}

const homeTemplate = blockSource(homeSource, 'template')
const homeScript = blockSource(homeSource, 'script')
const submitPlanGeneration = pageMethod(routeDetailSource, 'submitPlanGeneration')

describe('P9-03 Route to ExplorationPlan main user flow', () => {
  test('Home Hero routes parents into Route planning without a manual Plan creation path', () => {
    expect(homeTemplate).toContain('class="home-hero__cta" @click="goToRoutePlanning"')
    expect(homeTemplate).toContain('规划亲子路线')
    expect(homeScript).toContain("uni.reLaunch({ url: '/pages/route/index' })")
    expect(homeScript).not.toContain('usePlanStore')
    expect(homeScript).not.toContain('createPlan(')
    expect(homeScript).not.toContain('planSheetOpen')
    expect(homeScript).not.toContain('planForm')
    expect(homeTemplate).not.toContain('class="plan-sheet"')
  })

  test('Home first feature card is Route planning and opens the Route page', () => {
    expect(homeScript).toContain("title: '路线规划'")
    expect(homeScript).toContain("desc: '安排景点与行程'")
    expect(homeScript).toContain("path: '/pages/route/index'")
    expect(homeScript).not.toContain("path: '/pages/plan/index'")
  })

  test('Route Detail keeps the sealed generation endpoint and exact Child plus RouteStop payload', async () => {
    expect(routesApiSource).toContain('path: `/routes/${routeId}/exploration-plans/generate`')
    expect(routesApiSource).toContain('data: { childId, routeStopIds }')

    const context = {
      currentRoute: { id: 901 },
      selectedChildId: 102,
      selectedRouteStopIds: [81, 82],
      hasSubmittedGeneration: false,
      planGenerationError: '',
      canSubmitPlanGeneration: true,
      routeStore: {
        isGeneratingPlans: false,
        generateExplorationPlans: vi.fn().mockResolvedValue({ results: [] }),
      },
    }

    await submitPlanGeneration.call(context)

    expect(context.routeStore.generateExplorationPlans).toHaveBeenCalledWith(901, 102, [81, 82])
    expect(context.hasSubmittedGeneration).toBe(true)
  })

  test('the generation result keeps its created or existing detail and offers an explicit Explore entry', () => {
    expect(routeDetailSource).toContain('探索计划已准备好')
    expect(routeDetailSource).toContain('generationDisplayResults')
    expect(routeDetailSource).toContain("created: '已生成'")
    expect(routeDetailSource).toContain("existing: '已存在'")
    expect(routeDetailSource).toContain('查看探索计划')
    expect(routeDetailSource).toContain('@click="openGeneratedPlans"')
  })

  test('the result CTA reLaunches only when the parent chooses to view ExplorationPlans', () => {
    const openGeneratedPlans = pageMethod(routeDetailSource, 'openGeneratedPlans')
    const originalUni = globalThis.uni
    const reLaunch = vi.fn()
    globalThis.uni = { reLaunch }
    try {
      openGeneratedPlans.call({})
      expect(reLaunch).toHaveBeenCalledWith({ url: '/pages/plan/index' })
    } finally {
      globalThis.uni = originalUni
    }
  })
})
