<template>
  <view
    class="app-skeleton"
    :class="[`app-skeleton--${variant}`, { 'app-skeleton--animated': animated }]"
    aria-hidden="true"
  />
</template>

<script>
const SKELETON_VARIANTS = ['line', 'block', 'circle']

export default {
  name: 'AppSkeleton',
  props: {
    variant: {
      type: String,
      default: 'line',
      validator: (value) => SKELETON_VARIANTS.includes(value)
    },
    animated: { type: Boolean, default: true }
  }
}
</script>

<style scoped lang="scss">
.app-skeleton {
  display: block;
  width: 100%;
  background: var(--tl-surface-muted);
  border: 2rpx solid rgba(190, 142, 78, 0.14);
}

.app-skeleton--line {
  height: 24rpx;
  border-radius: var(--tl-radius-small);
}

.app-skeleton--block {
  height: 160rpx;
  border-radius: var(--tl-radius-media);
}

.app-skeleton--circle {
  width: var(--tl-touch-target);
  height: var(--tl-touch-target);
  border-radius: var(--tl-radius-pill);
}

.app-skeleton--animated {
  animation: app-skeleton-pulse var(--tl-motion-loading) var(--tl-ease-standard) infinite alternate;
}

@keyframes app-skeleton-pulse {
  from { opacity: 0.55; }
  to { opacity: 1; }
}

@media (prefers-reduced-motion: reduce) {
  .app-skeleton--animated {
    animation: none;
  }
}
</style>
