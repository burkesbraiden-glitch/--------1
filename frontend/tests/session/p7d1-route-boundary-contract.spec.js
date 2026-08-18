import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const root = resolve(process.cwd(), '..')
const frontendFile = (path) => resolve(root, 'frontend', path)
const readFrontendFile = (path) => readFileSync(frontendFile(path), 'utf8')

const planPageSource = readFrontendFile('src/pages/plan/index.vue')
const planStoreSource = readFrontendFile('src/stores/plan.js')
const taskStoreSource = readFrontendFile('src/stores/task.js')
const guideStoreSource = readFrontendFile('src/stores/guide.js')
const recordStoreSource = readFrontendFile('src/stores/record.js')
const recordJourneySource = readFrontendFile('src/stores/recordJourney.mjs')
const pagesConfigSource = readFrontendFile('src/pages.json')
const tabbarSource = readFrontendFile('src/components/AppTabbar.vue')

function expectNoRouteDomainCoupling(source) {
  expect(source).not.toMatch(/\buseRouteStore\b/)
  expect(source).not.toMatch(/from\s*['"][^'"]*(?:stores\/route|api\/routes)(?:\.js)?['"]/)
}

describe('P7D-1 Route and navigation boundary contract', () => {
  test('keeps the Plan page in the ExplorationPlan domain', () => {
    expect(planPageSource).toMatch(/import\s*\{\s*usePlanStore\s*\}\s*from\s*['"][^'"]*stores\/plan['"]/)
    expect(planPageSource).toMatch(/import\s*\{\s*useTaskStore\s*\}\s*from\s*['"][^'"]*stores\/task['"]/)
    expect(planPageSource).toContain('ensureCurrentPlanReady')
    expect(planPageSource).toContain('startExploration')
    expect(planPageSource).toContain('/pages/tasks/index')
    expectNoRouteDomainCoupling(planPageSource)
  })

  test('keeps the Plan Store responsible for ExplorationPlan state only', () => {
    expect(planStoreSource).toContain("import * as plansApi from '../api/plans.js'")
    expect(planStoreSource).toContain("defineStore('plan'")
    expect(planStoreSource).toContain('currentPlan')
    expectNoRouteDomainCoupling(planStoreSource)
  })

  test('keeps the Task Store coupled to ExplorationPlan rather than Route', () => {
    expect(taskStoreSource).toMatch(/import\s*\{\s*usePlanStore\s*\}\s*from\s*['"]\.\/plan\.js['"]/)
    expect(taskStoreSource).toContain('currentPlanId')
    expectNoRouteDomainCoupling(taskStoreSource)
  })

  test('keeps the Guide Store on the ExplorationPlan GuideCard boundary', () => {
    expect(guideStoreSource).toContain("import * as guidesApi from '../api/guides.js'")
    expect(guideStoreSource).toContain('loadedForPlanId')
    expect(guideStoreSource).toContain('ensureGuide(planId)')
    expectNoRouteDomainCoupling(guideStoreSource)
  })

  test('keeps JourneyRecord free of Route v2 coupling and snapshots', () => {
    for (const source of [recordStoreSource, recordJourneySource]) {
      expectNoRouteDomainCoupling(source)
      expect(source).not.toMatch(/\brouteSnapshotV2\b/)
      expect(source).not.toMatch(/\brouteSnapshot\b/)
    }
  })

  test('keeps legacy ExplorationPlan flow pages registered', () => {
    for (const path of [
      'pages/plan/index',
      'pages/guide/index',
      'pages/tasks/index',
      'pages/task-detail/index',
    ]) {
      expect(pagesConfigSource).toContain(path)
    }
  })

  test('preserves the profile tab authentication split without locking navigation keys', () => {
    expect(tabbarSource).toContain("item.key === 'profile'")
    expect(tabbarSource).toContain('restoreSession')
    expect(tabbarSource).toContain('userStore.isLoggedIn')
    expect(tabbarSource).toContain('/pages/profile/index')
    expect(tabbarSource).toContain('/pages/login/index')
    expect(tabbarSource).toContain('uni.reLaunch({')
  })

  test('keeps current ExplorationPlan domain pages present with their existing responsibilities', () => {
    const pageContracts = [
      ['src/pages/plan/index.vue', planPageSource, 'usePlanStore'],
      ['src/pages/guide/index.vue', readFrontendFile('src/pages/guide/index.vue'), 'useGuideStore'],
      ['src/pages/tasks/index.vue', readFrontendFile('src/pages/tasks/index.vue'), 'useTaskStore'],
      ['src/pages/task-detail/index.vue', readFrontendFile('src/pages/task-detail/index.vue'), 'useTaskStore'],
    ]

    for (const [path, source, responsibility] of pageContracts) {
      expect(existsSync(frontendFile(path))).toBe(true)
      expect(source).toContain(responsibility)
    }
  })
})
