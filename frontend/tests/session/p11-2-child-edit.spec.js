import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { beforeEach, describe, expect, test } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { getRequestCalls, resetUniRuntime, setRequestHandler } from './setup/uniRuntime.js'
import { useChildStore } from '../../src/stores/child.js'
import { useUserStore } from '../../src/stores/user.js'

const root = resolve(__dirname, '../../..')
const frontendFile = (...parts) => resolve(root, 'frontend', ...parts)
const sourceOf = (...parts) => readFileSync(frontendFile(...parts), 'utf8')
const childEdit = sourceOf('src', 'pages', 'child-edit', 'index.vue')
const childAvatars = sourceOf('src', 'constants', 'childAvatars.js')
const profile = sourceOf('src', 'pages', 'profile', 'index.vue')
const childSwitch = sourceOf('src', 'pages', 'child-switch', 'index.vue')
const pages = sourceOf('src', 'pages.json')

const avatarKeys = ['avatar_01', 'avatar_02', 'avatar_03', 'avatar_04', 'avatar_05', 'avatar_06']
const ageOptions = Array.from({ length: 10 }, (_, index) => index + 3)

function pageMethod(source, name, dependencyNames = []) {
  const match = source.match(new RegExp(`(async )?${name}\\(([^)]*)\\) \\{[\\s\\S]*?\\n    \\},`))
  if (!match) throw new Error(`Missing ${name} method`)
  const functionSource = match[0]
    .replace(new RegExp(`^(async )?${name}\\(`), `${match[1] || ''}function ${name}(`)
    .replace(/,\s*$/, '')
  return Function(...dependencyNames, `return (${functionSource})`)
}

function respond(options, data, statusCode = 200) {
  options.success({ statusCode, data: { success: true, data } })
}

function login() {
  useUserStore().loginSuccess('p11-2-token', { id: 9201, nickname: '监护人' })
}

