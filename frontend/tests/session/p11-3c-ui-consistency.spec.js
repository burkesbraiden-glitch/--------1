import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const root = resolve(__dirname, '../../..')
const sourceOf = (...parts) => readFileSync(resolve(root, 'frontend', ...parts), 'utf8')

const pageHeader = sourceOf('src', 'components', 'ui', 'PageHeader.vue')
const pageState = sourceOf('src', 'components', 'ui', 'PageState.vue')
const appSkeleton = sourceOf('src', 'components', 'ui', 'AppSkeleton.vue')
const bottomActionBar = sourceOf('src', 'components', 'ui', 'BottomActionBar.vue')
const appTabbar = sourceOf('src', 'components', 'AppTabbar.vue')
const childEdit = sourceOf('src', 'pages', 'child-edit', 'index.vue')
const childSwitch = sourceOf('src', 'pages', 'child-switch', 'index.vue')
const explore = sourceOf('src', 'pages', 'explore', 'index.vue')
const home = sourceOf('src', 'pages', 'home', 'index.vue')
const profile = sourceOf('src', 'pages', 'profile', 'index.vue')
const record = sourceOf('src', 'pages', 'record', 'index.vue')
const settings = sourceOf('src', 'pages', 'settings', 'index.vue')
const globalStyles = sourceOf('src', 'styles', 'global.scss')
const mixins = sourceOf('src', 'styles', 'mixins.scss')

