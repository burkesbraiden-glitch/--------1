import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const root = resolve(process.cwd(), '..')
const readFrontendFile = (path) => readFileSync(resolve(root, 'frontend', path), 'utf8')

const pagePaths = [
  'src/pages/home/index.vue',
  'src/pages/plan/index.vue',
  'src/pages/guide/index.vue',
  'src/pages/tasks/index.vue',
  'src/pages/task-detail/index.vue',
  'src/pages/record/index.vue',
  'src/pages/record-detail/index.vue',
  'src/pages/login/index.vue',
  'src/pages/profile/index.vue',
]

describe('FE-R6 full application visual contract', () => {
  test('keeps all core page routes while consuming the visual foundation', () => {
    const pagesConfig = readFrontendFile('src/pages.json')
    const allPageSource = pagePaths.map(readFrontendFile).join('\n')

    for (const path of pagePaths) {
      const source = readFrontendFile(path)
      expect(source).toContain('<template>')
      expect(source).toContain('<script>')
    }

    expect(allPageSource).toMatch(/var\(--tl-(bg|paper|text-main|primary|tabbar-height)/)

    for (const route of [
      'pages/home/index', 'pages/plan/index', 'pages/guide/index', 'pages/tasks/index',
      'pages/task-detail/index', 'pages/record/index', 'pages/record-detail/index',
      'pages/login/index', 'pages/profile/index',
    ]) {
      expect(pagesConfig).toContain(route)
    }
  })

  test('uses the four-item P10.2 tab contract without changing profile authentication routing', () => {
    const tabbar = readFrontendFile('src/components/AppTabbar.vue')

    const tabEntries = tabbar.match(/\{\s*key:\s*'[^']+',\s*label:\s*'[^']+',\s*icon:\s*'[^']+',\s*path:\s*'[^']+'\s*\}/g) || []
    expect(tabEntries).toHaveLength(4)
    for (const icon of ['home', 'explore', 'record', 'profile']) {
      expect(tabbar).toContain(`icon: '${icon}'`)
    }

    expect(tabbar).toContain('app-tabbar__icon--${item.icon}')
    for (const source of [
      'tab-home-idle.svg', 'tab-home-active.svg',
      'tab-explore-idle.svg', 'tab-explore-active.svg',
      'tab-record-idle.svg', 'tab-record-active.svg',
      'tab-profile-idle.svg', 'tab-profile-active.svg',
    ]) {
      expect(tabbar).toContain(source)
    }
    expect(tabbar).toContain("targetPath = userStore.isLoggedIn ? '/pages/profile/index' : '/pages/login/index'")
    expect(tabbar).toContain('uni.reLaunch({')
  })

  test('removes rejected Home book architecture and fake status-bar clock text', () => {
    const home = readFrontendFile('src/pages/home/index.vue')
    const login = readFrontendFile('src/pages/login/index.vue')
    const profile = readFrontendFile('src/pages/profile/index.vue')

    for (const rejectedMarker of [
      'home-hero__spine', 'home-hero__page-stack', 'home-hero__page-shape',
      'home-hero__frame', 'open-book-frame', 'clip-path: polygon',
    ]) {
      expect(home).not.toContain(rejectedMarker)
    }

    expect(login).not.toContain('9:41')
    expect(profile).not.toContain('9:41')
  })

  test('keeps final visual cleanup responsibilities separate from app behavior', () => {
    const login = readFrontendFile('src/pages/login/index.vue')
    const profile = readFrontendFile('src/pages/profile/index.vue')
    const tabbar = readFrontendFile('src/components/AppTabbar.vue')
    const recordDetail = readFrontendFile('src/pages/record-detail/index.vue')

    expect(login).not.toContain('login-page__button-icon">机</text>')
    expect(login).not.toContain('login-page__wechat-icon">微</text>')
    expect(login).not.toContain('login-page__button-icon--phone')
    expect(login).toContain('login-page__button-icon--chat')
    expect(login).toContain("@click=\"agreed = !agreed\"")

    expect(profile).not.toContain('profile-page__avatar">\n        <text>探</text>')
    expect(profile).not.toContain("icon: '档'")
    expect(profile).toContain('active-child__name')
    expect(profile).toContain('activeChild.name')

    expect(tabbar).toContain('flex: 1;')
    expect(tabbar).toContain('min-width: 0;')
    expect(tabbar).toContain('white-space: nowrap;')
    expect(tabbar).toContain('@media (max-width: 360px)')

    expect(recordDetail).toContain('previewEntryImage(entry)')
    expect(recordDetail).toContain('uni.previewImage({')
    expect(recordDetail).not.toContain('recordWatercolorFallback')
    expect(recordDetail).toContain('retryDetail')
  })

  test('keeps the final defect corrections limited to restrained decoration and agreement presentation', () => {
    const record = readFrontendFile('src/pages/record/index.vue')
    const guide = readFrontendFile('src/pages/guide/index.vue')
    const login = readFrontendFile('src/pages/login/index.vue')
    const profile = readFrontendFile('src/pages/profile/index.vue')

    expect(record).not.toContain('.record-page::before')
    expect(record).not.toContain('radial-gradient(ellipse at center, rgba(244, 170, 35, 0.18)')

    expect(guide).toContain('.guide-header__star {')
    expect(guide).toContain('width: 26rpx;')
    expect(guide).toContain('height: 26rpx;')

    expect(login).toContain('.login-page__agreement {')
    expect(login).toContain('background: transparent;')
    expect(login).toContain('.login-page__agreement::after')
    expect(login).toContain('display: none;')
    expect(login).toContain("@click=\"agreed = !agreed\"")

    expect(profile).toContain('当前探索档案')
    expect(profile).not.toContain("'未填写城市'")
  })

  test('keeps the P10.4 Record page quiet instead of treating an album as scrapbook decoration', () => {
    const record = readFrontendFile('src/pages/record/index.vue')

    expect(record).toContain('class="record-year-group"')
    expect(record).toContain('class="record-card__progress-track"')
    expect(record).not.toContain('record-intro__tape')
    expect(record).not.toContain('PolaroidCard')
    expect(record).not.toContain('recordWatercolorFallback')
  })

  test('uses quiet hierarchy and a single light media-card elevation on Record', () => {
    const record = readFrontendFile('src/pages/record/index.vue')

    expect(record).toContain('box-shadow: var(--tl-shadow-media)')
    expect(record).toContain('.record-header__subtitle')
    expect(record).not.toContain('section-title__star')
    expect(record).not.toContain('record-header__spark')
  })

  test('keeps core business handlers and permanently protected task/record affordances', () => {
    const home = readFrontendFile('src/pages/home/index.vue')
    const tasks = readFrontendFile('src/pages/tasks/index.vue')
    const detail = readFrontendFile('src/pages/task-detail/index.vue')
    const recordDetail = readFrontendFile('src/pages/record-detail/index.vue')
    const login = readFrontendFile('src/pages/login/index.vue')
    const profile = readFrontendFile('src/pages/profile/index.vue')
    const childEdit = readFrontendFile('src/pages/child-edit/index.vue')

    for (const sourceAndMarker of [
      [home, 'openCurrentExploration()'], [tasks, 'async completeExploration()'], [detail, 'chooseImage()'],
      [detail, 'async completeTask()'], [detail, 'JOURNEY_RECORD_FINALIZED'],
      [recordDetail, 'previewEntryImage(entry)'], [login, 'submitWechatLogin()'],
      [childEdit, 'async saveProfile()'],
      [profile, 'endUserSession()'],
    ]) {
      expect(sourceAndMarker[0]).toContain(sourceAndMarker[1])
    }
    expect(recordDetail).not.toContain('saveJourneyRecordDraft')
    expect(recordDetail).not.toContain('finalizeJourneyRecordDraft')
  })
})
