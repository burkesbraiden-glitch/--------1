import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const root = resolve(process.cwd(), '..')
const frontendFile = (...parts) => resolve(root, 'frontend', ...parts)
const sourceOf = (...parts) => readFileSync(frontendFile(...parts), 'utf8')

const profile = sourceOf('src', 'pages', 'profile', 'index.vue')
const tabbar = sourceOf('src', 'components', 'AppTabbar.vue')
const pages = sourceOf('src', 'pages.json')

describe('P10.5 profile, child switch, and settings', () => {
  test('builds the quiet Profile home around the real active child without a brand logo or exploration feed', () => {
    expect(profile).toContain('和孩子一起，发现更大的世界')
    expect(profile).toContain('this.child.activeChild')
    expect(profile).toContain('当前探索档案')
    expect(profile).toContain('切换孩子')
    expect(profile).toContain('管理孩子')
    expect(profile).not.toContain('tonglvji-logo')
    expect(profile).not.toContain('openJourneyRecords')
    expect(profile).not.toContain('成长记录')
    expect(profile).not.toContain('当前探索任务')
    expect(profile).not.toContain('推荐目的地')
  })

  test('registers dedicated child-switch and settings pages without changing the four-tab contract', () => {
    for (const pagePath of ['pages/child-switch/index', 'pages/settings/index']) {
      expect(pages).toContain(pagePath)
    }
    expect(existsSync(frontendFile('src', 'pages', 'child-switch', 'index.vue'))).toBe(true)
    expect(existsSync(frontendFile('src', 'pages', 'settings', 'index.vue'))).toBe(true)

    const tabEntries = tabbar.match(/\{\s*key:\s*'[^']+',\s*label:\s*'[^']+',\s*icon:\s*'[^']+',\s*path:\s*'[^']+'\s*\}/g) || []
    expect(tabEntries).toHaveLength(4)
    expect(profile).toContain('<AppTabbar active="profile"')
  })

  test('renders child switching from loaded child data and delegates selection only to childStore active context', () => {
    const switcher = sourceOf('src', 'pages', 'child-switch', 'index.vue')

    expect(switcher).toContain('v-for="candidate in child.children"')
    expect(switcher).toContain('this.child.activeChild')
    expect(switcher).toContain('this.child.setActiveChild(candidate?.id)')
    expect(switcher).toContain('当前探索档案')
    expect(switcher).not.toContain('children[0]')
    expect(switcher).not.toContain('updateChild(')
    expect(switcher).not.toContain('isDefault')
  })

  test('preserves active-child consumers outside Profile', () => {
    for (const path of [
      ['src', 'pages', 'home', 'index.vue'],
      ['src', 'pages', 'explore', 'index.vue'],
      ['src', 'pages', 'record', 'index.vue'],
    ]) {
      expect(sourceOf(...path)).toContain('activeChild')
    }
  })

  test('keeps settings truthful: account context, about entry, and real session logout only', () => {
    const settings = sourceOf('src', 'pages', 'settings', 'index.vue')

    expect(settings).toContain('账号信息')
    expect(settings).toContain('关于童旅记')
    expect(settings).toContain('endUserSession()')
    expect(settings).not.toContain('通知设置')
    expect(settings).not.toContain('隐私设置')
    expect(settings).not.toContain('账号安全')
    expect(settings).not.toContain('未读')
  })
})