describe('P11.2b Child Edit', () => {
  beforeEach(() => {
    resetUniRuntime()
    setActivePinia(createPinia())
  })

  test('registers one non-tab child-edit page and real preset-avatar mapping', () => {
    expect(pages).toContain('pages/child-edit/index')
    expect(childEdit).toContain("isCreateMode ? '添加孩子' : '儿童资料'")
    expect(childEdit).not.toContain('<AppTabbar')
    expect(childAvatars).toContain('CHILD_AVATARS')

    for (const avatarKey of avatarKeys) {
      expect(childAvatars).toContain(`key: '${avatarKey}'`)
      expect(existsSync(frontendFile('src', 'static', 'avatars', 'children', `${avatarKey}.png`))).toBe(true)
    }
  })

  test('create mode starts with no fabricated child data or guardian consent', () => {
    expect(childEdit).toContain("avatarPreset: ''")
    expect(childEdit).toContain('age: null')
    expect(childEdit).toContain('guardianConsent: false')
    expect(childEdit).toContain('请选择一个预设头像')
    expect(childEdit).toContain("if (this.isCreateMode) return this.form.guardianConsent === true")
  })

  test('validates avatar, name, both age boundaries, optional city, and interests before save', () => {
    const collectValidationErrors = pageMethod(childEdit, 'collectValidationErrors', ['CHILD_AVATAR_KEYS', 'AGE_OPTIONS'])(avatarKeys, ageOptions)
    const validContext = {
      form: { avatarPreset: 'avatar_01', name: '小童', age: 3, city: '', interests: ['动物'], customInterests: [] },
    }
    expect(collectValidationErrors.call(validContext)).toEqual({})
    validContext.form.age = 12
    expect(collectValidationErrors.call(validContext)).toEqual({})
    validContext.form.age = 2
    validContext.form.avatarPreset = ''
    validContext.form.name = ' '
    validContext.form.city = 'x'.repeat(51)
    expect(collectValidationErrors.call(validContext)).toMatchObject({
      avatarPreset: '请选择一个预设头像',
      name: '昵称需为 1–50 个字符',
      age: '请选择 3–12 岁',
      city: '城市最多 50 个字符',
    })
  })

  test('builds a create payload without derived or default-child fields', () => {
    const buildPayload = pageMethod(childEdit, 'buildPayload')()
    const context = {
      form: {
        avatarPreset: 'avatar_02', name: ' 小安 ', age: 12, city: ' ', interests: ['动物'], customInterests: ['手工'], guardianConsent: true,
      },
      isCreateMode: true,
      requiresGuardianConsent: false,
      selectedInterests() { return [...this.form.interests, ...this.form.customInterests] },
    }

    expect(buildPayload.call(context)).toEqual({
      avatarPreset: 'avatar_02', name: '小安', age: 12, city: null, interests: ['动物', '手工'], guardianConsent: true,
    })
  })

  test('keeps normal edit consent absent while legacy consent is explicit', () => {
    const buildPayload = pageMethod(childEdit, 'buildPayload')()
    const form = { avatarPreset: 'avatar_03', name: '小北', age: 7, city: '佛山', interests: [], customInterests: [], guardianConsent: false }
    const normalEdit = { form, isCreateMode: false, requiresGuardianConsent: false, selectedInterests: () => [] }
    const legacyEdit = { form: { ...form, guardianConsent: true }, isCreateMode: false, requiresGuardianConsent: true, selectedInterests: () => [] }

    expect(buildPayload.call(normalEdit)).not.toHaveProperty('guardianConsent')
    expect(buildPayload.call(legacyEdit)).toMatchObject({ guardianConsent: true })
    expect(childEdit).toContain('监护人同意已确认')
    expect(childEdit).toContain('确认继续保存该儿童资料')
  })

  test('adds custom interests only after trim, without duplicates or more than ten items', () => {
    const addCustomInterest = pageMethod(childEdit, 'addCustomInterest', ['INTEREST_OPTIONS'])(['历史故事', '古建筑', '观察探索', '动物', '手工'])
    const context = {
      customInterest: ' 天文 ',
      customInterestError: '',
      form: { customInterests: [], interests: ['历史故事'] },
      selectedInterests() { return [...this.form.interests, ...this.form.customInterests] },
      clearFieldError() {},
    }
    addCustomInterest.call(context)
    expect(context.form.customInterests).toEqual(['天文'])
    expect(context.customInterest).toBe('')

    context.customInterest = '天文'
    addCustomInterest.call(context)
    expect(context.form.customInterests).toEqual(['天文'])
    expect(context.customInterestError).toBe('该兴趣已经添加')

    context.form.interests = Array.from({ length: 9 }, (_, index) => `兴趣${index}`)
    context.customInterest = '新兴趣'
    addCustomInterest.call(context)
    expect(context.customInterestError).toBe('兴趣最多选择 10 项')
  })

  test('loads the latest edit detail, compares snapshots for dirty state, and handles a missing child', () => {
    expect(childEdit).toContain('const data = await getChild(this.childId)')
    expect(childEdit).toContain('this.initialSnapshot = this.snapshotForm()')
    expect(childEdit).toContain('this.initialSnapshot !== this.snapshotForm()')
    expect(childEdit).toContain("error?.code === 'CHILD_NOT_FOUND'")
    expect(childEdit).toContain('await this.child.fetchChildren(this.user.userInfo.id)')
  })

  test('uses shared authentication cleanup instead of a page-owned token flow', () => {
    expect(childEdit).toContain('isAuthenticationError(error)')
    expect(childEdit).toContain('await endUserSession()')
    expect(childEdit).not.toContain('getStorageSync')
    expect(childEdit).not.toContain('Authorization:')
  })

  test('protects dirty exits and keeps the bottom action above the reported keyboard height', () => {
    expect(childEdit).toContain("title: '放弃本次修改？'")
    expect(childEdit).toContain("cancelText: '继续编辑'")
    expect(childEdit).toContain("confirmText: '放弃修改'")
    expect(childEdit).toContain('onBackPress()')
    expect(childEdit).toContain('uni.onKeyboardHeightChange(this.keyboardHeightHandler)')
    expect(childEdit).toContain("bottom: `${this.keyboardHeight}px`")
    expect(childEdit).toContain('var(--tl-safe-bottom)')
  })

  test('requires two-stage deletion with matching normalized nickname and server-only deletion scope', () => {
    expect(childEdit).toContain("title: '删除儿童资料？'")
    expect(childEdit).toContain('家庭共享路线不会删除')
    expect(childEdit).toContain('其他孩子资料不会受到影响')
    expect(childEdit).toContain('操作不可恢复')
    expect(childEdit).toContain('请输入孩子昵称以确认')
    expect(childEdit).toContain("this.deleteName.trim() === String(this.childDetail?.name || '').trim()")
    expect(childEdit).toContain('await this.child.deleteChild(this.childId)')
    expect(childEdit).not.toContain('JourneyRecord')
    expect(childEdit).not.toContain('audio_object_key')
  })

  test('DELETE sends no client cleanup payload and applies backend currentChild as active context', async () => {
    login()
    const child = useChildStore()
    const children = [
      { id: 1, name: '小宁', age: 8, isDefault: true },
      { id: 2, name: '小安', age: 7, isDefault: false },
      { id: 3, name: '小北', age: 6, isDefault: false },
    ]
    child.applyChildrenPayload({ children, currentChild: children[0] }, 9201)
    child.setActiveChild(2)
    setRequestHandler((options) => {
      expect(options.method).toBe('DELETE')
      expect(options.url).toMatch(/\/children\/3$/)
      expect(options.data).toBeUndefined()
      respond(options, { deletedChildId: 3, children: children.slice(0, 2), currentChild: children[0] })
    })

    await child.deleteChild(3)

    expect(getRequestCalls()).toHaveLength(1)
    expect(child.children.map((item) => item.id)).toEqual([1, 2])
    expect(child.currentChild.id).toBe(1)
    expect(child.activeChildId).toBe(1)
  })

  test('clears active child from a last-child deletion response and leaves Profile truthful', () => {
    login()
    const child = useChildStore()
    child.applyDeletedChildPayload({ deletedChildId: 1, children: [], currentChild: null }, 9201)

    expect(child.children).toEqual([])
    expect(child.currentChild).toBeNull()
    expect(child.activeChild).toBeNull()
    expect(profile).toContain('尚未添加孩子')
    expect(profile).toContain('添加孩子档案后，就能开始保存专属探索记录。')
    expect(profile).toContain("@click=\"openChildEdit()\"")
  })

  test('shows preset avatars while retaining the name-initial fallback for legacy null avatars', () => {
    expect(profile).toContain('getChildAvatar(candidate?.avatarPreset)')
    expect(childSwitch).toContain('getChildAvatar(candidate?.avatarPreset)')
    expect(profile).toContain('v-else>{{ childInitial }}</text>')
    expect(childSwitch).toContain('v-else>{{ childInitial(candidate) }}</text>')
  })

  test('does not add sensitive device permissions or an upload path', () => {
    expect(childEdit).not.toContain('chooseImage')
    expect(childEdit).not.toContain('uploadFile')
    expect(childEdit).not.toContain('getLocation')
    expect(childEdit).not.toContain('authorize')
  })
})
