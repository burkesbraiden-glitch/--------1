<template>
  <view class="explore-center-page">
    <view class="explore-center-page__paper">
      <view class="center-header">
        <view class="center-header__seal">✦</view>
        <view class="center-header__copy">
          <text class="center-header__eyebrow">TRAVEL NOTEBOOK</text>
          <text class="center-header__title">探索中心</text>
        </view>
        <view class="center-header__leaf">❋</view>
      </view>

      <view class="center-intro">
        <text class="center-intro__title">把每一次出发，变成新的发现</text>
        <text class="center-intro__note">选择一份探索计划，和孩子继续这段旅程。</text>
      </view>

      <view v-if="isPageLoading" class="center-state-card">
        <text class="center-state-card__stamp">正在整理</text>
        <text class="center-state-card__title">正在加载探索计划...</text>
      </view>

      <view v-else-if="planStore.error" class="center-state-card">
        <text class="center-state-card__stamp">小小提醒</text>
        <text class="center-state-card__title">探索计划加载失败</text>
        <text class="center-state-card__action" @click="loadPlans(true)">重新试一次</text>
      </view>

      <view v-else-if="!planStore.plans.length" class="center-state-card">
        <text class="center-state-card__stamp">空白一页</text>
        <text class="center-state-card__title">还没有探索计划</text>
        <text class="center-state-card__note">先去首页创建一次亲子探索吧。</text>
        <text class="center-state-card__action" @click="goHome">去首页看看</text>
      </view>

      <view v-else class="plan-list">
        <view
          v-for="plan in planStore.plans"
          :key="plan.id"
          class="plan-card"
          @click="openPlan(plan)"
        >
          <view class="plan-card__tape"></view>
          <view class="plan-card__topline">
            <text class="plan-card__eyebrow">探索计划</text>
            <text class="plan-card__status">{{ statusText(plan.status) }}</text>
          </view>
          <text class="plan-card__title">{{ plan.title }}</text>
          <view class="plan-card__destination">
            <text class="plan-card__destination-label">目的地</text>
            <text class="plan-card__destination-value">{{ plan.destination }}</text>
          </view>
          <view class="plan-card__progress">
            <view class="plan-card__progress-copy">
              <text>探索进度</text>
              <text>{{ plan.progress?.completed || 0 }}/{{ plan.progress?.total || 0 }}</text>
            </view>
            <view class="plan-card__progress-track">
              <view class="plan-card__progress-fill" :style="{ width: progressWidth(plan) }"></view>
            </view>
          </view>
          <view class="plan-card__source">
            <text class="plan-card__source-label">来源</text>
            <text class="plan-card__source-value">{{ sourceLabel(plan) }}</text>
          </view>
          <text class="plan-card__action">{{ actionText(plan.status) }} ›</text>
        </view>
      </view>
    </view>

    <AppTabbar active="explore" />
  </view>
</template>

<script>
import AppTabbar from '../../components/AppTabbar.vue'
import { usePlanStore } from '../../stores/plan'
import { useUserStore } from '../../stores/user'
import { ensureCurrentPlanReady } from '../../utils/planRecovery'
import { endUserSession } from '../../utils/sessionBoundary'

export default {
  components: { AppTabbar },
  computed: {
    planStore() {
      return usePlanStore()
    },
    userStore() {
      return useUserStore()
    },
    isPageLoading() {
      return this.userStore.isRestoring || this.planStore.isLoading
    },
  },
  async onShow() {
    await this.loadPlans(true)
  },
  methods: {
    async handleAuthExpired() {
      await endUserSession()
    },
    async loadPlans(force = false) {
      try {
        const result = await ensureCurrentPlanReady({ withTasks: false, force })
        if (!result.user) {
          uni.reLaunch({ url: '/pages/login/index' })
        }
      } catch (error) {
        if (['UNAUTHORIZED', 'TOKEN_EXPIRED', 'INVALID_TOKEN'].includes(error?.code) || error?.statusCode === 401) {
          await this.handleAuthExpired()
        }
      }
    },
    statusText(status) {
      return {
        ready: '准备出发',
        'in-progress': '探索中',
        completed: '已完成',
      }[status] || status || ''
    },
    actionText(status) {
      if (status === 'completed') return '查看任务'
      return status === 'in-progress' ? '继续探索' : '开始探索'
    },
    sourceLabel(plan) {
      return plan.sourceSnapshot?.route?.title
        || plan.sourceSnapshot?.attraction?.name
        || (plan.sourceSnapshot ? '路线生成' : '手动创建')
    },
    progressWidth(plan) {
      const total = Number(plan.progress?.total) || 0
      const completed = Number(plan.progress?.completed) || 0
      return total ? `${Math.min(100, Math.round((completed / total) * 100))}%` : '0%'
    },
    openPlan(plan) {
      const selectedPlan = this.planStore.selectPlanById(plan.id)
      if (!selectedPlan) return
      uni.navigateTo({
        url: `/pages/explore-detail/index?planId=${plan.id}`,
      })
    },
    goHome() {
      uni.reLaunch({ url: '/pages/home/index' })
    },
  },
}
</script>

