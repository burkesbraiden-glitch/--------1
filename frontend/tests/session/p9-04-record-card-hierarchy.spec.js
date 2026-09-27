import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const root = resolve(process.cwd(), '..')
const recordPageSource = readFileSync(resolve(root, 'frontend/src/pages/record/index.vue'), 'utf8')

function polaroidUsage() {
  const match = recordPageSource.match(/<PolaroidCard[\s\S]*?\/>/)
  if (!match) {
    throw new Error('Missing JourneyRecord PolaroidCard')
  }
  return match[0]
}

describe('P9-04 JourneyRecord card information hierarchy', () => {
  test('keeps PolaroidCard as the cover photo only', () => {
    const card = polaroidUsage()

    expect(card).toContain(':image-path="record.displayCoverImage || recordWatercolorFallback"')
    expect(card).not.toContain(':title=')
    expect(card).not.toContain(':description=')
    expect(card).not.toContain(':date-label=')
  })

  test('keeps title, destination, labeled date, and one compact progress summary in the information body', () => {
    expect(recordPageSource).toContain('{{ record.displayTitle }}')
    expect(recordPageSource).toContain("{{ record.destination || '目的地待补充' }}")
    expect(recordPageSource).toContain('{{ record.displayDateLabel }}')
    expect(recordPageSource).toContain('任务 {{ record.completedTaskCount }}/{{ record.taskCount }} · 照片 {{ record.photoCount }} · 笔记 {{ record.noteCount }}')
  })

  test('preserves record status, active-child loading, and detail navigation contracts', () => {
    expect(recordPageSource).toContain("return '整理中'")
    expect(recordPageSource).toContain("return '已封存'")
    expect(recordPageSource).toContain('childId: this.childStore.activeChild.id')
    expect(recordPageSource).toContain('url: `/pages/record-detail/index?planId=${planId}`')
  })
})
