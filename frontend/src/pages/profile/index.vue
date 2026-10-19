<template>
  <view class="profile-page">
    <view class="profile-page__paper">
      <view class="profile-header">
        <view>
          <text class="profile-header__title">我的</text>
          <text class="profile-header__subtitle">和孩子一起，发现更大的世界</text>
        </view>
        <button class="profile-header__settings tl-pressable" aria-label="账号与设置" @click="openSettings">
          <view class="profile-header__settings-icon" aria-hidden="true"></view>
        </button>
      </view>

      <AppSkeleton v-if="isInitialChildLoading" class="profile-child-skeleton" variant="block" aria-label="正在同步孩子档案" />
      <PageState
        v-else-if="showFullChildError"
        type="error"
        title="孩子资料加载失败，请重试"
        action-text="重试"
        :disabled="child.isLoading"
        @action="loadChildren"
      />
      <PageState
        v-else-if="isChildEmpty"
        type="empty"
        title="尚未添加孩子"
        description="添加孩子档案后，就能开始保存专属探索记录。"
        action-text="添加孩子"
        @action="openChildEdit()"
      />
      <template v-else>
      <view v-if="showChildRefreshError" class="profile-refresh-error" role="status">
        <text>孩子资料更新失败，当前仍显示上次内容。</text>
        <button class="profile-refresh-error__retry tl-pressable" :disabled="child.isLoading" @click="loadChildren">
          {{ child.isLoading ? '正在加载…' : '重试' }}
        </button>
      </view>
      <view v-if="activeChild" class="active-child">
        <button class="active-child__identity tl-pressable" @click="openChildEdit(activeChild.id)">
          <view class="active-child__avatar" aria-hidden="true">
            <image v-if="childAvatar(activeChild)" :src="childAvatar(activeChild).src" mode="aspectFit" />
            <text v-else>{{ childInitial }}</text>
          </view>
          <view class="active-child__copy">
            <text class="active-child__name">{{ activeChild.name }}</text>
            <text class="active-child__meta"><template v-if="ageText">{{ ageText }} · </template>当前探索档案</text>
          </view>
          <text class="active-child__arrow" aria-hidden="true">›</text>
        </button>
        <view class="active-child__actions">
          <button class="active-child__action active-child__action--primary tl-pressable" @click="openChildSwitcher">切换孩子</button>
          <button class="active-child__action tl-pressable" @click="openChildEdit(activeChild.id)">管理孩子</button>
        </view>
      </view>
      <AppSkeleton v-else class="profile-child-skeleton" variant="block" aria-label="正在同步孩子档案" />
      </template>

      <view class="profile-section">
        <text class="profile-section__title">孩子与家庭</text>
        <view class="profile-list">
          <button class="profile-list__item tl-pressable" @click="openManageChild">
            <view class="profile-list__copy"><text>孩子档案</text><text>查看和编辑孩子的基本信息</text></view>
            <text class="profile-list__arrow" aria-hidden="true">›</text>
          </button>
          <button class="profile-list__item tl-pressable" @click="openChildEdit()">
            <view class="profile-list__copy"><text>添加孩子</text><text>为家人添加新的孩子档案</text></view>
            <text class="profile-list__arrow" aria-hidden="true">›</text>
          </button>
        </view>
      </view>

      <view v-if="activeChild" class="profile-section">
        <text class="profile-section__title">探索偏好</text>
        <view class="profile-list">
          <button class="profile-list__item tl-pressable" @click="openChildEdit(activeChild.id)">
            <view class="profile-list__copy"><text>兴趣偏好</text><text>设置孩子感兴趣的探索主题</text></view>
            <text class="profile-list__arrow" aria-hidden="true">›</text>
          </button>
        </view>
      </view>

      <view class="profile-section profile-section--last">
        <text class="profile-section__title">账号与设置</text>
        <view class="profile-list">
          <button class="profile-list__item tl-pressable" @click="openSettings">
            <view class="profile-list__copy"><text>账号与设置</text><text>管理隐私与账户</text></view>
            <text class="profile-list__arrow" aria-hidden="true">›</text>
          </button>
        </view>
      </view>
    </view>
    <AppTabbar active="profile" />
  </view>
