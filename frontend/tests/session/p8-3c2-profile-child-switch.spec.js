import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test, vi } from 'vitest'

const root = resolve(__dirname, '../../..')
const sourceOf = (...parts) => readFileSync(resolve(root, 'frontend', ...parts), 'utf8')

const profile = sourceOf('src/pages/profile/index.vue')
const childSwitch = sourceOf('src/pages/child-switch/index.vue')
const childB = { id: 102, name: '小安', age: 6 }

function pageMethod(source, name) {
  const match = source.match(new RegExp(`(async )?${name}\\(([^)]*)\\) \\{[\\s\\S]*?\\n    \\},`))
  if (!match) throw new Error(`Missing ${name} method`)
  const functionSource = match[0]
    .replace(new RegExp(`^(async )?${name}\\(`), `${match[1] || ''}function ${name}(`)
    .replace(/,\s*$/, '')
  return Function(`return (${functionSource})`)()
}

describe('P8.3C2 active-child switching after P10.5', () => {
  test('Profile reads the active child from the shared child store', () => {
    expect(profile).toContain('activeChild() {')
    expect(profile).toContain('return this.child.activeChild')
    expect(profile).toContain('{{ activeChild.name }}')
    expect(profile).not.toContain('currentChild')
    expect(profile).not.toContain('children[0]')
  })

  test('Profile routes switching to the dedicated child-switch page', () => {
    expect(profile).toContain('openChildSwitcher()')
    expect(profile).toContain("url: '/pages/child-switch/index'")
    expect(profile).not.toContain('showChildSwitcher')
    expect(profile).not.toContain('quick-child')
  })

  test('requires at least two real children before opening the switch page', () => {
    expect(profile).toContain('canSwitchChild()')
    expect(profile).toContain('return this.child.children.length > 1')
    expect(profile).toContain("this.showToast('添加更多孩子后即可切换')")
  })

  test('the dedicated page lists actual children and marks the active child', () => {
    expect(childSwitch).toContain('v-for="candidate in child.children"')
    expect(childSwitch).toContain('{{ candidate.name }}')
    expect(childSwitch).toContain('{{ ageText(candidate) }}')
    expect(childSwitch).toContain('isActiveChild(candidate)')
    expect(childSwitch).toContain('当前探索档案')
  })

  test('switching only updates the active-child context', () => {
    expect(childSwitch).toContain('this.child.setActiveChild(candidate?.id)')
    expect(childSwitch).not.toContain('updateChild(')
    expect(childSwitch).not.toContain('isDefault')
    expect(childSwitch).not.toContain('currentChild')
  })

  test('switching succeeds by returning and fails without leaving the current page', () => {
    const selectActiveChild = pageMethod(childSwitch, 'selectActiveChild')
    const originalUni = globalThis.uni
    const navigateBack = vi.fn()
    const showToast = vi.fn()
    globalThis.uni = { navigateBack, showToast }

    try {
      const successful = { isActiveChild: () => false, child: { setActiveChild: vi.fn(() => true) } }
      selectActiveChild.call(successful, childB)
      expect(successful.child.setActiveChild).toHaveBeenCalledWith(childB.id)
      expect(navigateBack).toHaveBeenCalledOnce()

      const failed = { isActiveChild: () => false, child: { setActiveChild: vi.fn(() => false) } }
      selectActiveChild.call(failed, childB)
      expect(showToast).toHaveBeenCalledOnce()
      expect(navigateBack).toHaveBeenCalledOnce()
    } finally {
      globalThis.uni = originalUni
    }
  })

  test('Profile retains real create and edit entry points', () => {
    expect(profile).toContain('this.child.createChild(payload)')
    expect(profile).toContain('this.child.updateChild(this.activeChild.id, payload)')
    expect(childSwitch).toContain("openProfile('manage')")
    expect(childSwitch).toContain("openProfile('create')")
  })
})
