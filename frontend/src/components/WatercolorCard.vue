<template>
  <view class="watercolor-card">
    <slot></slot>
  </view>
</template>

<script>
export default {
  name: 'WatercolorCard',
}
</script>

<style scoped>
.watercolor-card {
  padding: 28rpx;
  background: #fff7e8;
  border: 2rpx solid rgba(190, 142, 78, 0.42);
  border-radius: 24rpx;
  box-shadow: 0 12rpx 24rpx rgba(97, 63, 28, 0.12);
}
</style>