</template>

<script>
import AppTabbar from '../../components/AppTabbar.vue'
import { getChildAvatar } from '../../constants/childAvatars.js'
import { useChildStore } from '../../stores/child'
import { useUserStore } from '../../stores/user'
import { endUserSession } from '../../utils/sessionBoundary'
import AppSkeleton from '../../components/ui/AppSkeleton.vue'
import PageState from '../../components/ui/PageState.vue'

export default {
  components: { AppSkeleton, AppTabbar, PageState },
  computed: {
    child() { return useChildStore() },
    user() { return useUserStore() },
    activeChild() { return this.child.activeChild },
    childInitial() { return String(this.activeChild?.name || '孩').trim().slice(0, 1) || '孩' },
    ageText() { return Number.isInteger(this.activeChild?.age) ? `${this.activeChild.age}岁` : '' },
    canSwitchChild() { return this.child.children.length > 1 },
    hasRetainedChild() {
      return Boolean(this.activeChild)
        && String(this.child.loadedForUserId) === String(this.user.userInfo?.id)
    },
    isInitialChildLoading() {
      return (this.child.isLoading || (!this.child.isLoaded && !this.child.error)) && !this.hasRetainedChild
    },
    isChildEmpty() {
      return this.child.isLoaded && !this.child.isLoading && !this.child.error && this.child.children.length === 0
    },
    showFullChildError() { return Boolean(this.child.error) && !this.hasRetainedChild },
    showChildRefreshError() { return Boolean(this.child.error) && this.hasRetainedChild },
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
    showToast(title) { uni.showToast({ title, icon: 'none' }) },
    async loadChildren() {
      try {
        await this.child.fetchChildren(this.user.userInfo.id)
      } catch (error) {
        if (['UNAUTHORIZED', 'INVALID_TOKEN', 'TOKEN_EXPIRED'].includes(error?.code) || error?.statusCode === 401) {
          await endUserSession()
        }
      }
    },
    childAvatar(candidate) { return getChildAvatar(candidate?.avatarPreset) },
    openChildSwitcher() {
      if (!this.canSwitchChild) {
        this.showToast('添加更多孩子后即可切换')
        return
      }
      uni.navigateTo({ url: '/pages/child-switch/index' })
    },
    openSettings() { uni.navigateTo({ url: '/pages/settings/index' }) },
    openManageChild() { this.openChildEdit(this.activeChild?.id) },
    openChildEdit(childId = null) {
      const suffix = Number.isInteger(childId) && childId > 0 ? `?id=${encodeURIComponent(childId)}` : ''
      uni.navigateTo({ url: `/pages/child-edit/index${suffix}` })
    },
  },
}
</script>

