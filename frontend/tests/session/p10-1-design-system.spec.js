import { readFileSync, existsSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const readSource = (relativePath) => readFileSync(new URL(relativePath, import.meta.url), 'utf8')

const variables = readSource('../../src/styles/variables.scss')
const globalStyles = readSource('../../src/styles/global.scss')
const tabbar = readSource('../../src/components/AppTabbar.vue')
const designSystemPath = new URL('../../../docs/design-system-v2.md', import.meta.url)

describe('P10.1 design-system foundation', () => {
  it('defines the semantic visual foundation while retaining legacy compatibility tokens', () => {
    for (const token of [
      '$tl-paper:',
      '$tl-shadow-card:',
      '$tl-radius-lg:',
      '$tl-radius-md:',
      '$tl-radius-sm:',
      '$tl-surface:',
      '$tl-surface-muted:',
      '$tl-divider:',
      '$tl-space-xs: 16rpx;',
      '$tl-space-sm: 24rpx;',
      '$tl-space-md: 32rpx;',
      '$tl-space-lg: 48rpx;',
      '$tl-space-xl: 64rpx;',
      '$tl-radius-small: 12rpx;',
      '$tl-radius-control: 20rpx;',
      '$tl-radius-media: 24rpx;',
      '$tl-radius-sheet: 32rpx;',
      '$tl-shadow-none: none;',
      '$tl-shadow-media:',
      '$tl-shadow-overlay:',
      '$tl-type-page-title: 48rpx;',
      '$tl-type-section-title: 34rpx;',
      '$tl-type-body: 30rpx;',
      '$tl-type-meta: 26rpx;',
      '$tl-type-primary-action: 30rpx;',
      '$tl-weight-page-title: 700;',
      '$tl-weight-section-title: 600;',
      '$tl-weight-body: 400;',
      '$tl-weight-meta: 400;',
      '$tl-weight-primary-action: 600;',
      '$tl-line-height-body: 1.6;',
      '$tl-control-min-height: 88rpx;',
    ]) {
      expect(variables).toContain(token)
    }

    expect(variables).not.toContain('$tl-tabbar-height: 132rpx;')
    expect(variables).toContain('$tl-tabbar-height: 112rpx;')
  })

  it('exposes only the approved global type and interaction utilities', () => {
    for (const selector of [
      '.tl-page-title',
      '.tl-section-title',
      '.tl-body',
      '.tl-meta',
      '.tl-divider',
      '.tl-primary-button',
      '.tl-text-action',
    ]) {
      expect(globalStyles).toContain(selector)
    }

    for (const customProperty of [
      '--tl-surface:',
      '--tl-surface-muted:',
      '--tl-divider:',
      '--tl-space-xs:',
      '--tl-radius-control:',
      '--tl-shadow-overlay:',
      '--tl-type-page-title:',
      '--tl-weight-primary-action:',
      '--tl-control-min-height:',
    ]) {
      expect(globalStyles).toContain(customProperty)
    }

    expect(globalStyles).toContain('min-height: var(--tl-control-min-height);')
    expect(globalStyles).toContain('border-radius: var(--tl-radius-control);')
    expect(globalStyles).not.toContain('.tl-card')
    expect(globalStyles).not.toContain('font-weight: 900')
  })

  it('keeps the five-tab navigation contract while using the restrained tabbar presentation', () => {
    for (const item of [
      "{ key: 'home', label: '首页', icon: 'home', path: '/pages/home/index' }",
      "{ key: 'route', label: '路线', icon: 'plan', path: '/pages/route/index' }",
      "{ key: 'explore', label: '探索', icon: 'tasks', path: '/pages/plan/index' }",
      "{ key: 'record', label: '记录', icon: 'record', path: '/pages/record/index' }",
      "{ key: 'profile', label: '我的', icon: 'profile', path: '/pages/profile/index' }",
    ]) {
      expect(tabbar).toContain(item)
    }

    for (const svg of [
      'tab-home-idle.svg', 'tab-home-active.svg',
      'tab-route-idle.svg', 'tab-route-active.svg',
      'tab-explore-idle.svg', 'tab-explore-active.svg',
      'tab-record-idle.svg', 'tab-record-active.svg',
      'tab-profile-idle.svg', 'tab-profile-active.svg',
    ]) {
      expect(tabbar).toContain(svg)
    }

    for (const businessGuard of ['restoreSession', 'isLoggedIn', "item.key === 'profile'", 'uni.reLaunch']) {
      expect(tabbar).toContain(businessGuard)
    }

    expect(tabbar).toContain('var(--tl-surface)')
    expect(tabbar).toContain('var(--tl-divider)')
    expect(tabbar).toContain('min-height: var(--tl-control-min-height);')
    expect(tabbar).not.toContain('.app-tabbar__icon::before')
    expect(tabbar).not.toContain('display: none !important')
    expect(tabbar).not.toContain('box-shadow: 0 -10rpx 24rpx')
  })

  it('documents the v2 system and the anti-patterns that it replaces', () => {
    expect(existsSync(designSystemPath)).toBe(true)
    const documentation = readFileSync(designSystemPath, 'utf8')

    for (const section of [
      '设计原则',
      '色彩',
      '排版',
      '间距',
      '圆角',
      '阴影',
      '照片与插画',
      '按钮、列表、分割线与底部导航',
      '禁止项',
      '卡片套卡片',
      '所有分区都做成卡片',
      '无意义的英文 eyebrow',
      '胶带、印章、星星、树叶',
      '多个主 CTA',
      '静态 Demo 内容冒充动态内容',
    ]) {
      expect(documentation).toContain(section)
    }
  })
})
