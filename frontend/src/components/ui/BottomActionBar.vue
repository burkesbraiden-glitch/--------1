<template>
  <view
    class="bottom-action-bar"
    :class="{ 'bottom-action-bar--fixed': fixed }"
    :style="barStyle"
  >
    <view
      class="bottom-action-bar__content"
      :class="{ 'bottom-action-bar__content--with-secondary': secondaryText }"
    >
      <view v-if="$slots.default" class="bottom-action-bar__message">
        <slot />
      </view>
      <button
        v-if="secondaryText"
        class="bottom-action-bar__secondary tl-pressable"
        :disabled="secondaryActionDisabled"
        @click="triggerSecondary"
      >
        {{ secondaryText }}
      </button>
      <button
        class="bottom-action-bar__primary tl-pressable"
        :disabled="primaryActionDisabled"
        @click="triggerPrimary"
      >
        {{ primaryLoading ? loadingText : primaryText }}
      </button>
    </view>
  </view>
</template>

<script>
export default {
  name: 'BottomActionBar',
  props: {
    primaryText: { type: String, required: true },
    loadingText: { type: String, default: '保存中…' },
    primaryDisabled: { type: Boolean, default: false },
    primaryLoading: { type: Boolean, default: false },
    secondaryText: { type: String, default: '' },
    fixed: { type: Boolean, default: true },
    bottomOffset: { type: [Number, String], default: 0 }
  },
  emits: ['primary', 'secondary'],
  computed: {
    primaryActionDisabled() {
      return this.primaryDisabled || this.primaryLoading
    },
    secondaryActionDisabled() {
      return this.primaryLoading
    },
    barStyle() {
      if (!this.fixed) return {}
      const value = typeof this.bottomOffset === 'number'
        ? `${this.bottomOffset}px`
        : this.bottomOffset
      return { bottom: value || '0px' }
    }
  },
  methods: {
    triggerPrimary() {
      if (this.primaryActionDisabled) return
      this.$emit('primary')
    },
    triggerSecondary() {
      if (this.secondaryActionDisabled) return
      this.$emit('secondary')
    }
  }
}
</script>

<style scoped lang="scss">
.bottom-action-bar {
  width: 100%;
  padding: 16rpx var(--tl-page-padding) calc(16rpx + var(--tl-safe-bottom));
  background: rgba(255, 247, 232, 0.96);
  border-top: 2rpx solid var(--tl-color-border);
}

.bottom-action-bar--fixed {
  position: fixed;
  right: 0;
  left: 0;
  z-index: var(--tl-z-sticky);
}

.bottom-action-bar__content {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: var(--tl-space-xs);
  width: 100%;
  max-width: var(--tl-content-max-width);
  margin: 0 auto;
}

.bottom-action-bar__content--with-secondary {
  grid-template-columns: auto minmax(0, 1fr);
}

.bottom-action-bar__message {
  grid-column: 1 / -1;
}

.bottom-action-bar__primary,
.bottom-action-bar__secondary {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: var(--tl-touch-target);
  padding: 0 var(--tl-space-md);
  font-size: var(--tl-type-primary-action);
  font-weight: var(--tl-weight-primary-action);
  border-radius: var(--tl-radius-control);
}

.bottom-action-bar__primary {
  color: var(--tl-color-on-primary);
  background: var(--tl-color-primary);
}

.bottom-action-bar__secondary {
  min-width: var(--tl-touch-target);
  color: var(--tl-color-primary);
  border: 2rpx solid var(--tl-color-border);
}

.bottom-action-bar__primary[disabled],
.bottom-action-bar__secondary[disabled] {
  color: var(--tl-color-disabled);
  background: var(--tl-surface-muted);
  border-color: transparent;
}
</style>
