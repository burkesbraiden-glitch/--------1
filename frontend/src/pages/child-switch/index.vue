<template>
  <view class="child-switch-page">
    <view class="child-switch-page__paper">
      <view class="child-switch-header">
        <button class="child-switch-header__back" aria-label="返回" @click="goBack">‹</button>
        <text>切换孩子</text>
        <button class="child-switch-header__manage" @click="openManageChild">管理</button>
      </view>

      <view v-if="child.isLoading" class="child-switch-state"><text>正在同步孩子档案…</text></view>
      <view v-else-if="child.error" class="child-switch-state">
        <text>孩子资料加载失败，请重试</text>
        <button @click="loadChildren">重试</button>
      </view>
      <view v-else-if="child.isLoaded && child.children.length === 0" class="child-switch-state">
        <text>尚未添加孩子</text>
        <button @click="openAddChild">添加孩子</button>
      </view>
      <view v-else class="child-switch-list">
        <button
          v-for="candidate in child.children"
          :key="candidate.id"
          class="child-switch-item"
          :class="{ 'child-switch-item--active': isActiveChild(candidate) }"
          @click="selectActiveChild(candidate)"
        >
          <view class="child-switch-item__avatar" aria-hidden="true"><text>{{ childInitial(candidate) }}</text></view>
          <view class="child-switch-item__copy">
            <text>{{ candidate.name }}</text>
            <text><template v-if="ageText(candidate)">{{ ageText(candidate) }} · </template>{{ isActiveChild(candidate) ? '当前探索档案' : '孩子档案' }}</text>
          </view>
          <view v-if="isActiveChild(candidate)" class="child-switch-item__check" aria-label="当前孩子">✓</view>
          <view v-else class="child-switch-item__radio" aria-hidden="true"></view>
        </button>
      </view>

      <button class="child-switch-add" @click="openAddChild"><text>＋</text>添加孩子</button>
    </view>
  </view>
</template>

<script>
import { useChildStore } from '../../stores/child'
import { useUserStore } from '../../stores/user'
import { endUserSession } from '../../utils/sessionBoundary'

export default {
  computed: {
    child() { return useChildStore() },
    user() { return useUserStore() },
  },
  async onShow() {
    await this.user.restoreSession()
    if (!this.user.isLoggedIn) {
      uni.reLaunch({ url: '/pages/login/index' })
      return
    }
    await this.loadChildren()
  },
  methods: {
    async loadChildren() {
      try {
        await this.child.fetchChildren(this.user.userInfo.id)
      } catch (error) {
        if (['UNAUTHORIZED', 'INVALID_TOKEN', 'TOKEN_EXPIRED'].includes(error?.code) || error?.statusCode === 401) {
          await endUserSession()
        }
      }
    },
    childInitial(candidate) {
      return String(candidate?.name || '孩').trim().slice(0, 1) || '孩'
    },
    ageText(candidate) {
      return Number.isInteger(candidate?.age) ? `${candidate.age}岁` : ''
    },
    isActiveChild(candidate) {
      return String(candidate?.id) === String(this.child.activeChild?.id)
    },
    selectActiveChild(candidate) {
      if (this.isActiveChild(candidate)) return
      if (!this.child.setActiveChild(candidate?.id)) {
        uni.showToast({ title: '切换孩子失败，请稍后重试', icon: 'none' })
        return
      }
      uni.navigateBack()
    },
    openProfile(childAction) {
      uni.navigateTo({ url: `/pages/profile/index?childAction=${encodeURIComponent(childAction)}` })
    },
    openAddChild() { this.openProfile('create') },
    openManageChild() { this.openProfile('manage') },
    goBack() { uni.navigateBack() },
  },
}
</script>

