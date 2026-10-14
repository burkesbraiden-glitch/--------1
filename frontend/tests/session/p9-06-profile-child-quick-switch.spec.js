import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test, vi } from 'vitest'

const root = resolve(__dirname, '../../..')
const sourceOf = (...parts) => readFileSync(resolve(root, 'frontend', ...parts), 'utf8')

const profile = sourceOf('src/pages/profile/index.vue')
const childSwitch = sourceOf('src/pages/child-switch/index.vue')
const childEdit = sourceOf('src/pages/child-edit/index.vue')
const childA = { id: 101, name: '小宁', age: 8 }

function pageMethod(source, name) {
  const match = source.match(new RegExp(`(async )?${name}\\(([^)]*)\\) \\{[\\s\\S]*?\\n    \\},`))
  if (!match) throw new Error(`Missing ${name} method`)
  const functionSource = match[0]
    .replace(new RegExp(`^(async )?${name}\\(`), `${match[1] || ''}function ${name}(`)
    .replace(/,\s*$/, '')
  return Function(`return (${functionSource})`)()
}

describe('P9.06 Profile child switching after P11.2b', () => {
  test('Profile uses one active-child card and routes child actions to the unified editor', () => {
    expect(profile).toContain('active-child')
    expect(profile).toContain('当前探索档案')
    expect(profile).toContain('openChildSwitcher')
    expect(profile).toContain('openChildEdit(activeChild.id)')
    expect(profile).not.toContain('child-form-sheet')
    expect(profile).not.toContain('childFormMode')
  })

  test('Profile creates and edits through child-edit without changing the active-child store contract', () => {
    const openChildEdit = pageMethod(profile, 'openChildEdit')
    const originalUni = globalThis.uni
    globalThis.uni = { navigateTo: vi.fn() }

    try {
      openChildEdit.call({}, null)
      openChildEdit.call({}, childA.id)
      expect(globalThis.uni.navigateTo).toHaveBeenNthCalledWith(1, { url: '/pages/child-edit/index' })
      expect(globalThis.uni.navigateTo).toHaveBeenNthCalledWith(2, { url: '/pages/child-edit/index?id=101' })
    } finally {
      globalThis.uni = originalUni
    }
  })

  test('the switcher keeps active selection local and uses the shared preset-avatar fallback', () => {
    expect(childSwitch).toContain('this.child.setActiveChild(candidate?.id)')
    expect(childSwitch).toContain('getChildAvatar(candidate?.avatarPreset)')
    expect(childSwitch).toContain('v-else>{{ childInitial(candidate) }}</text>')
    expect(childSwitch).not.toContain('updateChild(')
    expect(childSwitch).not.toContain('isDefault')
  })

  test('selecting the already-active child is a no-op', () => {
    const selectActiveChild = pageMethod(childSwitch, 'selectActiveChild')
    const originalUni = globalThis.uni
    globalThis.uni = { navigateBack: vi.fn(), showToast: vi.fn() }

    try {
      const setActiveChild = vi.fn()
      selectActiveChild.call({ isActiveChild: () => true, child: { setActiveChild } }, childA)
      expect(setActiveChild).not.toHaveBeenCalled()
      expect(globalThis.uni.navigateBack).not.toHaveBeenCalled()
    } finally {
      globalThis.uni = originalUni
    }
  })

  test('the child editor owns create and update API calls', () => {
    expect(childEdit).toContain('this.child.createChild(this.buildPayload())')
    expect(childEdit).toContain('this.child.updateChild(this.childId, this.buildPayload())')
    expect(childEdit).toContain('this.child.setActiveChild(savedChild.id)')
  })
})
