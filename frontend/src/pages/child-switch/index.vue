<template>
  <view class="child-switch-page">
    <view class="child-switch-page__paper">
      <PageHeader class="child-switch-page__header" title="切换孩子" @back="goBack">
        <template #right="{ disabled }">
          <button class="child-switch-manage tl-pressable" :disabled="disabled" @click="openManageChild">管理</button>
        </template>
      </PageHeader>

      <view v-if="child.isLoading && child.children.length === 0" class="child-switch-skeletons" aria-label="正在同步孩子档案">
        <AppSkeleton v-for="item in 3" :key="item" class="child-switch-skeleton" variant="block" />
      </view>
      <PageState
        v-else-if="child.error && child.children.length === 0"
        type="error"
        title="孩子资料加载失败"
        description="请检查网络后重试。"
        action-text="重试"
        @action="loadChildren"
      />
      <PageState
        v-else-if="child.isLoaded && child.children.length === 0"
        type="empty"
        title="尚未添加孩子"
        description="添加孩子档案后，就能切换专属探索记录。"
        action-text="添加孩子"
        @action="openAddChild"
      />
      <view v-else>
        <view v-if="child.error && child.children.length" class="child-switch-refresh-error" role="status">
          <text>孩子资料更新失败，请检查网络后重试。</text>
          <button class="child-switch-refresh-error__retry tl-pressable" :disabled="child.isLoading" @click="loadChildren">重试</button>
        </view>
        <view class="child-switch-list">
          <button
            v-for="candidate in child.children"
            :key="candidate.id"
            class="child-switch-item tl-pressable tl-selected-transition"
            :class="{ 'child-switch-item--active': isActiveChild(candidate) }"
            @click="selectActiveChild(candidate)"
          >
            <view class="child-switch-item__avatar" aria-hidden="true">
              <image v-if="childAvatar(candidate)" :src="childAvatar(candidate).src" mode="aspectFit" />
              <text v-else>{{ childInitial(candidate) }}</text>
            </view>
            <view class="child-switch-item__copy">
              <text>{{ candidate.name }}</text>
              <text><template v-if="ageText(candidate)">{{ ageText(candidate) }} · </template>{{ isActiveChild(candidate) ? '当前探索档案' : '孩子档案' }}</text>
            </view>
            <view v-if="isActiveChild(candidate)" class="child-switch-item__check" aria-label="当前孩子">✓</view>
            <view v-else class="child-switch-item__radio" aria-hidden="true"></view>
          </button>
        </view>
      </view>

      <button v-if="child.isLoaded && child.children.length" class="child-switch-add tl-pressable" @click="openAddChild"><text>＋</text>添加孩子</button>
    </view>
  </view>
</template>

<script>
import { useChildStore } from '../../stores/child'
import { useUserStore } from '../../stores/user'
import { getChildAvatar } from '../../constants/childAvatars.js'
import { endUserSession } from '../../utils/sessionBoundary'
import AppSkeleton from '../../components/ui/AppSkeleton.vue'
import PageHeader from '../../components/ui/PageHeader.vue'
import PageState from '../../components/ui/PageState.vue'

export default {
  components: { AppSkeleton, PageHeader, PageState },
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
    childAvatar(candidate) { return getChildAvatar(candidate?.avatarPreset) },
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
    openChildEdit(childId = null) {
      const suffix = Number.isInteger(childId) && childId > 0 ? `?id=${encodeURIComponent(childId)}` : ''
      uni.navigateTo({ url: `/pages/child-edit/index${suffix}` })
    },
    openAddChild() { this.openChildEdit() },
    openManageChild() { this.openChildEdit(this.child.activeChild?.id) },
    goBack() { uni.navigateBack() },
  },
}
</script>

