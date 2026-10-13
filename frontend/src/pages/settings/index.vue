<template>
  <view class="settings-page">
    <view class="settings-page__paper">
      <view class="settings-header">
        <button class="settings-header__back" aria-label="返回" @click="goBack">‹</button>
        <text>账号与设置</text>
        <view></view>
      </view>

      <view class="settings-list">
        <button class="settings-row" @click="showUnavailable('账号信息暂不支持编辑')">
          <view class="settings-row__icon settings-row__icon--account" aria-hidden="true"></view>
          <view class="settings-row__copy"><text>账号信息</text><text>查看当前登录账号</text></view>
          <text class="settings-row__arrow" aria-hidden="true">›</text>
        </button>
        <button class="settings-row" @click="showUnavailable('关于童旅记')">
          <view class="settings-row__icon settings-row__icon--about" aria-hidden="true"></view>
          <view class="settings-row__copy"><text>关于童旅记</text><text>亲子旅行学习 App</text></view>
          <text class="settings-row__arrow" aria-hidden="true">›</text>
        </button>
      </view>

      <button class="settings-logout" @click="logout"><text aria-hidden="true">↪</text>退出登录</button>
    </view>
    <AppTabbar active="profile" />
  </view>
</template>

<script>
import AppTabbar from '../../components/AppTabbar.vue'
import { useUserStore } from '../../stores/user'
import { endUserSession } from '../../utils/sessionBoundary'

export default {
  components: { AppTabbar },
  computed: { user() { return useUserStore() } },
  async onShow() {
    await this.user.restoreSession()
    if (!this.user.isLoggedIn) uni.reLaunch({ url: '/pages/login/index' })
  },
  methods: {
    goBack() { uni.navigateBack() },
    showUnavailable(title) { uni.showToast({ title, icon: 'none' }) },
    async logout() { await endUserSession() },
  },
}
</script>

<style scoped>
.settings-page { min-height: 100vh; color: var(--tl-text-main); background: var(--tl-bg); }.settings-page__paper { width: 100%; max-width: var(--tl-content-max-width); min-height: 100vh; padding: calc(var(--tl-page-padding) + var(--tl-safe-top)) var(--tl-page-padding) calc(var(--tl-tabbar-height) + var(--tl-safe-bottom) + 40rpx); margin: 0 auto; }.settings-header { display: grid; grid-template-columns: 88rpx 1fr 88rpx; align-items: center; min-height: 88rpx; margin-bottom: 40rpx; text-align: center; }.settings-header > text { font-size: var(--tl-type-section-title); font-weight: 700; }.settings-header__back { min-height: 88rpx; font-size: 58rpx; font-weight: 300; color: var(--tl-text-main); text-align: left; }
.settings-list { overflow: hidden; background: var(--tl-surface); border: 1rpx solid var(--tl-divider); border-radius: var(--tl-radius-media); box-shadow: var(--tl-shadow-media); }.settings-row { display: flex; align-items: center; width: 100%; min-height: 126rpx; padding: 20rpx 24rpx; color: var(--tl-text-main); text-align: left; }.settings-row + .settings-row { border-top: 1rpx solid var(--tl-divider); }.settings-row__icon { position: relative; flex: 0 0 54rpx; width: 54rpx; height: 54rpx; margin-right: 20rpx; color: #315248; }.settings-row__icon::before,.settings-row__icon::after { position: absolute; box-sizing: border-box; content: ''; }.settings-row__icon--account::before { top: 2rpx; left: 16rpx; width: 20rpx; height: 20rpx; border: 3rpx solid currentColor; border-radius: 50%; }.settings-row__icon--account::after { bottom: 2rpx; left: 7rpx; width: 38rpx; height: 24rpx; border: 3rpx solid currentColor; border-bottom: 0; border-radius: 24rpx 24rpx 0 0; }.settings-row__icon--about::before { width: 38rpx; height: 46rpx; margin: 4rpx 8rpx; border: 3rpx solid currentColor; border-radius: 6rpx; }.settings-row__icon--about::after { top: 15rpx; left: 18rpx; width: 18rpx; height: 3rpx; background: currentColor; box-shadow: 0 10rpx 0 currentColor; }.settings-row__copy { flex: 1; min-width: 0; }.settings-row__copy text { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.settings-row__copy text:first-child { font-size: var(--tl-type-body); font-weight: 600; }.settings-row__copy text:last-child { margin-top: 7rpx; font-size: var(--tl-type-meta); color: var(--tl-text-secondary); }.settings-row__arrow { margin-left: 16rpx; font-size: 42rpx; font-weight: 300; color: var(--tl-text-secondary); }.settings-logout { display: flex; gap: 12rpx; align-items: center; justify-content: center; width: 100%; min-height: var(--tl-control-min-height); margin-top: 38rpx; font-size: var(--tl-type-primary-action); font-weight: 600; color: #c94b3b; background: #fff0ed; border-radius: var(--tl-radius-control); }.settings-logout text { font-size: 36rpx; }
@media (min-width: 431px) { .settings-page__paper { padding: calc(18px + var(--tl-safe-top)) 18px calc(var(--tl-tabbar-height) + var(--tl-safe-bottom) + 22px); }.settings-header { grid-template-columns: 44px 1fr 44px; min-height: 44px; margin-bottom: 20px; }.settings-header__back { min-height: 44px; }.settings-row { min-height: 63px; padding: 10px 12px; }.settings-row__icon { flex-basis: 27px; width: 27px; height: 27px; margin-right: 10px; }.settings-logout { min-height: 44px; margin-top: 19px; } }
</style>
