import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const root = resolve(process.cwd(), '..')
const taskDetailSource = readFileSync(resolve(root, 'frontend/src/pages/task-detail/index.vue'), 'utf8')

describe('FE-R3 Task Detail correction contract', () => {
  test('keeps the FE-R2 State A editing baseline for an active Plan', () => {
    expect(taskDetailSource).toMatch(
      /canEditNote\(\)[\s\S]*?currentPlan\?\.status\s*===\s*['"]in-progress['"][\s\S]*?!this\.isTaskNotStarted/,
    )
    expect(taskDetailSource).toMatch(
      /canChooseImage\(\)[\s\S]*?currentPlan\?\.status\s*===\s*['"]in-progress['"][\s\S]*?!this\.isTaskNotStarted/,
    )
  })

  test('makes a completed Plan editable only while its JourneyRecord is missing or draft', () => {
    expect(taskDetailSource).toContain('correctionRecordStatusForPlan')
    expect(taskDetailSource).toMatch(/canEditNote\(\)[\s\S]*?correctionRecordStatus[\s\S]*?finalized/)
    expect(taskDetailSource).toMatch(/canChooseImage\(\)[\s\S]*?correctionRecordStatus[\s\S]*?finalized/)
  })

  test('renders the finalized read-only explanation and keeps loading or error states read-only with retry', () => {
    expect(taskDetailSource).toContain('这次成长记录已封存，任务记录不可再修改')
    expect(taskDetailSource).toContain('retryJourneyRecordCorrectionStatus')
    expect(taskDetailSource).toMatch(/correctionRecordStatus[\s\S]*?loading[\s\S]*?canEditNote/)
    expect(taskDetailSource).toMatch(/correctionRecordStatus[\s\S]*?error[\s\S]*?canChooseImage/)
  })

  test('uses a status probe rather than detail loading, record creation, or a correction completion path', () => {
    expect(taskDetailSource).toContain('loadJourneyRecordCorrectionStatus')
    expect(taskDetailSource).not.toContain('loadJourneyRecordDetail(')
    expect(taskDetailSource).not.toContain('completeCorrection')
    expect(taskDetailSource).not.toContain('finalizeJourneyRecord(')
  })

  test('locks finalization races so stale note or image writes cannot restore editable UI', () => {
    expect(taskDetailSource).toContain('markJourneyRecordCorrectionFinalized')
    expect(taskDetailSource).toMatch(/saveNoteNow[\s\S]*?correctionRecordStatus[\s\S]*?finalized/)
    expect(taskDetailSource).toMatch(/uploadTaskImage[\s\S]*?correctionRecordStatus[\s\S]*?finalized/)
  })
})
