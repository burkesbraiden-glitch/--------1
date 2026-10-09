import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const root = resolve(process.cwd(), '..')
const recordPageSource = readFileSync(resolve(root, 'frontend/src/pages/record/index.vue'), 'utf8')

describe('P9-04 JourneyRecord card information hierarchy', () => {
  test('shows a genuine cover image only when the Record Store downloaded one', () => {
    expect(recordPageSource).toContain('v-if="record.displayCoverImage"')
    expect(recordPageSource).toContain('class="record-card__media-placeholder"')
    expect(recordPageSource).not.toContain('PolaroidCard')
    expect(recordPageSource).not.toContain('recordWatercolorFallback')
  })

  test('keeps route context, real date, progress, and optional artifacts in the information body', () => {
    expect(recordPageSource).toContain('recordRouteLabel(record)')
    expect(recordPageSource).toContain('{{ record.recordDateLabel }}')
    expect(recordPageSource).toContain('{{ taskProgressText(record) }}')
    expect(recordPageSource).toContain('taskCompletionWidth(record)')
    expect(recordPageSource).toContain('v-if="record.photoCount"')
    expect(recordPageSource).toContain('v-if="record.noteCount"')
  })

  test('keeps active-child filtering and explicit Record detail navigation without status jargon', () => {
    expect(recordPageSource).toContain('childId: this.childStore.activeChild.id')
    expect(recordPageSource).toContain('url: `/pages/record-detail/index?planId=${planId}`')
    expect(recordPageSource).not.toContain('{{ record.id }}')
    expect(recordPageSource).not.toContain('{{ record.planId }}')
    expect(recordPageSource).not.toContain('recordStatusText')
  })
})
