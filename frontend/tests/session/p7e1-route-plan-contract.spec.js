import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const workspaceRoot = resolve(process.cwd(), '..')
const frontendFile = (...segments) => resolve(workspaceRoot, 'frontend', ...segments)
const backendFile = (...segments) => resolve(workspaceRoot, 'backend', ...segments)

const routeDetailSource = readFileSync(frontendFile('src', 'pages', 'route-detail', 'index.vue'), 'utf8')
const planPageSource = readFileSync(frontendFile('src', 'pages', 'plan', 'index.vue'), 'utf8')
const planModelSource = readFileSync(backendFile('app', 'models', 'exploration_plan.py'), 'utf8')
const routeModelSource = readFileSync(backendFile('app', 'models', 'route.py'), 'utf8')
const routeStopModelSource = readFileSync(backendFile('app', 'models', 'route_stop.py'), 'utf8')
const taskApiSource = readFileSync(backendFile('app', 'api', 'v1', 'tasks.py'), 'utf8')
const guideApiSource = readFileSync(backendFile('app', 'api', 'v1', 'guides.py'), 'utf8')
const recordModelSource = readFileSync(backendFile('app', 'models', 'journey_record.py'), 'utf8')
const pagesConfigSource = readFileSync(frontendFile('src', 'pages.json'), 'utf8')

const futureContract = Object.freeze({
  generationUnit: 'RouteStop × Child',
  relationship: 'ExplorationPlan.route_stop_id nullable FK route_stops.id',
  idempotencyKey: ['route_stop_id', 'child_id'],
  manualPlanNullSource: true,
  explicitChildRequired: true,
  currentChildPrefillOnly: true,
  routeReadyRequired: true,
  sourceSnapshotRequired: true,
  generatedPlanRouteSync: 'snapshot-no-auto-sync',
  routeStopDeletePolicy: 'RESTRICT',
  routeDayDeletePolicy: 'RESTRICT',
  routeDeletePolicy: 'RESTRICT',
  taskAutoGeneration: false,
  guideAutoGeneration: false,
  exploreCenterImplemented: false,
  journeyRecordV2Implemented: false,
  attractionPicker: {
    object: 'Attraction',
    multiSelect: true,
    selectAll: true,
    deselectAll: true,
    selectedCount: true,
    cardSelect: true,
    dragReorder: true,
    finalUpDownButtons: false,
    selectedTheme: 'tonglvji-warm-orange-cream',
    unselectedTheme: 'tonglvji-beige-soft-brown',
  },
  planGenerationSelectionObject: 'RouteStop',
  temporalContractRule: 'P7D-6 no-drag-drop is historical, not permanent',
  endpoint: 'POST /api/v1/routes/{routeId}/exploration-plans/generate',
  request: { childId: 'required', routeStopIds: 'required-array' },
  batchResultPerRouteStop: true,
})

describe('P7E-1 Route to ExplorationPlan relationship contract', () => {
  test('records the P7E-2A ORM boundary without claiming generation implementation', () => {
    expect(routeModelSource).not.toContain('child_id')
    expect(planModelSource).toContain('route_stop_id')
    expect(planModelSource).toContain('source_snapshot')
    expect(routeDetailSource).not.toContain('usePlanStore')
    expect(planPageSource).not.toContain('useRouteStore')
  })

  test('locks the future RouteStop by Child generation contract', () => {
    expect(futureContract.generationUnit).toBe('RouteStop × Child')
    expect(futureContract.relationship).toBe('ExplorationPlan.route_stop_id nullable FK route_stops.id')
    expect(futureContract.idempotencyKey).toEqual(['route_stop_id', 'child_id'])
    expect(futureContract.manualPlanNullSource).toBe(true)
    expect(futureContract.explicitChildRequired).toBe(true)
    expect(futureContract.currentChildPrefillOnly).toBe(true)
    expect(futureContract.routeReadyRequired).toBe(true)
    expect(futureContract.sourceSnapshotRequired).toBe(true)
    expect(futureContract.generatedPlanRouteSync).toBe('snapshot-no-auto-sync')
    expect(futureContract.routeStopDeletePolicy).toBe('RESTRICT')
    expect(futureContract.routeDayDeletePolicy).toBe('RESTRICT')
    expect(futureContract.routeDeletePolicy).toBe('RESTRICT')
  })

  test('keeps deferred task, guide, record, Explore Center, and picker boundaries explicit', () => {
    expect(taskApiSource).toContain('/<int:plan_id>/tasks/generate')
    expect(guideApiSource).toContain('/<int:plan_id>/guide/generate')
    expect(recordModelSource).not.toContain('route_snapshot')
    expect(pagesConfigSource).not.toContain('pages/explore/index')
    expect(routeStopModelSource).toContain('attraction_id')
    expect(futureContract.taskAutoGeneration).toBe(false)
    expect(futureContract.guideAutoGeneration).toBe(false)
    expect(futureContract.exploreCenterImplemented).toBe(false)
    expect(futureContract.journeyRecordV2Implemented).toBe(false)
    expect(futureContract.attractionPicker).toEqual({
      object: 'Attraction',
      multiSelect: true,
      selectAll: true,
      deselectAll: true,
      selectedCount: true,
      cardSelect: true,
      dragReorder: true,
      finalUpDownButtons: false,
      selectedTheme: 'tonglvji-warm-orange-cream',
      unselectedTheme: 'tonglvji-beige-soft-brown',
    })
    expect(futureContract.planGenerationSelectionObject).toBe('RouteStop')
    expect(futureContract.temporalContractRule).toBe('P7D-6 no-drag-drop is historical, not permanent')
  })

  test('locks the future batch API direction without adding it to production', () => {
    expect(futureContract.endpoint).toBe('POST /api/v1/routes/{routeId}/exploration-plans/generate')
    expect(futureContract.request).toEqual({ childId: 'required', routeStopIds: 'required-array' })
    expect(futureContract.batchResultPerRouteStop).toBe(true)
    expect(routeDetailSource).not.toContain('exploration-plans/generate')
  })
})