<style scoped>
.profile-page { min-height: 100vh; color: var(--tl-text-main); background: var(--tl-bg); }.profile-page__paper { width: 100%; max-width: var(--tl-content-max-width); min-height: 100vh; padding: calc(var(--tl-page-padding) + var(--tl-safe-top)) var(--tl-page-padding) calc(var(--tl-tabbar-height) + var(--tl-safe-bottom) + 40rpx); margin: 0 auto; box-sizing: border-box; }
.profile-header { display: flex; align-items: flex-start; justify-content: space-between; margin-bottom: 40rpx; }.profile-header__title,.profile-header__subtitle { display: block; }.profile-header__title { font-size: var(--tl-type-page-title); font-weight: var(--tl-weight-page-title); line-height: 1.25; }.profile-header__subtitle { margin-top: 10rpx; font-size: var(--tl-type-body); line-height: 1.5; color: var(--tl-text-secondary); }.profile-header__settings { display: flex; align-items: center; justify-content: center; width: 88rpx; min-width: 88rpx; height: 88rpx; }.profile-header__settings-icon { position: relative; width: 34rpx; height: 34rpx; border: 4rpx solid #315248; border-radius: 50%; }.profile-header__settings-icon::before,.profile-header__settings-icon::after { position: absolute; inset: -9rpx; content: ''; border: 3rpx solid #315248; border-radius: 10rpx; transform: rotate(45deg); }.profile-header__settings-icon::after { inset: 8rpx; background: var(--tl-bg); border: 0; border-radius: 50%; }
.profile-child-skeleton { height: 164rpx; }.profile-page__paper > .page-state { min-height: 300rpx; padding-right: 0; padding-left: 0; }.profile-refresh-error { display: flex; gap: var(--tl-space-sm); align-items: center; justify-content: space-between; min-height: var(--tl-touch-target); padding: var(--tl-space-xs) 0; margin-bottom: var(--tl-space-sm); font-size: var(--tl-type-meta); line-height: 1.5; color: var(--tl-primary-deep); border-bottom: 1rpx solid var(--tl-divider); }.profile-refresh-error__retry { flex: 0 0 auto; min-width: var(--tl-touch-target); min-height: var(--tl-touch-target); color: inherit; text-decoration: underline; }
.active-child { border-top: 1rpx solid var(--tl-divider); border-bottom: 1rpx solid var(--tl-divider); }.active-child__identity { display: flex; align-items: center; width: 100%; min-height: 164rpx; padding: 26rpx 0; color: var(--tl-text-main); text-align: left; background: transparent; }.active-child__avatar { display: flex; flex: 0 0 104rpx; align-items: center; justify-content: center; width: 104rpx; height: 104rpx; margin-right: 24rpx; overflow: hidden; font-size: 42rpx; font-weight: 600; color: #fff; background: #315248; border-radius: 50%; }.active-child__avatar image { width: 100%; height: 100%; }.active-child__copy { flex: 1; min-width: 0; }.active-child__name,.active-child__meta { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.active-child__name { font-size: 34rpx; font-weight: 700; }.active-child__meta { margin-top: 10rpx; font-size: var(--tl-type-meta); color: var(--tl-text-secondary); }.active-child__arrow,.profile-list__arrow { flex: 0 0 auto; font-size: 42rpx; color: var(--tl-text-secondary); }.active-child__actions { display: flex; gap: 14rpx; padding: 0 0 26rpx; }.active-child__action { flex: 1; min-height: var(--tl-touch-target); font-size: var(--tl-type-meta); color: #17673c; background: transparent; border: 1rpx solid #1f7b47; border-radius: var(--tl-radius-control); }.active-child__action--primary { color: #fff; background: #1f7b47; }
.profile-section { margin-top: 54rpx; }.profile-section--last { margin-bottom: 30rpx; }.profile-section__title { display: block; margin-bottom: 16rpx; font-size: var(--tl-type-body); font-weight: var(--tl-weight-section-title); }.profile-list { border-top: 1rpx solid var(--tl-divider); }.profile-list__item { display: flex; gap: 18rpx; align-items: center; width: 100%; min-height: 122rpx; padding: 20rpx 0; color: var(--tl-text-main); text-align: left; background: transparent; border-bottom: 1rpx solid var(--tl-divider); }.profile-list__copy { flex: 1; min-width: 0; }.profile-list__copy text { display: block; }.profile-list__copy text:first-child { font-size: var(--tl-type-body); font-weight: 600; }.profile-list__copy text:last-child { margin-top: 7rpx; overflow: hidden; font-size: var(--tl-type-meta); color: var(--tl-text-secondary); text-overflow: ellipsis; white-space: nowrap; }
@media (min-width: 431px) { .profile-page__paper { padding: calc(18px + var(--tl-safe-top)) 18px calc(var(--tl-tabbar-height) + var(--tl-safe-bottom) + 20px); }.profile-header { margin-bottom: 20px; }.profile-header__settings { width: 44px; min-width: 44px; height: 44px; }.profile-header__settings-icon { width: 17px; height: 17px; }.active-child__identity { min-height: 82px; padding: 13px 0; }.active-child__avatar { flex-basis: 52px; width: 52px; height: 52px; margin-right: 12px; font-size: 21px; }.active-child__actions { gap: 7px; padding-bottom: 13px; }.active-child__action { min-height: 44px; }.profile-section { margin-top: 27px; }.profile-list__item { min-height: 61px; padding: 10px 0; }.active-child__arrow,.profile-list__arrow { font-size: 21px; } }
</style>
