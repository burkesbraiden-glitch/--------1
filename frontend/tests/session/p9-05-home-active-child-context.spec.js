import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const root = resolve(process.cwd(), '..')
const homeSource = readFileSync(resolve(root, 'frontend/src/pages/home/index.vue'), 'utf8')

describe('P9-05 Home active-child summary context', () => {
  test('restores the user session before loading active-child Home data', () => {
    expect(homeSource).toContain('async loadHome(force = false)')
    expect(homeSource).toContain('await this.userStore.restoreSession()')
    expect(homeSource).toContain('await this.childStore.fetchChildren(userId)')
  })

  test('redirects an unauthenticated direct Home entry to Login', () => {
    expect(homeSource).toContain("if (!this.hasAuthenticatedUser) {")
    expect(homeSource).toContain("uni.reLaunch({ url: '/pages/login/index' })")
  })

  test('renders the current journey summary instead of local child management controls', () => {
    expect(homeSource).toContain('class="current-exploration"')
    expect(homeSource).toContain('继续探索')
    for (const retiredMarker of ['当前孩子', '切换孩子', '完善孩子档案', 'home-child-context', 'home-age']) {
      expect(homeSource).not.toContain(retiredMarker)
    }
  })

  test('uses only Child Store activeChild and never writes child profile data from Home', () => {
    expect(homeSource).toContain('this.childStore.activeChild')
    expect(homeSource).toContain('sameId(plan.childId, this.activeChild.id)')
    expect(homeSource).not.toContain('children[0]')
    expect(homeSource).not.toContain('currentChild.id')
    expect(homeSource).not.toContain('updateChild(')
    expect(homeSource).not.toContain('createChild(')
  })

  test('uses projected Plans without changing currentPlan or loading Task details', () => {
    expect(homeSource).toContain("this.planStore.fetchPlans(userId, { selectionPolicy: 'none' })")
    expect(homeSource).not.toContain('selectPlanById(')
    expect(homeSource).not.toContain('ensureTasks(')
    expect(homeSource).not.toContain('generateExplorationPlans(')
  })

  test('keeps Guide opening inside Explore and forwards known context there', () => {
    expect(homeSource).not.toContain('AudioGuideSheet')
    expect(homeSource).not.toContain('ensureCurrentPlanReady')
    for (const key of ['routeId', 'dayId', 'stopId', 'planId']) {
      expect(homeSource).toContain(`['${key}', context?.${key}]`)
    }
  })
})
