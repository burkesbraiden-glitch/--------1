<template>
  <view class="growth-badge" :class="`growth-badge--${theme}`">
    <view class="growth-badge__icon">
      <text>{{ icon }}</text>
    </view>
    <view class="growth-badge__copy">
      <text class="growth-badge__name">{{ label }}</text>
      <text v-if="description" class="growth-badge__description">{{ description }}</text>
    </view>
    <text class="growth-badge__value">{{ value }}</text>
  </view>
</template>

<script>
export default {
  name: 'GrowthBadge',
  props: {
    label: {
      type: String,
      default: '成长',
    },
    value: {
      type: [String, Number],
      default: 0,
    },
    description: {
      type: String,
      default: '',
    },
    icon: {
      type: String,
      default: '看',
    },
    theme: {
      type: String,
      default: 'green',
    },
  },
}
</script>

<style scoped>
.growth-badge {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  min-width: 0;
  min-height: 164rpx;
  padding: 16rpx 12rpx 14rpx;
  background: #dceecb;
  border: 2rpx solid rgba(85, 117, 60, 0.2);
  border-radius: 22rpx;
}

.growth-badge--blue {
  background: #dfeff8;
  border-color: rgba(47, 111, 148, 0.2);
}

.growth-badge--yellow {
  background: #fff0bd;
  border-color: rgba(244, 170, 35, 0.24);
}

.growth-badge__icon {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 50rpx;
  height: 50rpx;
  margin-bottom: 8rpx;
  font-size: 20rpx;
  font-weight: 900;
  color: #55753c;
  background: rgba(255, 250, 240, 0.72);
  border: 3rpx solid rgba(255, 250, 240, 0.84);
  border-radius: 50%;
}

.growth-badge__copy {
  width: 100%;
  flex: 0 1 auto;
  min-width: 0;
  text-align: center;
}

.growth-badge__name {
  display: block;
  font-size: 24rpx;
  font-weight: 900;
  line-height: 1.15;
  color: #4a2f1b;
  white-space: nowrap;
}

.growth-badge__description {
  display: block;
  margin-top: 8rpx;
  font-size: 19rpx;
  line-height: 1.28;
  color: #5e3c22;
}

.growth-badge__value {
  position: absolute;
  top: 14rpx;
  right: 14rpx;
  font-size: 24rpx;
  font-weight: 800;
  color: #55753c;
}
</style>