<style scoped>
.child-switch-page { min-height: 100vh; color: var(--tl-text-main); background: var(--tl-bg); }
.child-switch-page__paper { width: 100%; max-width: var(--tl-content-max-width); min-height: 100vh; padding: 0 var(--tl-page-padding) calc(var(--tl-space-xl) + var(--tl-safe-bottom)); margin: 0 auto; }
.child-switch-page__header { margin-bottom: 38rpx; }.child-switch-manage { min-width: var(--tl-touch-target); min-height: var(--tl-touch-target); font-size: var(--tl-type-meta); font-weight: 600; color: var(--tl-color-primary); text-align: right; white-space: nowrap; }.child-switch-manage[disabled] { color: var(--tl-color-disabled); }
  .child-switch-refresh-error { display: flex; gap: var(--tl-space-xs); align-items: center; justify-content: space-between; min-height: var(--tl-touch-target); padding: var(--tl-space-xs) 0; color: var(--tl-color-text-secondary); border-bottom: 1rpx solid var(--tl-color-border); }.child-switch-refresh-error text { flex: 1; min-width: 0; font-size: var(--tl-type-meta); line-height: var(--tl-line-height-body); }.child-switch-refresh-error__retry { min-width: var(--tl-touch-target); min-height: var(--tl-touch-target); padding: 0; font-size: var(--tl-type-meta); color: var(--tl-color-primary); }
  .child-switch-list { display: flex; flex-direction: column; gap: 18rpx; }.child-switch-item { display: flex; align-items: center; width: 100%; min-height: 142rpx; padding: 22rpx; color: var(--tl-text-main); text-align: left; background: var(--tl-surface); border: 1rpx solid transparent; border-radius: var(--tl-radius-media); box-shadow: var(--tl-shadow-media); }.child-switch-item--active { border-color: #1f7b47; }.child-switch-item__avatar { display: flex; flex: 0 0 92rpx; align-items: center; justify-content: center; width: 92rpx; height: 92rpx; margin-right: 22rpx; overflow: hidden; font-size: 36rpx; font-weight: 600; color: #fff; background: #315248; border-radius: 50%; }.child-switch-item__avatar image { width: 100%; height: 100%; }.child-switch-item__copy { flex: 1; min-width: 0; }.child-switch-item__copy text { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.child-switch-item__copy text:first-child { font-size: var(--tl-type-body); font-weight: 700; }.child-switch-item__copy text:last-child { margin-top: 10rpx; font-size: var(--tl-type-meta); color: var(--tl-text-secondary); }.child-switch-item__check,.child-switch-item__radio { display: flex; flex: 0 0 44rpx; align-items: center; justify-content: center; width: 44rpx; height: 44rpx; border-radius: 50%; }.child-switch-item__check { font-size: 28rpx; font-weight: 700; color: #fff; background: #1f9b5a; }.child-switch-item__radio { border: 2rpx solid #b4bec6; }
.child-switch-add { display: flex; gap: 16rpx; align-items: center; justify-content: center; width: 100%; min-height: var(--tl-control-min-height); margin-top: 26rpx; font-size: var(--tl-type-primary-action); font-weight: 600; color: #17673c; background: #e2f3e7; border-radius: var(--tl-radius-control); }.child-switch-add text { font-size: 48rpx; font-weight: 300; }
.child-switch-skeletons { display: flex; flex-direction: column; gap: 18rpx; }.child-switch-skeleton { height: 142rpx; }
  @media (min-width: 431px) { .child-switch-page__paper { padding: 0 18px calc(32px + var(--tl-safe-bottom)); }.child-switch-page__header { margin-bottom: 19px; }.child-switch-refresh-error,.child-switch-refresh-error__retry { min-height: 44px; }.child-switch-item { min-height: 71px; padding: 11px; }.child-switch-item__avatar { flex-basis: 46px; width: 46px; height: 46px; margin-right: 11px; font-size: 18px; }.child-switch-item__check,.child-switch-item__radio { flex-basis: 22px; width: 22px; height: 22px; }.child-switch-add { min-height: 44px; margin-top: 13px; }.child-switch-add text { font-size: 24px; } }
</style>
