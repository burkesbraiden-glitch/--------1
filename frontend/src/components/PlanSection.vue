<template>
  <view class="plan-section">
    <text class="plan-section__title">{{ title }}</text>
    <slot></slot>
  </view>
</template>

<script>
export default {
  name: 'PlanSection',
  props: {
    title: {
      type: String,
      default: '探索计划',
    },
  },
}
</script>

<style scoped>
.plan-section {
  padding: 26rpx;
  background: #fff7e8;
  border: 2rpx solid rgba(190, 142, 78, 0.42);
  border-radius: 24rpx;
  box-shadow: 0 12rpx 24rpx rgba(97, 63, 28, 0.12);
}

.plan-section__title {
  display: block;
  margin-bottom: 14rpx;
  font-size: 30rpx;
  font-weight: 800;
}
</style>

