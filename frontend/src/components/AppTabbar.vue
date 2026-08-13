<template>
  <view class="app-tabbar">
    <button
      v-for="item in tabs"
      :key="item.key"
      class="app-tabbar__item"
      :class="{ 'app-tabbar__item--active': active === item.key }"
      @click="go(item)"
    >
      <view class="app-tabbar__icon" :class="`app-tabbar__icon--${item.icon}`" aria-hidden="true">
        <view class="app-tabbar__icon-stroke"></view>
      </view>
      <text class="app-tabbar__label">{{ item.label }}</text>
    </button>
  </view>
</template>

<script>
import { useUserStore } from '../stores/user'

export default {
  name: 'AppTabbar',
  props: {
    active: {
      type: String,
      default: 'home',
    },
  },
  data() {
    return {
      tabs: [
        { key: 'home', label: '首页', icon: 'home', path: '/pages/home/index' },
        { key: 'plan', label: '计划', icon: 'plan', path: '/pages/plan/index' },
        { key: 'tasks', label: '任务', icon: 'tasks', path: '/pages/tasks/index' },
        { key: 'record', label: '记录', icon: 'record', path: '/pages/record/index' },
        { key: 'profile', label: '我的', icon: 'profile', path: '/pages/profile/index' },
      ],
    }
  },
  methods: {
    async go(item) {
      if (this.active === item.key) {
        return
      }

      let targetPath = item.path
      if (item.key === 'profile') {
        const userStore = useUserStore()
        if (!userStore.isAuthReady || userStore.isRestoring) {
          await userStore.restoreSession()
        }
        targetPath = userStore.isLoggedIn ? '/pages/profile/index' : '/pages/login/index'
      }

      uni.reLaunch({
        url: targetPath,
      })
    },
  },
}
</script>

<style scoped>
.app-tabbar {
  position: fixed;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 50;
  display: flex;
  height: calc(var(--tl-tabbar-height) + var(--tl-safe-bottom));
  padding: 14rpx 18rpx calc(12rpx + var(--tl-safe-bottom));
  background: rgba(255, 247, 232, 0.96);
  border-top: 2rpx solid rgba(190, 142, 78, 0.22);
  box-shadow: 0 -10rpx 28rpx rgba(97, 63, 28, 0.08);
}

.app-tabbar__item {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8rpx;
  min-width: 0;
  font-size: 22rpx;
  color: var(--tl-text-secondary);
}

.app-tabbar__icon {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48rpx;
  height: 48rpx;
  color: inherit;
}

.app-tabbar__icon::before,
.app-tabbar__icon::after,
.app-tabbar__icon-stroke {
  position: absolute;
  box-sizing: border-box;
  content: '';
}

.app-tabbar__icon--home::before {
  top: 14rpx;
  width: 30rpx;
  height: 24rpx;
  border: 3rpx solid currentColor;
  border-top: 0;
  border-radius: 4rpx 4rpx 8rpx 8rpx;
}

.app-tabbar__icon--home::after {
  top: 6rpx;
  width: 30rpx;
  height: 30rpx;
  border-top: 3rpx solid currentColor;
  border-left: 3rpx solid currentColor;
  transform: rotate(45deg) scale(.7);
}

.app-tabbar__icon--plan::before {
  width: 34rpx;
  height: 29rpx;
  border: 3rpx solid currentColor;
  border-radius: 5rpx;
  transform: rotate(-4deg);
}

.app-tabbar__icon--plan::after {
  width: 3rpx;
  height: 31rpx;
  background: currentColor;
  border-radius: 999rpx;
}

.app-tabbar__icon--plan .app-tabbar__icon-stroke {
  top: 14rpx;
  width: 20rpx;
  height: 3rpx;
  background: currentColor;
  border-radius: 999rpx;
}

.app-tabbar__icon--tasks::before {
  width: 32rpx;
  height: 36rpx;
  border: 3rpx solid currentColor;
  border-radius: 7rpx;
}

.app-tabbar__icon--tasks::after {
  top: 5rpx;
  width: 16rpx;
  height: 8rpx;
  border: 3rpx solid currentColor;
  border-bottom: 0;
  border-radius: 7rpx 7rpx 0 0;
}

.app-tabbar__icon--tasks .app-tabbar__icon-stroke {
  top: 26rpx;
  left: 16rpx;
  width: 16rpx;
  height: 8rpx;
  border-bottom: 3rpx solid currentColor;
  border-left: 3rpx solid currentColor;
  transform: rotate(-45deg);
}

.app-tabbar__icon--record::before {
  width: 31rpx;
  height: 35rpx;
  border: 3rpx solid currentColor;
  border-radius: 5rpx 5rpx 8rpx 8rpx;
}

.app-tabbar__icon--record::after {
  top: 14rpx;
  width: 17rpx;
  height: 3rpx;
  background: currentColor;
  border-radius: 999rpx;
  box-shadow: 0 8rpx 0 currentColor, 0 16rpx 0 currentColor;
}

.app-tabbar__icon--profile::before {
  top: 5rpx;
  width: 18rpx;
  height: 18rpx;
  border: 3rpx solid currentColor;
  border-radius: 50%;
}

.app-tabbar__icon--profile::after {
  bottom: 4rpx;
  width: 34rpx;
  height: 20rpx;
  border: 3rpx solid currentColor;
  border-radius: 20rpx 20rpx 8rpx 8rpx;
}

.app-tabbar__label {
  display: block;
  max-width: 100%;
  overflow: hidden;
  font-size: 24rpx;
  line-height: 1;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-tabbar__item--active {
  color: var(--tl-primary);
}

@media (max-width: 360px) {
  .app-tabbar {
    padding-right: 10rpx;
    padding-left: 10rpx;
  }

  .app-tabbar__item {
    gap: 5rpx;
  }

  .app-tabbar__icon {
    width: 44rpx;
    height: 44rpx;
  }

  .app-tabbar__label {
    font-size: 22rpx;
  }
}
</style>