describe('P11.3c UI consistency and interaction polish', () => {
  test('keeps the shared secondary header balanced, safe-area aware, and touch sized', () => {
    expect(pageHeader).toContain('class="page-header tl-safe-top"')
    expect(pageHeader).toContain('grid-template-columns: var(--tl-touch-target) minmax(0, 1fr) var(--tl-touch-target)')
    expect(pageHeader).toContain('min-height: var(--tl-touch-target)')
    expect(pageHeader).toContain('text-overflow: ellipsis')
    for (const page of [childEdit, childSwitch, settings]) {
      expect(page).toContain("import PageHeader from '../../components/ui/PageHeader.vue'")
      expect(page).toContain('@back=')
    }
  })

  test('keeps root tabs out of secondary-page headers and provides accessible selected feedback', () => {
    for (const page of [home, explore, record, profile]) {
      expect(page).not.toContain('<PageHeader')
    }
    for (const label of ['首页', '探索', '记录', '我的']) {
      expect(appTabbar).toContain(`label: '${label}'`)
    }
    expect(appTabbar).toContain('tl-pressable tl-selected-transition')
    expect(appTabbar).toContain(":aria-current=\"active === item.key ? 'page' : undefined\"")
    expect(appTabbar).toContain('z-index: var(--tl-z-tabbar)')
  })

  test('keeps Child Edit dirty protection and dialogs ahead of page exit', () => {
    expect(childEdit).toContain('requestLeave()')
    expect(childEdit).toContain('if (!this.isDirty)')
    expect(childEdit).toContain('this.showDiscardDialog()')
    expect(childEdit).toContain('onBackPress()')
    expect(childEdit).toContain('if (this.showDiscardConfirm)')
    expect(childEdit).toContain('if (this.showDeleteConfirm)')
    expect(childEdit).toContain('if (this.showDeleteNameDialog)')
    expect(childEdit).toContain('<ConfirmDialog')
    expect(childEdit).toContain('showDeleteNameDialog')
  })

  test('keeps BottomActionBar and Child Edit keyboard offsets tied to live keyboard state', () => {
    expect(bottomActionBar).toContain('bottomOffset')
    expect(bottomActionBar).toContain("return { bottom: value || '0px' }")
    expect(bottomActionBar).toContain('var(--tl-safe-bottom)')
    expect(childEdit).toContain('uni.onKeyboardHeightChange(this.keyboardHeightHandler)')
    expect(childEdit).toContain('uni.offKeyboardHeightChange(this.keyboardHeightHandler)')
    expect(childEdit).toContain(':bottom-offset="bottomActionStyle.bottom"')
    expect(childEdit).toContain('deleteNameDialogStyle()')
    expect(childEdit).toContain(':style="deleteNameDialogStyle"')
    expect(childEdit).toContain(':adjust-position="true"')
  })

  test('keeps Profile child empty, error, and retained-data refresh states separate', () => {
    expect(profile).toContain('v-else-if="isChildEmpty"')
    expect(profile).toContain('isChildEmpty()')
    expect(profile).toContain('showFullChildError()')
    expect(profile).toContain('showChildRefreshError()')
    expect(profile).toContain('hasRetainedChild()')
    expect(profile).toContain('当前仍显示上次内容')
    expect(profile).toContain(':disabled="child.isLoading"')
  })

  test('keeps Record child context, empty, full error, and retained-data errors distinct', () => {
    const childLoading = record.indexOf('v-if="isChildLoading"')
    const childError = record.indexOf('v-else-if="showChildError"')
    const noChild = record.indexOf('v-else-if="showNoChild"')
    const initialLoading = record.indexOf('v-else-if="isInitialLoading"')
    const fullError = record.indexOf('v-else-if="showFullError"')
    const empty = record.indexOf('v-else-if="isEmpty"')
    expect([childLoading, childError, noChild, initialLoading, fullError, empty].every((index) => index >= 0)).toBe(true)
    expect(childLoading).toBeLessThan(childError)
    expect(childError).toBeLessThan(noChild)
    expect(noChild).toBeLessThan(initialLoading)
    expect(initialLoading).toBeLessThan(fullError)
    expect(fullError).toBeLessThan(empty)
    expect(record).toContain('recordContextMatchesActiveChild()')
    expect(record).toContain('this.recordStore.records.filter')
    expect(record).toContain('showChildRefreshError()')
    expect(record).not.toContain('record-card--pressed')
  })

  test('keeps Explore top-level error and empty states separate without changing workbench ownership', () => {
    expect(explore).toContain('v-else-if="showFullPageError"')
    expect(explore).toContain('v-if="!currentRoute"')
    expect(explore).toContain('showFullPageError()')
    expect(explore).toContain('Boolean(this.pageError) && !this.currentRoute')
    expect(explore).toContain('加载最新探索内容失败，当前仍显示上次内容。')
    expect(explore).toContain("selectionPolicy: 'none'")
    expect(explore).toContain('sameId(plan.routeStopId, stopId)')
    expect(explore).not.toContain('error?.message')
  })

  test('keeps Settings account deletion two-stage and lets system back close an open dialog first', () => {
    expect(settings).toContain('requestDeleteAccount()')
    expect(settings).toContain("title: '删除账户？'")
    expect(settings).toContain('uni.showModal({')
    expect(settings).toContain('this.isDeleteConfirming = true')
    expect(settings).toContain('请输入“删除我的账户”继续')
    expect(settings).toContain('onBackPress()')
    expect(settings).toContain('this.cancelDeleteAccount()')
    expect(settings).toContain('this.deleteError = \'删除失败，请稍后重试\'')
  })

  test('uses shared touch-target and quiet press feedback on migrated controls', () => {
    expect(globalStyles).toContain('--tl-touch-target')
    expect(pageState).toContain('min-height: var(--tl-touch-target)')
    for (const page of [childEdit, childSwitch, explore, home, profile, record, settings]) {
      expect(page).toContain('tl-pressable')
    }
    expect(childEdit).toContain('child-edit-consent__check tl-pressable')
    expect(explore).toContain('stop-summary tl-pressable tl-selected-transition')
  })

  test('keeps skeleton, dialog, press, and selection motion behind reduced-motion rules', () => {
    expect(appSkeleton).toContain('animation: app-skeleton-pulse var(--tl-motion-loading)')
    expect(appSkeleton).toContain('@media (prefers-reduced-motion: reduce)')
    expect(appSkeleton).toContain('animation: none')
    expect(globalStyles).toContain('@media (prefers-reduced-motion: reduce)')
    expect(globalStyles).toContain('animation-duration: 1ms')
    expect(globalStyles).toContain('transition-duration: 1ms')
    expect(record).toContain('transition: width var(--tl-motion-normal) var(--tl-ease-standard)')
  })

  test('uses shared safe-area helpers for headers, fixed actions, dialogs, and root tabs', () => {
    expect(mixins).toContain('@mixin safe-area-top')
    expect(mixins).toContain('@mixin safe-area-bottom')
    expect(pageHeader).toContain('tl-safe-top')
    expect(bottomActionBar).toContain('var(--tl-safe-bottom)')
    expect(appTabbar).toContain('var(--tl-safe-bottom)')
    expect(childEdit).toContain('var(--tl-safe-bottom)')
    expect(settings).toContain('var(--tl-safe-bottom)')
  })

  test('uses layer tokens in this polish instead of new numeric overlay or tabbar z-indexes', () => {
    expect(appTabbar).not.toMatch(/z-index:\s*50\b/)
    expect(appTabbar).toContain('z-index: var(--tl-z-tabbar)')
    expect(settings).not.toMatch(/z-index:\s*20\b/)
    expect(settings).toContain('z-index: var(--tl-z-overlay)')
    expect(settings).toContain('z-index: var(--tl-z-dialog)')
    expect(childEdit).toContain('z-index: var(--tl-z-dialog)')
  })
})
