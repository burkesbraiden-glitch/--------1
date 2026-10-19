import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const root = resolve(__dirname, '../../..')
const sourceOf = (...parts) => readFileSync(resolve(root, 'frontend', ...parts), 'utf8')

const childEdit = sourceOf('src', 'pages', 'child-edit', 'index.vue')
const childSwitch = sourceOf('src', 'pages', 'child-switch', 'index.vue')
const profile = sourceOf('src', 'pages', 'profile', 'index.vue')
const record = sourceOf('src', 'pages', 'record', 'index.vue')
const explore = sourceOf('src', 'pages', 'explore', 'index.vue')
const settings = sourceOf('src', 'pages', 'settings', 'index.vue')
const home = sourceOf('src', 'pages', 'home', 'index.vue')
const globalStyles = sourceOf('src', 'styles', 'global.scss')

describe('P11.3b shared UI integration', () => {
  test('Child Edit uses the shared header while keeping leave policy in the page', () => {
    expect(childEdit).toContain("import PageHeader from '../../components/ui/PageHeader.vue'")
    expect(childEdit).toMatch(/<PageHeader[\s\S]*?@back="requestLeave"/)
    expect(childEdit).toContain('if (!this.isDirty)')
    expect(childEdit).toContain('this.showDiscardDialog()')
    expect(childEdit).toContain('onBackPress()')
    expect(childEdit).not.toContain('class="child-edit-header"')
  })

  test('Child Edit delegates save presentation and keyboard offset to BottomActionBar', () => {
    expect(childEdit).toContain("import BottomActionBar from '../../components/ui/BottomActionBar.vue'")
    expect(childEdit).toMatch(/<BottomActionBar[\s\S]*?:primary-disabled="!canSave"/)
    expect(childEdit).toContain(':primary-loading="isSubmitting"')
    expect(childEdit).toContain(':bottom-offset="bottomActionStyle.bottom"')
    expect(childEdit).toContain('uni.onKeyboardHeightChange(this.keyboardHeightHandler)')
    expect(childEdit).toContain('uni.offKeyboardHeightChange(this.keyboardHeightHandler)')
  })

  test('Child Edit uses ConfirmDialog for first-stage deletion and keeps nickname confirmation local', () => {
    expect(childEdit).toContain("import ConfirmDialog from '../../components/ui/ConfirmDialog.vue'")
    expect(childEdit).toMatch(/<ConfirmDialog[\s\S]*?:model-value="showDeleteConfirm"[\s\S]*?danger/)
    expect(childEdit).toContain('@confirm="continueDelete"')
    expect(childEdit).toContain('showDeleteNameDialog')
    expect(childEdit).toContain('请输入孩子昵称以确认')
    expect(childEdit).toContain('deleteNameMatches')
  })

  test('Child Switch uses shared header and distinct loading, error, and empty states', () => {
    expect(childSwitch).toContain("import PageHeader from '../../components/ui/PageHeader.vue'")
    expect(childSwitch).toContain("import PageState from '../../components/ui/PageState.vue'")
    expect(childSwitch).toContain("import AppSkeleton from '../../components/ui/AppSkeleton.vue'")
    expect(childSwitch).toMatch(/v-if="child\.isLoading"[\s\S]*?<AppSkeleton/)
    expect(childSwitch).toMatch(/v-else-if="child\.error"[\s\S]*?type="error"/)
    expect(childSwitch).toMatch(/v-else-if="child\.isLoaded && child\.children\.length === 0"[\s\S]*?type="empty"/)
    expect(childSwitch).toContain('this.child.setActiveChild(candidate?.id)')
  })

  test('Profile keeps its root-tab header and integrates a truthful child PageState', () => {
    expect(profile).not.toContain('<PageHeader')
    expect(profile).toContain('class="profile-header"')
    expect(profile).toContain("import PageState from '../../components/ui/PageState.vue'")
    expect(profile).toMatch(/child\.children\.length === 0[\s\S]*?type="empty"/)
    expect(profile).toContain('title="尚未添加孩子"')
    expect(profile).toContain('description="添加孩子档案后，就能开始保存专属探索记录。"')
    expect(profile).toContain('@action="openChildEdit()"')
  })

  test('Record keeps loading, empty, and error branches distinct with shared states', () => {
    const childLoading = record.indexOf('v-if="isChildLoading"')
    const childError = record.indexOf('v-else-if="showChildError"')
    const noChild = record.indexOf('v-else-if="showNoChild"')
    const recordLoading = record.indexOf('v-else-if="isInitialLoading"')
    const recordError = record.indexOf('v-else-if="showFullError"')
    const empty = record.indexOf('v-else-if="isEmpty"')
    expect([childLoading, childError, noChild, recordLoading, recordError, empty].every((index) => index >= 0)).toBe(true)
    expect(childLoading).toBeLessThan(childError)
    expect(childError).toBeLessThan(noChild)
    expect(noChild).toBeLessThan(recordLoading)
    expect(recordLoading).toBeLessThan(recordError)
    expect(recordError).toBeLessThan(empty)
    expect(record).toContain('<AppSkeleton')
    expect(record.match(/<PageState/g)).toHaveLength(4)
  })

  test('Explore distinguishes top-level loading, error, and route-empty states without changing workbench ownership', () => {
    const loading = explore.indexOf('v-if="isPageLoading"')
    const error = explore.indexOf('v-else-if="pageError"')
    const empty = explore.indexOf('v-else-if="!currentRoute"')
    expect(loading).toBeGreaterThanOrEqual(0)
    expect(error).toBeGreaterThan(loading)
    expect(empty).toBeGreaterThan(error)
    expect(explore).toContain('<AppSkeleton')
    expect(explore).toContain('type="error"')
    expect(explore).toContain('type="empty"')
    expect(explore).toContain("selectionPolicy: 'none'")
    expect(explore).toContain('sameId(plan.routeStopId, stopId)')
  })

  test('Settings retains its shared header and Home keeps its brand-specific header', () => {
    expect(settings).toContain('<PageHeader class="settings-page__header"')
    expect(settings).toContain('@back="goBack"')
    expect(settings).toContain('await deleteAccount()')
    expect(home).toContain('class="home-header"')
    expect(home).toContain('home-header__brand')
    expect(home).not.toContain('<PageHeader')
  })

  test('integrated controls use shared touch, press, selection, and reduced-motion contracts', () => {
    for (const source of [childEdit, childSwitch, profile, record, explore]) {
      expect(source).toContain('tl-pressable')
    }
    expect(childEdit).toContain('tl-selected-transition')
    expect(childSwitch).toContain('tl-selected-transition')
    expect(explore).toContain('tl-selected-transition')
    expect(explore).toContain('var(--tl-touch-target)')
    expect(globalStyles).toContain('@media (prefers-reduced-motion: reduce)')
    expect(globalStyles).toContain('.tl-selected-transition')
  })
})