<style scoped>
.child-switch-page { min-height: 100vh; color: var(--tl-text-main); background: var(--tl-bg); }
.child-switch-page__paper { width: 100%; max-width: var(--tl-content-max-width); min-height: 100vh; padding: calc(var(--tl-page-padding) + var(--tl-safe-top)) var(--tl-page-padding) calc(var(--tl-space-xl) + var(--tl-safe-bottom)); margin: 0 auto; }
.child-switch-header { display: grid; grid-template-columns: 88rpx 1fr 88rpx; align-items: center; min-height: 88rpx; margin-bottom: 38rpx; text-align: center; }.child-switch-header > text { font-size: var(--tl-type-section-title); font-weight: 700; }.child-switch-header__back,.child-switch-header__manage { min-height: 88rpx; padding: 0; font-size: var(--tl-type-meta); color: #17673c; }.child-switch-header__back { font-size: 58rpx; font-weight: 300; color: var(--tl-text-main); text-align: left; }.child-switch-header__manage { font-weight: 600; text-align: right; white-space: nowrap; }
.child-switch-list { display: flex; flex-direction: column; gap: 18rpx; }.child-switch-item { display: flex; align-items: center; width: 100%; min-height: 142rpx; padding: 22rpx; color: var(--tl-text-main); text-align: left; background: var(--tl-surface); border: 1rpx solid transparent; border-radius: var(--tl-radius-media); box-shadow: var(--tl-shadow-media); }.child-switch-item--active { border-color: #1f7b47; }.child-switch-item__avatar { display: flex; flex: 0 0 92rpx; align-items: center; justify-content: center; width: 92rpx; height: 92rpx; margin-right: 22rpx; font-size: 36rpx; font-weight: 600; color: #fff; background: #315248; border-radius: 50%; }.child-switch-item__copy { flex: 1; min-width: 0; }.child-switch-item__copy text { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.child-switch-item__copy text:first-child { font-size: var(--tl-type-body); font-weight: 700; }.child-switch-item__copy text:last-child { margin-top: 10rpx; font-size: var(--tl-type-meta); color: var(--tl-text-secondary); }.child-switch-item__check,.child-switch-item__radio { display: flex; flex: 0 0 44rpx; align-items: center; justify-content: center; width: 44rpx; height: 44rpx; border-radius: 50%; }.child-switch-item__check { font-size: 28rpx; font-weight: 700; color: #fff; background: #1f9b5a; }.child-switch-item__radio { border: 2rpx solid #b4bec6; }
.child-switch-add { display: flex; gap: 16rpx; align-items: center; justify-content: center; width: 100%; min-height: var(--tl-control-min-height); margin-top: 26rpx; font-size: var(--tl-type-primary-action); font-weight: 600; color: #17673c; background: #e2f3e7; border-radius: var(--tl-radius-control); }.child-switch-add text { font-size: 48rpx; font-weight: 300; }
.child-switch-state { display: flex; flex-direction: column; gap: 18rpx; align-items: flex-start; padding: 32rpx; font-size: var(--tl-type-body); line-height: var(--tl-line-height-body); background: var(--tl-surface); border: 1rpx solid var(--tl-divider); border-radius: var(--tl-radius-media); }.child-switch-state button { min-height: 72rpx; padding: 0 22rpx; font-size: var(--tl-type-meta); color: #17673c; border: 1rpx solid #1f7b47; border-radius: var(--tl-radius-control); }
@media (min-width: 431px) { .child-switch-page__paper { padding: calc(18px + var(--tl-safe-top)) 18px calc(32px + var(--tl-safe-bottom)); }.child-switch-header { grid-template-columns: 44px 1fr 44px; min-height: 44px; margin-bottom: 19px; }.child-switch-header__back,.child-switch-header__manage { min-height: 44px; }.child-switch-item { min-height: 71px; padding: 11px; }.child-switch-item__avatar { flex-basis: 46px; width: 46px; height: 46px; margin-right: 11px; font-size: 18px; }.child-switch-item__check,.child-switch-item__radio { flex-basis: 22px; width: 22px; height: 22px; }.child-switch-add { min-height: 44px; margin-top: 13px; }.child-switch-add text { font-size: 24px; } }
</style>
