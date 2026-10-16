<template>
  <view class="page-header tl-safe-top">
    <view class="page-header__row">
      <view class="page-header__side">
        <button
          v-if="showBack"
          class="page-header__control page-header__back tl-pressable"
          :disabled="controlsDisabled"
          aria-label="返回"
          @click="handleBack"
        >
          <text aria-hidden="true">‹</text>
        </button>
      </view>

      <text class="page-header__title">{{ title }}</text>

      <view class="page-header__side page-header__side--right">
        <slot name="right" :disabled="controlsDisabled">
          <button
            v-if="actionText"
            class="page-header__control page-header__action tl-pressable"
            :disabled="controlsDisabled"
            @click="handleAction"
          >
            {{ loading ? loadingText : actionText }}
          </button>
        </slot>
      </view>
    </view>
  </view>
</template>

<script>
export default {
  name: 'PageHeader',
  props: {
    title: { type: String, required: true },
    showBack: { type: Boolean, default: true },
    actionText: { type: String, default: '' },
    loadingText: { type: String, default: '处理中…' },
    disabled: { type: Boolean, default: false },
    loading: { type: Boolean, default: false }
  },
  emits: ['back', 'action'],
  computed: {
    controlsDisabled() {
      return this.disabled || this.loading
    }
  },
  methods: {
    handleBack() {
      if (this.controlsDisabled) return
      this.$emit('back')
    },
    handleAction() {
      if (this.controlsDisabled) return
      this.$emit('action')
    }
  }
}
</script>

<style scoped lang="scss">
.page-header {
  width: 100%;
  color: var(--tl-color-text);
  background: var(--tl-color-bg);
}

.page-header__row {
  display: grid;
  grid-template-columns: var(--tl-touch-target) minmax(0, 1fr) var(--tl-touch-target);
  align-items: center;
  min-height: var(--tl-touch-target);
}

.page-header__side {
  display: flex;
  align-items: center;
  min-width: 0;
  min-height: var(--tl-touch-target);
}

.page-header__side--right {
  justify-content: flex-end;
}

.page-header__control {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: var(--tl-touch-target);
  min-height: var(--tl-touch-target);
  border: 0;
  border-radius: var(--tl-radius-control);
}

.page-header__control[disabled] {
  color: var(--tl-color-disabled);
  opacity: 0.72;
}

.page-header__back {
  font-size: 56rpx;
  line-height: 1;
  color: var(--tl-color-primary);
}

.page-header__action {
  max-width: 168rpx;
  padding: 0 12rpx;
  overflow: hidden;
  font-size: var(--tl-type-meta);
  font-weight: var(--tl-weight-primary-action);
  color: var(--tl-color-primary);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.page-header__title {
  display: block;
  min-width: 0;
  overflow: hidden;
  font-size: 34rpx;
  font-weight: 700;
  line-height: 1.3;
  text-align: center;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
