import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const root = resolve(process.cwd(), '..')
const readFrontendFile = (path) => readFileSync(resolve(root, 'frontend', path), 'utf8')
const homeSource = readFrontendFile('src/pages/home/index.vue')
const plansApiSource = readFrontendFile('src/api/plans.js')

function blockSource(source, tag) {
  const match = source.match(new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`))
  expect(match).toBeTruthy()
  return match[1]
}

const templateSource = blockSource(homeSource, 'template')
const scriptSource = blockSource(homeSource, 'script')
const audioGuideSource = scriptSource.match(/async openAudioGuide\(\) \{[\s\S]*?\n    \},/)?.[0] || ''

describe('P8.4C Home truthful production copy', () => {
  test('Home production template contains no Mock, simulated, test-data, or demo-data copy', () => {
    for (const forbiddenCopy of ['Mock', '模拟', '测试数据', '演示数据']) {
      expect(templateSource).not.toContain(forbiddenCopy)
    }
  })

  test('the create-plan button retains the existing real API action', () => {
    expect(templateSource).toContain('class="plan-sheet__submit" @click="submitPlan"')
    expect(scriptSource).toContain('async submitPlan()')
    expect(scriptSource).toContain('await this.child.fetchChildren(this.user.userInfo.id)')
    expect(scriptSource).toContain('await this.plan.createPlan(')
    expect(plansApiSource).toContain("path: '/plans'")
    expect(plansApiSource).toContain("method: 'POST'")
    expect(plansApiSource).toContain('auth: true')
  })

  test('Home introduces no fake-data fallback into its production creation path', () => {
    expect(scriptSource).not.toMatch(/(?:from|require|import\()[^\n]*mock/i)
    expect(scriptSource).not.toContain('mockRecords')
    expect(scriptSource).not.toContain('FALLBACK_CHILD')
  })

  test('the existing active-child and Plan empty-or-error guards remain intact', () => {
    expect(scriptSource).toContain('const activeChild = this.child.activeChild')
    expect(scriptSource).toContain('childId: activeChild.id')
    expect(audioGuideSource).toContain('result.currentPlan?.id !== null')
    expect(audioGuideSource).toContain('this.audioGuidePlanId = null')
    expect(audioGuideSource).toContain('this.audioGuideOpen = false')
    expect(audioGuideSource).toContain("this.showToast('探索计划加载失败，请重试')")
  })
})
