import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const root = resolve(process.cwd(), '..')
const frontendFile = (...segments) => readFileSync(resolve(root, 'frontend', ...segments), 'utf8')

const recordPage = frontendFile('src', 'pages', 'record', 'index.vue')
const recordDetail = frontendFile('src', 'pages', 'record-detail', 'index.vue')
const explorePage = frontendFile('src', 'pages', 'explore', 'index.vue')
const homePage = frontendFile('src', 'pages', 'home', 'index.vue')
const tabbar = frontendFile('src', 'components', 'AppTabbar.vue')

describe('P10.4 record review experience', () => {
  test('loads existing records only for the active child and never creates records from the list page', () => {
    expect(recordPage).toContain('childId: this.childStore.activeChild.id')
    expect(recordPage).toContain('this.recordStore.loadJourneyRecords')
    expect(recordPage).not.toContain('ensureJourneyRecord(')
    expect(recordPage).not.toContain('createJourneyRecord(')
  })

  test('separates loading, error, no-child, and empty states while sending the empty CTA to Explore', () => {
    for (const state of ['isChildLoading', 'showChildError', 'showNoChild', 'isInitialLoading', 'showFullError', 'isEmpty']) {
      expect(recordPage).toContain(state)
    }
    expect(recordPage).toContain('还没有留下探索记录')
    expect(recordPage).toContain('完成一次探索后，这里会保存孩子的任务、照片和发现。')
    expect(recordPage).toContain("url: '/pages/explore/index'")
  })

  test('uses the requested Record heading and groups real cards by date without technical identifiers', () => {
    expect(recordPage).toContain('>探索记录</text>')
    expect(recordPage).toContain('记录孩子的每一次探索与成长')
    expect(recordPage).toContain('recordsByYear')
    expect(recordPage).toContain('recordYear')
    expect(recordPage).toContain('recordDateLabel')
    expect(recordPage).not.toContain('{{ record.id }}')
    expect(recordPage).not.toContain('{{ record.planId }}')
  })

  test('uses only real photos and real counts on a card, with a low-key non-image fallback', () => {
    expect(recordPage).toContain('v-if="record.displayCoverImage"')
    expect(recordPage).toContain('record-card__media-placeholder')
    expect(recordPage).toContain('record-card__progress-track')
    expect(recordPage).toContain('taskCompletionWidth(record)')
    expect(recordPage).toContain('record-card__stats')
    expect(recordPage).not.toContain('recordWatercolorFallback')
    expect(recordPage).toContain('v-if="record.photoCount"')
    expect(recordPage).toContain('v-if="record.noteCount"')
  })

  test('opens a read-only detail via navigateTo and returns with navigateBack', () => {
    expect(recordPage).toContain('uni.navigateTo({')
    expect(recordPage).toContain('url: `/pages/record-detail/index?planId=${planId}`')
    expect(recordDetail).toContain('uni.navigateBack({')
    expect(recordDetail).not.toContain('saveJourneyRecordDraft')
    expect(recordDetail).not.toContain('finalizeJourneyRecordDraft')
    expect(recordDetail).not.toContain('record-detail-editor')
    expect(recordDetail).not.toContain('<textarea')
    expect(recordDetail).not.toContain('<input')
  })

  test('shows only actual task artifacts in detail and previews real photos with the native API', () => {
    expect(recordDetail).toContain('record-detail-hero')
    expect(recordDetail).toContain('record-detail-summary-card')
    expect(recordDetail).toContain('任务记录')
    expect(recordDetail).toContain('v-if="entry.displayImage"')
    expect(recordDetail).toContain('v-if="entry.note"')
    expect(recordDetail).not.toContain('recordWatercolorFallback')
    expect(recordDetail).not.toContain('这一站还没有留下文字发现')
    expect(recordDetail).toContain('previewEntryImage(entry)')
    expect(recordDetail).toContain('uni.previewImage({')
  })

  test('connects a completed Explore plan straight to its record detail without restoring home records', () => {
    expect(explorePage).toContain("label: '查看探索相册'")
    expect(explorePage).toContain('uni.navigateTo({ url: `/pages/record-detail/index?planId=${encodeURIComponent(String(this.activePlan.id))}` })')
    expect(homePage).not.toContain('最近记录')
  })

  test('keeps the four-destination navigation with Record active on this page', () => {
    expect(recordPage).toContain('<AppTabbar active="record"')
    for (const tab of ['首页', '探索', '记录', '我的']) {
      expect(tabbar).toContain(`label: '${tab}'`)
    }
    expect(tabbar).not.toContain("key: 'route'")
    expect(tabbar).not.toContain("key: 'plan'")
  })
})
