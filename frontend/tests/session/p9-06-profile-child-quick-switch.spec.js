import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test, vi } from 'vitest'

const root = resolve(__dirname, '../../..')
const sourceOf = (...parts) => readFileSync(resolve(root, 'frontend', ...parts), 'utf8')

const profile = sourceOf('src/pages/profile/index.vue')
const childSwitch = sourceOf('src/pages/child-switch/index.vue')
const childStore = sourceOf('src/stores/child.js')
const childA = { id: 101, name: '小宁', age: 8, city: '北京', interests: ['古建筑'] }
const childB = { id: 102, name: '小安', age: 6, city: '西安', interests: ['博物馆'] }
const defaultInterests = ['历史故事', '古建筑', '观察探索']

function profileMethod(name) {
  const match = profile.match(new RegExp(`(async )?${name}\\(([^)]*)\\) \\{[\\s\\S]*?\\n    \\},`))
  if (!match) throw new Error(`Missing ${name} method`)
  const functionSource = match[0]
    .replace(new RegExp(`^(async )?${name}\\(`), `${match[1] || ''}function ${name}(`)
    .replace(/,\s*$/, '')
  return Function('DEFAULT_INTERESTS', `return (${functionSource})`)(defaultInterests)
}

function switcherMethod(name) {
  const match = childSwitch.match(new RegExp(`(async )?${name}\\(([^)]*)\\) \\{[\\s\\S]*?\\n    \\},`))
  if (!match) throw new Error(`Missing ${name} method`)
  const functionSource = match[0]
    .replace(new RegExp(`^(async )?${name}\\(`), `${match[1] || ''}function ${name}(`)
    .replace(/,\s*$/, '')
  return Function(`return (${functionSource})`)()
}

describe('P9.06 Profile child switching after P10.5', () => {
  test('Profile uses one current-child card and does not retain the quick selector', () => {
    expect(profile).toContain('active-child-card')
    expect(profile).toContain('当前探索档案')
    expect(profile).toContain('openChildSwitcher')
    expect(profile).not.toContain('quickSelectChild')
    expect(profile).not.toContain('quick-child')
  })

  test('Profile retains the real child create and edit workflow', () => {
    expect(profile).toContain("childFormMode: 'create'")
    expect(profile).toContain("this.childFormMode = 'edit'")
    expect(profile).toContain('this.child.createChild(payload)')
    expect(profile).toContain('this.child.updateChild(this.activeChild.id, payload)')
    expect(profile).toContain('this.child.setActiveChild(savedChild.id)')
  })

  test('opens create and edit forms from the real active-child context', () => {
    const openAddChildForm = profileMethod('openAddChildForm')
    const createContext = { childFormMode: 'edit', childForm: null, showChildForm: false }
    openAddChildForm.call(createContext)
    expect(createContext).toMatchObject({
      childFormMode: 'create',
      childForm: { name: '', age: '7', city: '', interests: defaultInterests },
      showChildForm: true,
    })

    const openEditChildForm = profileMethod('openEditChildForm')
    const editContext = { activeChild: childB, childFormMode: 'create', childForm: null, showChildForm: false }
    openEditChildForm.call(editContext)
    expect(editContext).toMatchObject({
      childFormMode: 'edit',
      childForm: { name: childB.name, age: '6', city: childB.city, interests: childB.interests },
      showChildForm: true,
    })
  })

  test('create mode saves a new child, selects it, and never updates the current child', async () => {
    const saveChildProfile = profileMethod('saveChildProfile')
    const createChild = vi.fn().mockResolvedValue(childB)
    const updateChild = vi.fn()
    const setActiveChild = vi.fn()
    const context = {
      activeChild: childA,
      child: { createChild, updateChild, setActiveChild },
      childFormMode: 'create',
      childForm: { name: ' 小安 ', age: '6', city: ' 西安 ', interests: ['博物馆'] },
      isSavingChild: false,
      showChildForm: true,
      validateChildForm: vi.fn(() => true),
      showToast: vi.fn(),
    }

    await saveChildProfile.call(context)

    expect(createChild).toHaveBeenCalledWith({ name: '小安', age: 6, city: '西安', interests: ['博物馆'] })
    expect(updateChild).not.toHaveBeenCalled()
    expect(setActiveChild).toHaveBeenCalledWith(childB.id)
    expect(context.showChildForm).toBe(false)
  })

  test('edit mode updates only the active child and does not create another child', async () => {
    const saveChildProfile = profileMethod('saveChildProfile')
    const createChild = vi.fn()
    const updateChild = vi.fn().mockResolvedValue(childA)
    const context = {
      activeChild: childA,
      child: { createChild, updateChild, setActiveChild: vi.fn() },
      childFormMode: 'edit',
      childForm: { name: '小宁', age: '9', city: '南京', interests: ['古建筑'] },
      isSavingChild: false,
      showChildForm: true,
      validateChildForm: vi.fn(() => true),
      showToast: vi.fn(),
    }

    await saveChildProfile.call(context)

    expect(updateChild).toHaveBeenCalledWith(childA.id, { name: '小宁', age: 9, city: '南京', interests: ['古建筑'] })
    expect(createChild).not.toHaveBeenCalled()
  })

  test('the switcher provides real add and manage routes', () => {
    expect(profile).toContain('@click="openAddChildForm"')
    expect(profile).toContain('添加孩子')
    expect(childSwitch).toContain('child-switch-add')
    expect(childSwitch).toContain('openAddChild')
    expect(childSwitch).toContain('encodeURIComponent(childAction)')
    expect(childSwitch).toContain("openProfile('manage')")
    expect(childSwitch).toContain("openProfile('create')")
  })

  test('the shared store remains the single source for active-child context', () => {
    expect(childStore).toContain('setActiveChild(childId)')
    expect(childSwitch).toContain('this.child.setActiveChild(candidate?.id)')
    expect(childSwitch).not.toContain('this.child.activeChildId =')
    expect(childSwitch).not.toContain('updateChild(')
  })

  test('selecting the already-active child is a no-op', () => {
    const selectActiveChild = switcherMethod('selectActiveChild')
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
})
