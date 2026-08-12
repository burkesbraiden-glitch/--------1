<template>
  <view class="app-tabbar">
    <button
      v-for="item in tabs"
      :key="item.key"
      class="app-tabbar__item"
      :class="{ 'app-tabbar__item--active': active === item.key }"
      @click="go(item)"
    >
      <text class="app-tabbar__icon">{{ item.icon }}</text>
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
        { key: 'home', label: '首页', icon: '宫', path: '/pages/home/index' },
        { key: 'plan', label: '计划', icon: '图', path: '/pages/plan/index' },
        { key: 'tasks', label: '任务', icon: '勾', path: '/pages/tasks/index' },
        { key: 'record', label: '记录', icon: '册', path: '/pages/record/index' },
        { key: 'profile', label: '我的', icon: '我', path: '/pages/profile/index' },
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
  display: flex;
  align-items: center;
  justify-content: center;
  width: 46rpx;
  height: 46rpx;
  font-size: 22rpx;
  font-weight: 700;
  color: inherit;
  border: 3rpx solid currentColor;
  border-radius: 14rpx;
}

.app-tabbar__label {
  font-size: 24rpx;
  line-height: 1;
}

.app-tabbar__item--active {
  color: var(--tl-primary);
}
</style>

