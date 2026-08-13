import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const root = resolve(process.cwd(), '..')
const readFrontendFile = (path) => readFileSync(resolve(root, 'frontend', path), 'utf8')
const variablesSource = readFrontendFile('src/styles/variables.scss')
const globalSource = readFrontendFile('src/styles/global.scss')
const mixinsSource = readFrontendFile('src/styles/mixins.scss')
const tabbarSource = readFrontendFile('src/components/AppTabbar.vue')

const coreTokens = [
  '$tl-bg: #f8efd9;',
  '$tl-paper: #fff7e8;',
  '$tl-paper-deep: #f5e5c5;',
  '$tl-text-main: #4a2f1b;',
  '$tl-text-secondary: #8a6d54;',
  '$tl-primary: #f26a21;',
  '$tl-primary-deep: #d94b12;',
  '$tl-blue: #cfe7f5;',
  '$tl-blue-deep: #2f6f94;',
  '$tl-green: #dceecb;',
  '$tl-green-deep: #55753c;',
  '$tl-yellow: #fff0bd;',
  '$tl-line: #dfbd83;',
  '$tl-shadow: rgba(97, 63, 28, 0.12);',
  '$tl-radius-lg: 32rpx;',
  '$tl-radius-md: 24rpx;',
  '$tl-radius-sm: 14rpx;',
  '$tl-page-padding: 32rpx;',
  '$tl-tabbar-height: 132rpx;',
  '$tl-safe-bottom: env(safe-area-inset-bottom);',
]

const approvedTokens = [
  '$tl-content-max-width: 430px;',
  '$tl-safe-top: env(safe-area-inset-top);',
  '$tl-border-soft: rgba(190, 142, 78, 0.28);',
  '$tl-shadow-card: 0 12rpx 24rpx $tl-shadow;',
]

const bridgeTokens = [
  'bg', 'paper', 'paper-deep', 'text-main', 'text-secondary', 'primary', 'primary-deep',
  'blue', 'blue-deep', 'green', 'green-deep', 'yellow', 'line', 'shadow', 'border-soft',
  'shadow-card', 'radius-lg', 'radius-md', 'radius-sm', 'page-padding', 'content-max-width',
  'tabbar-height', 'safe-top', 'safe-bottom',
]

function mixinBody(name) {
  const start = mixinsSource.indexOf(`@mixin ${name}`)
  expect(start).toBeGreaterThanOrEqual(0)
  const end = mixinsSource.indexOf('\n}', start)
  expect(end).toBeGreaterThan(start)
  return mixinsSource.slice(start, end)
}

function blockSource(tag) {
  const match = tabbarSource.match(new RegExp(`<${tag}[^>]*>([\\s\\S]*?)<\\/${tag}>`))
  expect(match).toBeTruthy()
  return match[1]
}

describe('FE-R5A global visual foundation', () => {
  test('keeps core tokens and defines the four approved foundation tokens', () => {
    for (const declaration of [...coreTokens, ...approvedTokens]) {
      expect(variablesSource).toContain(declaration)
    }
  })

  test('bridges required CSS custom properties from Sass tokens', () => {
    expect(globalSource).toMatch(/:root\s*,\s*page\s*\{/)

    for (const token of bridgeTokens) {
      expect(globalSource).toContain(`--tl-${token}: #{$tl-${token}};`)
    }
  })

  test('keeps page-shell limited to page-base responsibilities', () => {
    const pageShell = mixinBody('page-shell')

    expect(pageShell).toContain('min-height: 100vh;')
    expect(pageShell).toContain('box-sizing: border-box;')
    expect(pageShell).toContain('color: $tl-text-main;')
    expect(pageShell).toContain('background: $tl-bg;')
    expect(pageShell).not.toMatch(/padding|header|hero|tabbar|illustration/i)
  })

  test('keeps watercolor-card visually equivalent and responsibility-bounded', () => {
    const watercolorCard = mixinBody('watercolor-card')

    expect(mixinsSource).toContain('@mixin watercolor-card($background: $tl-paper)')
    expect(watercolorCard).toContain('background: $background;')
    expect(watercolorCard).toContain('border: 2rpx solid rgba(190, 142, 78, 0.42);')
    expect(watercolorCard).toContain('border-radius: $tl-radius-md;')
    expect(watercolorCard).toContain('box-shadow: $tl-shadow-card;')
    expect(watercolorCard).not.toMatch(/padding|min-height|header|hero|tabbar|illustration/i)
  })

  test('keeps AppTabbar navigation intact while consuming only equivalent bridge tokens', () => {
    const template = blockSource('template')
    const script = blockSource('script')
    const style = blockSource('style')

    expect(template).toContain('app-tabbar__icon--${item.icon}')
    expect(script).toContain("{ key: 'home', label: '首页', icon: 'home', path: '/pages/home/index' }")
    expect(script).toContain("{ key: 'plan', label: '计划', icon: 'plan', path: '/pages/plan/index' }")
    expect(script).toContain("{ key: 'tasks', label: '任务', icon: 'tasks', path: '/pages/tasks/index' }")
    expect(script).toContain("{ key: 'record', label: '记录', icon: 'record', path: '/pages/record/index' }")
    expect(script).toContain("{ key: 'profile', label: '我的', icon: 'profile', path: '/pages/profile/index' }")
    expect(script).toContain('async go(item)')
    expect(script).toContain('await userStore.restoreSession()')
    expect(script).toContain("targetPath = userStore.isLoggedIn ? '/pages/profile/index' : '/pages/login/index'")
    expect(script).toContain('uni.reLaunch({')

    expect(style).toContain('height: calc(var(--tl-tabbar-height) + var(--tl-safe-bottom));')
    expect(style).toContain('padding: 14rpx 18rpx calc(12rpx + var(--tl-safe-bottom));')
    expect(style).toContain('color: var(--tl-text-secondary);')
    expect(style).toContain('color: var(--tl-primary);')
    expect(style).toContain('background: rgba(255, 247, 232, 0.96);')
    expect(style).toContain('border-top: 2rpx solid rgba(190, 142, 78, 0.22);')
    expect(style).toContain('box-shadow: 0 -10rpx 28rpx rgba(97, 63, 28, 0.08);')
  })
})
