import { describe, expect, test, vi } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const root = resolve(process.cwd(), '..')
const profileSource = readFileSync(resolve(root, 'frontend/src/pages/profile/index.vue'), 'utf8')

const childA = { id: 101, name: '小宁', age: 8, city: '北京', interests: ['古建筑'] }
const childB = { id: 102, name: '小安', age: 6, city: '西安', interests: ['博物馆'] }
const defaultInterests = ['历史故事', '古建筑', '观察探索']

function profileMethod(name) {
  const match = profileSource.match(new RegExp(`(async )?${name}\\(([^)]*)\\) \\{[\\s\\S]*?\\n    \\},`))
  if (!match) {
    throw new Error(`Missing ${name} method`)
  }
  const functionSource = match[0]
    .replace(new RegExp(`^(async )?${name}\\(`), `${match[1] || ''}function ${name}(`)
    .replace(/,\s*$/, '')
  return Function(`return (${functionSource})`)()
}

describe('P9-06 Profile multi-child quick-switch contract', () => {
  test('renders all loaded children in a horizontal quick selector and keeps an add action beside them', () => {
    expect(profileSource).toContain('profile-page__child-quick-list')
    expect(profileSource).toContain('v-for="candidate in child.children"')
    expect(profileSource).toContain('@click="quickSelectChild(candidate)"')
    expect(profileSource).toContain('profile-page__child-quick-add')
    expect(profileSource).toContain('@click="openAddChildForm"')
    expect(profileSource).toContain('child.children.length > 0')
    expect(profileSource).toContain('{{ candidate.name }}')
    expect(profileSource).toContain('{{ candidate.age }}岁')
    expect(profileSource).toContain("'profile-page__child-quick-item--active'")
  })

  test('keeps adding a child available when an active child already exists', () => {
    const childrenIndex = profileSource.indexOf('v-else-if="child.isLoaded && child.children.length > 0"')
    const addActionIndex = profileSource.indexOf('profile-page__child-quick-add')

    expect(childrenIndex).toBeGreaterThanOrEqual(0)
    expect(addActionIndex).toBeGreaterThan(childrenIndex)
  })

  test('opens a blank, explicit create-mode form for a new child', () => {
    const openAddChildForm = profileMethod('openAddChildForm')
    const context = {
      childFormMode: 'edit',
      childForm: null,
      showChildForm: false,
    }

    openAddChildForm.call(context)

    expect(context.childFormMode).toBe('create')
    expect(context.childForm).toEqual({ name: '', age: '7', city: '', interests: defaultInterests })
    expect(context.showChildForm).toBe(true)
  })

  test('opens edit mode with the active child data', () => {
    const openEditChildForm = profileMethod('openEditChildForm')
    const context = {
      activeChild: childB,
      childFormMode: 'create',
      childForm: null,
      showChildForm: false,
    }

    openEditChildForm.call(context)

    expect(context.childFormMode).toBe('edit')
    expect(context.childForm).toEqual({ name: '小安', age: '6', city: '西安', interests: ['博物馆'] })
    expect(context.showChildForm).toBe(true)
  })

  test('create mode saves with createChild, selects the returned child, and never updates an existing child', async () => {
    const saveChildProfile = profileMethod('saveChildProfile')
    const createChild = vi.fn().mockResolvedValue(childB)
    const updateChild = vi.fn()
    const setActiveChild = vi.fn(() => true)
    const context = {
      activeChild: childA,
      child: { createChild, updateChild, setActiveChild },
      childFormMode: 'create',
      childForm: { name: ' 小安 ', age: '6', city: ' 西安 ', interests: ['博物馆'] },
      isSavingChild: false,
      showChildForm: true,
      validateChildForm: vi.fn(() => true),
      showToast: vi.fn(),
      mapChildError: vi.fn(),
    }

    await saveChildProfile.call(context)

    expect(createChild).toHaveBeenCalledWith({ name: '小安', age: 6, city: '西安', interests: ['博物馆'] })
    expect(updateChild).not.toHaveBeenCalled()
    expect(setActiveChild).toHaveBeenCalledWith(102)
    expect(context.showChildForm).toBe(false)
  })

  test('edit mode saves through updateChild with the active child ID', async () => {
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
      mapChildError: vi.fn(),
    }

    await saveChildProfile.call(context)

    expect(updateChild).toHaveBeenCalledWith(101, { name: '小宁', age: 9, city: '南京', interests: ['古建筑'] })
    expect(createChild).not.toHaveBeenCalled()
  })

  test('quick selection delegates to Child Store once, while selecting the current child is a no-op', () => {
    const quickSelectChild = profileMethod('quickSelectChild')
    const setActiveChild = vi.fn(() => true)
    const otherChildContext = {
      child: { setActiveChild },
      isActiveChild: vi.fn(() => false),
      showToast: vi.fn(),
    }

    quickSelectChild.call(otherChildContext, childB)

    expect(setActiveChild).toHaveBeenCalledWith(102)
    expect(otherChildContext.showToast).toHaveBeenCalledWith('已切换到小安')

    const currentChildContext = {
      child: { setActiveChild: vi.fn(() => true) },
      isActiveChild: vi.fn(() => true),
      showToast: vi.fn(),
    }

    quickSelectChild.call(currentChildContext, childA)

    expect(currentChildContext.child.setActiveChild).not.toHaveBeenCalled()
    expect(currentChildContext.showToast).not.toHaveBeenCalled()
  })

  test('keeps Child Store activeChild as the sole display source with no local active ID or first-child fallback', () => {
    expect(profileSource).toContain('activeChild()')
    expect(profileSource).toContain('return this.child.activeChild')
    expect(profileSource).not.toContain('this.child.activeChildId =')
    expect(profileSource).not.toContain('children[0]')
  })

  test('opens the child profile area from the menu without opening the editor', () => {
    const handleMenu = profileMethod('handleMenu')
    const context = {
      showChildCard: false,
      openAddChildForm: vi.fn(),
      openEditChildForm: vi.fn(),
    }

    handleMenu.call(context, 'child')

    expect(context.showChildCard).toBe(true)
    expect(context.openAddChildForm).not.toHaveBeenCalled()
    expect(context.openEditChildForm).not.toHaveBeenCalled()
  })
})
