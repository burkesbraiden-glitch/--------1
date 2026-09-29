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
        <image
          class="app-tabbar__icon-image"
          :src="getIconSource(item.key)"
          mode="aspectFit"
        />
      </view>
      <text class="app-tabbar__label">{{ item.label }}</text>
    </button>
  </view>
</template>

<script>
import { useUserStore } from '../stores/user'
import tabHomeIdle from '../assets/navigation/tab-home-idle.svg'
import tabHomeActive from '../assets/navigation/tab-home-active.svg'
import tabRouteIdle from '../assets/navigation/tab-route-idle.svg'
import tabRouteActive from '../assets/navigation/tab-route-active.svg'
import tabExploreIdle from '../assets/navigation/tab-explore-idle.svg'
import tabExploreActive from '../assets/navigation/tab-explore-active.svg'
import tabRecordIdle from '../assets/navigation/tab-record-idle.svg'
import tabRecordActive from '../assets/navigation/tab-record-active.svg'
import tabProfileIdle from '../assets/navigation/tab-profile-idle.svg'
import tabProfileActive from '../assets/navigation/tab-profile-active.svg'

const TAB_ICON_SOURCES = {
  home: { idle: tabHomeIdle, active: tabHomeActive },
  route: { idle: tabRouteIdle, active: tabRouteActive },
  explore: { idle: tabExploreIdle, active: tabExploreActive },
  record: { idle: tabRecordIdle, active: tabRecordActive },
  profile: { idle: tabProfileIdle, active: tabProfileActive },
}

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
        { key: 'route', label: '路线', icon: 'plan', path: '/pages/route/index' },
        { key: 'explore', label: '探索', icon: 'tasks', path: '/pages/plan/index' },
        { key: 'record', label: '记录', icon: 'record', path: '/pages/record/index' },
        { key: 'profile', label: '我的', icon: 'profile', path: '/pages/profile/index' },
      ],
    }
  },
  methods: {
    getIconSource(key) {
      return TAB_ICON_SOURCES[key][this.active === key ? 'active' : 'idle']
    },
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
  padding: 10rpx 18rpx calc(10rpx + var(--tl-safe-bottom));
  background: var(--tl-surface);
  border-top: 1rpx solid var(--tl-divider);
}

.app-tabbar__item {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4rpx;
  min-height: var(--tl-control-min-height);
  min-width: 0;
  padding: 0;
  font-size: var(--tl-type-meta);
  color: var(--tl-text-secondary);
}

.app-tabbar__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44rpx;
  height: 44rpx;
  color: inherit;
}

.app-tabbar__icon-image {
  display: block;
  width: 44rpx;
  height: 44rpx;
}

.app-tabbar__label {
  display: block;
  max-width: 100%;
  overflow: hidden;
  font-size: var(--tl-type-meta);
  font-weight: var(--tl-weight-meta);
  line-height: 1.2;
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
    width: 40rpx;
    height: 40rpx;
  }
}
</style>

