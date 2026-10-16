import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'

const root = resolve(__dirname, '../../..')
const sourceOf = (...parts) => readFileSync(resolve(root, 'frontend', ...parts), 'utf8')

const variables = sourceOf('src', 'styles', 'variables.scss')
const globalStyles = sourceOf('src', 'styles', 'global.scss')
const mixins = sourceOf('src', 'styles', 'mixins.scss')
const pageHeader = sourceOf('src', 'components', 'ui', 'PageHeader.vue')
const pageState = sourceOf('src', 'components', 'ui', 'PageState.vue')
const appSkeleton = sourceOf('src', 'components', 'ui', 'AppSkeleton.vue')
const confirmDialog = sourceOf('src', 'components', 'ui', 'ConfirmDialog.vue')
const bottomActionBar = sourceOf('src', 'components', 'ui', 'BottomActionBar.vue')
const settings = sourceOf('src', 'pages', 'settings', 'index.vue')

function componentOptions(source) {
  const script = source.match(/<script>([\s\S]*?)<\/script>/)?.[1]
  if (!script) throw new Error('Component script block is missing')
  return new Function(script.replace('export default', 'return'))()
}

describe('P11.3a global UI foundation', () => {
  test('extends the existing token system with semantic color, motion, touch and layer roles', () => {
    expect(variables).toContain('$tl-color-primary: #1f7b47')
    expect(variables).toContain('$tl-color-danger: #b43d31')
    expect(variables).toContain('$tl-motion-fast: 120ms')
    expect(variables).toContain('$tl-motion-loading: 1200ms')
    expect(variables).toContain('$tl-touch-target: 88rpx')
    expect(variables).toContain('$tl-z-dialog: 80')
    expect(globalStyles).toContain('--tl-color-primary: #{$tl-color-primary}')
    expect(globalStyles).toContain('--tl-motion-normal: #{$tl-motion-normal}')
    expect(globalStyles).toContain('--tl-touch-target: #{$tl-touch-target}')
    expect(globalStyles).toContain('--tl-z-content: #{$tl-z-content}')
  })

  test('provides reusable safe-area and reduced-motion contracts', () => {
    expect(mixins).toContain('@mixin safe-area-top')
    expect(mixins).toContain('@mixin safe-area-bottom')
    expect(mixins).toContain('@mixin touch-target')
    expect(globalStyles).toContain('.tl-safe-top')
    expect(globalStyles).toContain('.tl-safe-bottom')
    expect(globalStyles).toContain('@media (prefers-reduced-motion: reduce)')
    expect(globalStyles).toContain('transition-duration: 1ms')
    expect(globalStyles).toContain('.tl-dialog-exit')
  })

  test('keeps all five primitives free from API, store and product-copy dependencies', () => {
    const primitives = [pageHeader, pageState, appSkeleton, confirmDialog, bottomActionBar]
    for (const source of primitives) {
      expect(source).not.toMatch(/from ['"].*api\//)
      expect(source).not.toMatch(/from ['"].*stores\//)
      expect(source).not.toContain('useUserStore')
      expect(source).not.toContain('childId')
      expect(source).not.toContain('routeId')
    }
  })

  test('PageHeader owns safe-area layout while leaving navigation policy to its parent', () => {
    expect(pageHeader).toContain("name: 'PageHeader'")
    expect(pageHeader).toContain('class="page-header tl-safe-top"')
    expect(pageHeader).toContain('var(--tl-touch-target) minmax(0, 1fr) var(--tl-touch-target)')
    expect(pageHeader).toContain("emits: ['back', 'action']")
    expect(pageHeader).toContain("this.$emit('back')")
    expect(pageHeader).toContain('<slot name="right" :disabled="controlsDisabled">')
    expect(pageHeader).not.toContain('uni.navigateBack')

    const events = []
    const options = componentOptions(pageHeader)
    options.methods.handleBack.call({ controlsDisabled: false, $emit: (name) => events.push(name) })
    options.methods.handleAction.call({ controlsDisabled: false, $emit: (name) => events.push(name) })
    options.methods.handleBack.call({ controlsDisabled: true, $emit: (name) => events.push(name) })
    expect(events).toEqual(['back', 'action'])
  })

  test('PageState supports neutral and failure states with optional parent-owned actions', () => {
    expect(pageState).toContain("const STATE_TYPES = ['empty', 'error', 'offline', 'success']")
    expect(pageState).toContain('role="status"')
    expect(pageState).toContain('<slot name="icon" />')
    expect(pageState).toContain("emits: ['action', 'secondary-action']")
    expect(pageState).toContain("this.$emit('secondary-action')")
    expect(pageState).toContain('min-height: var(--tl-touch-target)')

    const events = []
    const options = componentOptions(pageState)
    options.methods.handleAction.call({ disabled: false, $emit: (name) => events.push(name) })
    options.methods.handleSecondaryAction.call({ disabled: false, $emit: (name) => events.push(name) })
    options.methods.handleAction.call({ disabled: true, $emit: (name) => events.push(name) })
    expect(events).toEqual(['action', 'secondary-action'])
  })

  test('AppSkeleton has line, block and circle variants with a static reduced-motion mode', () => {
    expect(appSkeleton).toContain("const SKELETON_VARIANTS = ['line', 'block', 'circle']")
    expect(appSkeleton).toContain("'app-skeleton--animated': animated")
    expect(appSkeleton).toContain('var(--tl-motion-loading)')
    expect(appSkeleton).toContain('@media (prefers-reduced-motion: reduce)')
    expect(appSkeleton).toContain('animation: none')
  })

  test('ConfirmDialog exposes normal, danger, loading and mask-close behavior without auto-confirming', () => {
    expect(confirmDialog).toContain('role="dialog"')
    expect(confirmDialog).toContain('aria-modal="true"')
    expect(confirmDialog).toContain("emits: ['update:modelValue', 'confirm', 'cancel']")
    expect(confirmDialog).toContain("'confirm-dialog__confirm--danger': danger")
    expect(confirmDialog).toContain('if (this.loading) return')
    expect(confirmDialog).toContain('if (!this.closeOnMask || this.loading) return')
    expect(confirmDialog).toContain('requestBackClose()')
    expect(confirmDialog).toContain('危险操作：${this.confirmText}')
    expect(confirmDialog).toContain("this.$emit('confirm')")
    expect(confirmDialog).not.toContain("this.$emit('update:modelValue', true)")

    const events = []
    const options = componentOptions(confirmDialog)
    const context = { loading: false, $emit: (...args) => events.push(args) }
    options.methods.requestConfirm.call(context)
    context.loading = true
    options.methods.requestConfirm.call(context)
    options.methods.requestCancel.call(context)
    context.loading = false
    options.methods.requestCancel.call(context)
    expect(events).toEqual([
      ['confirm'],
      ['cancel'],
      ['update:modelValue', false]
    ])
  })

  test('BottomActionBar delegates save policy and keyboard offset while enforcing touch and safe-area rules', () => {
    expect(bottomActionBar).toContain("emits: ['primary', 'secondary']")
    expect(bottomActionBar).toContain('primaryActionDisabled()')
    expect(bottomActionBar).toContain('return this.primaryDisabled || this.primaryLoading')
    expect(bottomActionBar).toContain('secondaryActionDisabled()')
    expect(bottomActionBar).toContain("? `${this.bottomOffset}px`")
    expect(bottomActionBar).toContain('calc(16rpx + var(--tl-safe-bottom))')
    expect(bottomActionBar).toContain('min-height: var(--tl-touch-target)')
    expect(bottomActionBar).not.toContain('onKeyboardHeightChange')

    const events = []
    const options = componentOptions(bottomActionBar)
    options.methods.triggerPrimary.call({ primaryActionDisabled: false, $emit: (name) => events.push(name) })
    options.methods.triggerPrimary.call({ primaryActionDisabled: true, $emit: (name) => events.push(name) })
    options.methods.triggerSecondary.call({ secondaryActionDisabled: false, $emit: (name) => events.push(name) })
    options.methods.triggerSecondary.call({ secondaryActionDisabled: true, $emit: (name) => events.push(name) })
    expect(events).toEqual(['primary', 'secondary'])
  })

  test('smoke-migrates only the Settings header and preserves the P11.2 account controls', () => {
    expect(settings).toContain("import PageHeader from '../../components/ui/PageHeader.vue'")
    expect(settings).toContain('<PageHeader class="settings-page__header" title="账号与设置" @back="goBack" />')
    expect(settings).toContain('components: { AppTabbar, PageHeader }')
    expect(settings).toContain('goBack() { uni.navigateBack() }')
    expect(settings).toContain('await deleteAccount()')
    expect(settings).toContain('await endUserSession()')
    expect(settings).not.toContain('class="settings-header"')
  })
})