<style scoped>
.explore-center-page { min-height: 100vh; color: var(--tl-text-main); background: radial-gradient(circle at 10% 6%, rgba(255, 238, 183, .76), transparent 190rpx), radial-gradient(circle at 92% 18%, rgba(210, 232, 242, .58), transparent 160rpx), var(--tl-bg); }
.explore-center-page__paper { width: 100%; max-width: var(--tl-content-max-width); min-height: 100vh; margin: 0 auto; padding: calc(var(--tl-page-padding) + var(--tl-safe-top)) var(--tl-page-padding) calc(var(--tl-tabbar-height) + var(--tl-safe-bottom) + 52rpx); }
.center-header { display: flex; align-items: center; justify-content: space-between; min-height: 88rpx; }.center-header__seal,.center-header__leaf { width: 64rpx; font-size: 38rpx; color: var(--tl-primary); text-align: center; }.center-header__leaf { color: var(--tl-green-deep); transform: rotate(20deg); }.center-header__copy { display: flex; flex: 1; flex-direction: column; align-items: center; }.center-header__eyebrow { font-size: 16rpx; font-weight: 900; color: var(--tl-primary); letter-spacing: 3rpx; }.center-header__title { margin-top: 3rpx; font-size: 48rpx; font-weight: 900; }
.center-intro { margin: 24rpx 0 30rpx; padding: 28rpx; background: rgba(255, 251, 239, .84); border: 2rpx solid var(--tl-line); border-radius: var(--tl-radius-lg); box-shadow: var(--tl-shadow-card); }.center-intro__title,.center-intro__note { display: block; }.center-intro__title { font-size: 31rpx; font-weight: 900; }.center-intro__note { margin-top: 10rpx; font-size: 23rpx; line-height: 1.55; color: var(--tl-text-secondary); }
.center-state-card { padding: 54rpx 34rpx; text-align: center; background: var(--tl-paper); border: 3rpx dashed var(--tl-line); border-radius: var(--tl-radius-lg); box-shadow: var(--tl-shadow-card); }.center-state-card__stamp,.center-state-card__title,.center-state-card__note,.center-state-card__action { display: block; }.center-state-card__stamp { margin-bottom: 16rpx; font-size: 22rpx; font-weight: 900; color: var(--tl-primary-deep); }.center-state-card__title { font-size: 30rpx; font-weight: 800; }.center-state-card__note { margin-top: 10rpx; font-size: 23rpx; color: var(--tl-text-secondary); }.center-state-card__action { margin-top: 20rpx; font-size: 25rpx; font-weight: 800; color: var(--tl-primary-deep); text-decoration: underline; }
.plan-list { display: flex; flex-direction: column; gap: 22rpx; }.plan-card { position: relative; padding: 30rpx; overflow: hidden; background: var(--tl-paper); border: 2rpx solid var(--tl-line); border-radius: var(--tl-radius-lg); box-shadow: var(--tl-shadow-card); }.plan-card__tape { position: absolute; top: 15rpx; right: 42rpx; width: 92rpx; height: 24rpx; background: rgba(243, 205, 114, .62); transform: rotate(8deg); }.plan-card__topline,.plan-card__destination,.plan-card__progress-copy,.plan-card__source { display: flex; align-items: center; justify-content: space-between; gap: 16rpx; }.plan-card__eyebrow { font-size: 19rpx; font-weight: 900; color: var(--tl-primary-deep); letter-spacing: 2rpx; }.plan-card__status { padding: 8rpx 13rpx; font-size: 20rpx; font-weight: 800; color: var(--tl-green-deep); background: var(--tl-green); border-radius: 999rpx; }.plan-card__title { display: block; margin: 20rpx 0 22rpx; font-size: 37rpx; font-weight: 900; line-height: 1.25; }.plan-card__destination-label,.plan-card__source-label { flex: 0 0 auto; font-size: 21rpx; font-weight: 800; color: var(--tl-text-secondary); }.plan-card__destination-value,.plan-card__source-value { flex: 1; min-width: 0; overflow: hidden; font-size: 25rpx; font-weight: 800; text-align: right; text-overflow: ellipsis; white-space: nowrap; }.plan-card__progress { margin-top: 22rpx; padding: 18rpx; background: rgba(239, 247, 226, .76); border-radius: var(--tl-radius-sm); }.plan-card__progress-copy { font-size: 21rpx; font-weight: 800; color: var(--tl-green-deep); }.plan-card__progress-track { height: 12rpx; margin-top: 12rpx; overflow: hidden; background: rgba(111, 147, 83, .18); border-radius: 999rpx; }.plan-card__progress-fill { height: 100%; background: var(--tl-green-deep); border-radius: inherit; }.plan-card__source { margin-top: 20rpx; }.plan-card__source-value { color: var(--tl-primary-deep); }.plan-card__action { display: block; margin-top: 24rpx; font-size: 25rpx; font-weight: 900; color: var(--tl-primary); text-align: right; }
</style>
