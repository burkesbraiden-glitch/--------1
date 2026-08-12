import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const root = resolve(process.cwd(), '..')
const taskDetailSource = readFileSync(resolve(root, 'frontend/src/pages/task-detail/index.vue'), 'utf8')
const recordStoreSource = readFileSync(resolve(root, 'frontend/src/stores/record.js'), 'utf8')

function correctionPathSource(marker) {
  const markerIndex = taskDetailSource.indexOf(marker)
  expect(markerIndex).toBeGreaterThanOrEqual(0)
  const methodStart = taskDetailSource.lastIndexOf('\n    ', markerIndex)
  const methodEnd = taskDetailSource.indexOf('\n    },', markerIndex)

  expect(methodStart).toBeGreaterThanOrEqual(0)
  expect(methodEnd).toBeGreaterThan(markerIndex)
  return taskDetailSource.slice(methodStart, methodEnd)
}

describe('FE-R3 page ownership contract', () => {
  test('preserves FE-R2 recovery while keeping FE-R3 correction status on the Record Store boundary', () => {
    expect(taskDetailSource).toMatch(/import\s*\{\s*useRecordStore\s*\}\s*from\s*['"]\.\.\/\.\.\/stores\/record['"]/,)
    expect(taskDetailSource).not.toMatch(/from\s*['"]\.\.\/\.\.\/api\/journeyRecords['"]/)
    expect(taskDetailSource).toContain('ensureJourneyRecordAfterTaskCompletion')
    expect(taskDetailSource).toContain('this.recordStore.ensureJourneyRecord(validPlanId)')
    expect(taskDetailSource).toContain('this.recordStore.loadJourneyRecordCorrectionStatus')
    expect(taskDetailSource).toContain('this.recordStore.retryJourneyRecordCorrectionStatus')
  })

  test('limits correction status probe and retry paths to lightweight Record Store APIs', () => {
    const probeSource = correctionPathSource('this.recordStore.loadJourneyRecordCorrectionStatus')
    const retrySource = correctionPathSource('this.recordStore.retryJourneyRecordCorrectionStatus')

    for (const source of [probeSource, retrySource]) {
      expect(source).not.toContain('ensureJourneyRecord(')
      expect(source).not.toContain('loadJourneyRecordDetail(')
      expect(source).not.toContain('completeTaskSubmission(')
      expect(source).not.toContain('completeExploration(')
    }
  })

  test('keeps correction request ownership and invalidation in Record Store', () => {
    expect(recordStoreSource).toContain('loadJourneyRecordCorrectionStatus')
    expect(recordStoreSource).toContain('retryJourneyRecordCorrectionStatus')
    expect(recordStoreSource).toContain('markJourneyRecordCorrectionFinalized')
    expect(recordStoreSource).toContain('resetRecordState')
  })
})
