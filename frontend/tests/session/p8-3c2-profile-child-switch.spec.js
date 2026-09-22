import { describe, expect, test, vi } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(process.cwd(), '..')
const profileSource = readFileSync(resolve(root, 'frontend/src/pages/profile/index.vue'), 'utf8')

const childA = { id: 101, name: '小宁', age: 8, city: '北京', interests: ['古建筑'], isDefault: true }
const childB = { id: 102, name: '小安', age: 6, city: '西安', interests: ['博物馆'], isDefault: false }

function profileMethod(name) {
  const match = profileSource.match(new RegExp(`${name}\\(([^)]*)\\) \\{[\\s\\S]*?\\n    \\},`))
  if (!match) {
    throw new Error(`Missing ${name} method`)
  }
  const functionSource = match[0]
    .replace(`${name}(`, `function ${name}(`)
    .replace(/,\s*$/, '')
  return Function(`return (${functionSource})`)()
}

describe('P8.3C2 Profile active-child switch contract', () => {
  test('reads activeChild for the Profile success display', () => {
    expect(profileSource).toContain('activeChild()')
    expect(profileSource).toContain('return this.child.activeChild')
    expect(profileSource).toContain('nickname: this.activeChild.name')
    expect(profileSource).toContain('v-else-if="activeChild"')
  })

  test('does not keep Profile display bound to backend currentChild', () => {
    expect(profileSource).not.toContain('child.currentChild')
    expect(profileSource).not.toContain('this.child.currentChild')
  })

  test('defines a multi-child-only switch condition from the real children list', () => {
    expect(profileSource).toContain('canSwitchChild()')
    expect(profileSource).toContain('this.child.children.length > 1')
  })

  test('renders the switch entry only when multiple children are available', () => {
    expect(profileSource).toContain('v-if="canSwitchChild"')
    expect(profileSource).toContain('切换孩子')
  })

  test('opens a dedicated child switch sheet from the switch entry', () => {
    expect(profileSource).toContain('@click="openChildSwitcher"')
    expect(profileSource).toContain('v-if="showChildSwitcher"')
    expect(profileSource).toContain('切换孩子')

    const openChildSwitcher = profileMethod('openChildSwitcher')
    const context = { canSwitchChild: true, showChildSwitcher: false }
    openChildSwitcher.call(context)
    expect(context.showChildSwitcher).toBe(true)
  })

  test('renders switch choices directly from real children with identifying fields', () => {
    expect(profileSource).toContain('v-for="candidate in child.children"')
    expect(profileSource).toContain('{{ candidate.name }}')
    expect(profileSource).toContain('{{ candidate.age }}岁')
    expect(profileSource).toContain("candidate.city || '未填写城市'")
  })

  test('marks the active child in the switch list', () => {
    expect(profileSource).toContain('isActiveChild(candidate)')
    expect(profileSource).toContain('当前孩子')
    expect(profileSource).toContain("'profile-page__child-option--active'")
  })

  test('selecting another child delegates through childStore.setActiveChild', () => {
    const selectActiveChild = profileMethod('selectActiveChild')
    const setActiveChild = vi.fn(() => true)
    const context = {
      child: { setActiveChild },
      showChildSwitcher: true,
      showToast: vi.fn(),
    }

    selectActiveChild.call(context, childB)

    expect(setActiveChild).toHaveBeenCalledWith(102)
  })

  test('a successful switch closes the sheet without a reload', () => {
    const selectActiveChild = profileMethod('selectActiveChild')
    const context = {
      child: { setActiveChild: vi.fn(() => true) },
      showChildSwitcher: true,
      showToast: vi.fn(),
    }

    selectActiveChild.call(context, childB)

    expect(context.showChildSwitcher).toBe(false)
    expect(context.showToast).not.toHaveBeenCalled()
  })

  test('a failed switch keeps the sheet open and shows a lightweight error', () => {
    const selectActiveChild = profileMethod('selectActiveChild')
    const context = {
      child: { setActiveChild: vi.fn(() => false) },
      showChildSwitcher: true,
      showToast: vi.fn(),
    }

    selectActiveChild.call(context, childB)

    expect(context.showChildSwitcher).toBe(true)
    expect(context.showToast).toHaveBeenCalledOnce()
  })

  test('switching does not write backend default state or call a child PATCH directly', () => {
    const selectActiveChild = profileMethod('selectActiveChild')
    const backendCurrentChild = { ...childA }
    const context = {
      child: {
        currentChild: backendCurrentChild,
        setActiveChild: vi.fn(() => true),
      },
      showChildSwitcher: true,
      showToast: vi.fn(),
    }

    selectActiveChild.call(context, childB)

    expect(context.child.currentChild).toEqual(backendCurrentChild)
    expect(context.child.currentChild.isDefault).toBe(true)
    expect(profileMethod('selectActiveChild').toString()).not.toContain('updateChild')
    expect(profileMethod('selectActiveChild').toString()).not.toContain('isDefault')
  })

  test('opens the existing editor with the active child rather than backend currentChild', () => {
    const openChildForm = profileMethod('openChildForm')
    const context = {
      activeChild: childB,
      child: { hasRemoteChild: true, currentChild: childA },
      childForm: null,
      showChildForm: false,
    }

    openChildForm.call(context)

    expect(context.childForm).toMatchObject({ name: '小安', age: '6', city: '西安', interests: ['博物馆'] })
    expect(context.showChildForm).toBe(true)
  })

  test('saves edits through the active child ID and keeps active context untouched', () => {
    expect(profileSource).toContain('this.child.updateChild(this.activeChild.id, payload)')
    expect(profileSource).not.toContain('this.child.updateChild(this.child.currentChild.id, payload)')
    expect(profileSource).not.toContain('this.child.activeChildId =')
  })

  test('keeps loading, error, and empty states ahead of active-child switch UI', () => {
    const loadingIndex = profileSource.indexOf('v-if="child.isLoading"')
    const errorIndex = profileSource.indexOf('v-else-if="child.error"')
    const emptyIndex = profileSource.indexOf('v-else-if="child.isLoaded && child.children.length === 0"')
    const switchIndex = profileSource.indexOf('v-if="canSwitchChild"')

    expect(loadingIndex).toBeGreaterThanOrEqual(0)
    expect(errorIndex).toBeGreaterThan(loadingIndex)
    expect(emptyIndex).toBeGreaterThan(errorIndex)
    expect(switchIndex).toBeGreaterThan(emptyIndex)
    expect(profileSource).toContain('添加孩子档案')
  })
})
