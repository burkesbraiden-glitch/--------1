<template>
  <view
    v-if="isOpen"
    class="confirm-dialog tl-fade-in"
    role="dialog"
    aria-modal="true"
    :aria-label="title"
    @click.self="requestMaskClose"
  >
    <view class="confirm-dialog__panel tl-dialog-enter">
      <text class="confirm-dialog__title">{{ title }}</text>
      <text v-if="message" class="confirm-dialog__message">{{ message }}</text>
      <slot />

      <view class="confirm-dialog__actions">
        <button
          class="confirm-dialog__button confirm-dialog__cancel tl-pressable"
          :disabled="loading"
          @click="requestCancel"
        >
          {{ cancelText }}
        </button>
        <button
          class="confirm-dialog__button confirm-dialog__confirm tl-pressable"
          :class="{ 'confirm-dialog__confirm--danger': danger }"
          :disabled="loading"
          @click="requestConfirm"
        >
          {{ resolvedConfirmText }}
        </button>
      </view>
    </view>
  </view>
</template>

<script>
export default {
  name: 'ConfirmDialog',
  props: {
    modelValue: { type: Boolean, default: undefined },
    visible: { type: Boolean, default: false },
    title: { type: String, required: true },
    message: { type: String, default: '' },
    confirmText: { type: String, default: '确认' },
    cancelText: { type: String, default: '取消' },
    loadingText: { type: String, default: '处理中…' },
    danger: { type: Boolean, default: false },
    loading: { type: Boolean, default: false },
    closeOnMask: { type: Boolean, default: true },
    closeOnBack: { type: Boolean, default: true }
  },
  emits: ['update:modelValue', 'confirm', 'cancel'],
  computed: {
    isOpen() {
      return typeof this.modelValue === 'boolean' ? this.modelValue : this.visible
    },
    resolvedConfirmText() {
      if (this.loading) return this.loadingText
      return this.danger ? `危险操作：${this.confirmText}` : this.confirmText
    }
  },
  methods: {
    requestConfirm() {
      if (this.loading) return
      this.$emit('confirm')
    },
    requestCancel() {
      if (this.loading) return
      this.$emit('cancel')
      this.$emit('update:modelValue', false)
    },
    requestMaskClose() {
      if (!this.closeOnMask || this.loading) return
      this.requestCancel()
    },
    // Page onBackPress hooks can delegate here because uni-app does not invoke
    // page lifecycle hooks inside child components.
    requestBackClose() {
      if (!this.isOpen) return false
      if (!this.closeOnBack || this.loading) return true
      this.requestCancel()
      return true
    }
  }
}
</script>

<style scoped lang="scss">
.confirm-dialog {
  position: fixed;
  inset: 0;
  z-index: var(--tl-z-overlay);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--tl-space-md);
  background: var(--tl-color-overlay);
}

.confirm-dialog__panel {
  position: relative;
  z-index: var(--tl-z-dialog);
  width: 100%;
  max-width: 640rpx;
  padding: var(--tl-space-md);
  background: var(--tl-color-surface);
  border: 2rpx solid var(--tl-color-border);
  border-radius: var(--tl-radius-sheet);
  box-shadow: var(--tl-shadow-soft);
}

.confirm-dialog__title,
.confirm-dialog__message {
  display: block;
}

.confirm-dialog__title {
  font-size: var(--tl-type-section-title);
  font-weight: var(--tl-weight-section-title);
  line-height: 1.4;
  color: var(--tl-color-text);
}

.confirm-dialog__message {
  margin-top: var(--tl-space-xs);
  font-size: var(--tl-type-body);
  line-height: var(--tl-line-height-body);
  color: var(--tl-color-text-secondary);
  white-space: pre-wrap;
}

.confirm-dialog__actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--tl-space-xs);
  margin-top: var(--tl-space-md);
}

.confirm-dialog__button {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: var(--tl-touch-target);
  padding: 0 var(--tl-space-xs);
  font-size: var(--tl-type-primary-action);
  font-weight: var(--tl-weight-primary-action);
  border-radius: var(--tl-radius-control);
}

.confirm-dialog__cancel {
  color: var(--tl-color-primary);
  border: 2rpx solid var(--tl-color-border);
}

.confirm-dialog__confirm {
  color: var(--tl-color-on-primary);
  background: var(--tl-color-primary);
}

.confirm-dialog__confirm--danger {
  background: var(--tl-color-danger);
}

.confirm-dialog__button[disabled] {
  color: var(--tl-color-disabled);
  background: var(--tl-surface-muted);
  border-color: transparent;
}
</style>
