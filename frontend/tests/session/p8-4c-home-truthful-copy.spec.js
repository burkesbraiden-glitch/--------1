import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const root = resolve(process.cwd(), '..')
const readFrontendFile = (path) => readFileSync(resolve(root, 'frontend', path), 'utf8')
const homeSource = readFrontendFile('src/pages/home/index.vue')
const planStoreSource = readFrontendFile('src/stores/plan.js')
const plansApiSource = readFrontendFile('src/api/plans.js')

function blockSource(source, tag) {
  const match = source.match(new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`))
  expect(match).toBeTruthy()
  return match[1]
}

const templateSource = blockSource(homeSource, 'template')
const scriptSource = blockSource(homeSource, 'script')

describe('P8.4C Home truthful production copy', () => {
  test('Home production template contains no Mock, simulated, test-data, or demo-data copy', () => {
    for (const forbiddenCopy of ['Mock', '模拟', '测试数据', '演示数据']) {
      expect(templateSource).not.toContain(forbiddenCopy)
    }
  })

  test('the primary Home action sends parents to the Explore workbench without a manual Plan request', () => {
    expect(templateSource).toMatch(/class="current-exploration__action(?:\s+[^\"]+)?"\s+@click="openCurrentExploration"/)
    expect(scriptSource).toContain('buildExploreUrl(context = this.currentExploration)')
    expect(scriptSource).toContain("selectionPolicy: 'none'")
    expect(scriptSource).not.toContain('createPlan(')
    expect(templateSource).not.toContain('class="plan-sheet"')

    expect(planStoreSource).toContain('async createPlan(')
    expect(plansApiSource).toContain("path: '/plans'")
    expect(plansApiSource).toContain("method: 'POST'")
    expect(plansApiSource).toContain('auth: true')
  })

  test('Home introduces no fake-data fallback into its production creation path', () => {
    expect(scriptSource).not.toMatch(/(?:from|require|import\()[^\n]*mock/i)
    expect(scriptSource).not.toContain('mockRecords')
    expect(scriptSource).not.toContain('FALLBACK_CHILD')
  })

  test('Home leaves Guide loading to Explore without restoring a Home Plan form', () => {
    expect(scriptSource).not.toContain('AudioGuideSheet')
    expect(scriptSource).not.toContain('ensureCurrentPlanReady')
    expect(scriptSource).not.toContain('ensureGuide')
    expect(scriptSource).not.toContain('planForm')
    expect(scriptSource).not.toContain('FALLBACK_CHILD')
  })
})
