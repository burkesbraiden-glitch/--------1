<template>
  <view class="page-state" :class="stateClass" role="status">
    <view v-if="$slots.icon" class="page-state__icon" aria-hidden="true">
      <slot name="icon" />
    </view>
    <text class="page-state__title">{{ title }}</text>
    <text v-if="description" class="page-state__description">{{ description }}</text>
    <view v-if="actionText || secondaryActionText" class="page-state__actions">
      <button
        v-if="actionText"
        class="page-state__primary tl-pressable"
        :disabled="disabled"
        @click="handleAction"
      >
        {{ actionText }}
      </button>
      <button
        v-if="secondaryActionText"
        class="page-state__secondary tl-pressable"
        :disabled="disabled"
        @click="handleSecondaryAction"
      >
        {{ secondaryActionText }}
      </button>
    </view>
  </view>
</template>

<script>
const STATE_TYPES = ['empty', 'error', 'offline', 'success']

export default {
  name: 'PageState',
  props: {
    type: {
      type: String,
      default: 'empty',
      validator: (value) => STATE_TYPES.includes(value)
    },
    title: { type: String, required: true },
    description: { type: String, default: '' },
    actionText: { type: String, default: '' },
    secondaryActionText: { type: String, default: '' },
    disabled: { type: Boolean, default: false }
  },
  emits: ['action', 'secondary-action'],
  computed: {
    stateClass() {
      return `page-state--${this.type}`
    }
  },
  methods: {
    handleAction() {
      if (this.disabled) return
      this.$emit('action')
    },
    handleSecondaryAction() {
      if (this.disabled) return
      this.$emit('secondary-action')
    }
  }
}
</script>

<style scoped lang="scss">
.page-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 360rpx;
  padding: var(--tl-space-lg) var(--tl-space-md);
  text-align: center;
}

.page-state__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--tl-touch-target);
  height: var(--tl-touch-target);
  margin-bottom: var(--tl-space-sm);
  color: var(--tl-color-primary);
  background: var(--tl-color-primary-soft);
  border-radius: var(--tl-radius-pill);
}

.page-state--error .page-state__icon {
  color: var(--tl-color-danger);
  background: rgba(180, 61, 49, 0.1);
}

.page-state__title {
  display: block;
  font-size: var(--tl-type-section-title);
  font-weight: var(--tl-weight-section-title);
  line-height: 1.4;
  color: var(--tl-color-text);
}

.page-state__description {
  display: block;
  max-width: 600rpx;
  margin-top: var(--tl-space-xs);
  font-size: var(--tl-type-body);
  line-height: var(--tl-line-height-body);
  color: var(--tl-color-text-secondary);
}

.page-state__actions {
  display: flex;
  flex-direction: column;
  gap: var(--tl-space-xs);
  width: 100%;
  max-width: 520rpx;
  margin-top: var(--tl-space-md);
}

.page-state__primary,
.page-state__secondary {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: var(--tl-touch-target);
  padding: 0 var(--tl-space-md);
  font-size: var(--tl-type-primary-action);
  font-weight: var(--tl-weight-primary-action);
  border-radius: var(--tl-radius-control);
}

.page-state__primary {
  color: var(--tl-color-on-primary);
  background: var(--tl-color-primary);
}

.page-state__secondary {
  color: var(--tl-color-primary);
  border: 2rpx solid var(--tl-color-border);
}

.page-state__primary[disabled],
.page-state__secondary[disabled] {
  color: var(--tl-color-disabled);
  background: var(--tl-surface-muted);
  border-color: transparent;
}
</style>
