<template>
  <view class="explore-detail-page">
    <view class="explore-detail-page__paper">
      <view class="detail-header">
        <button class="detail-header__back" @click="goCenter" aria-label="返回探索中心">‹</button>
        <view class="detail-header__copy">
          <text class="detail-header__eyebrow">TRAVEL NOTEBOOK</text>
          <text class="detail-header__title">探索详情</text>
        </view>
        <view class="detail-header__spacer"></view>
      </view>

      <view v-if="isPageLoading" class="detail-state-card">
        <text class="detail-state-card__stamp">正在整理</text>
        <text class="detail-state-card__title">正在打开这次探索...</text>
      </view>

      <view v-else-if="isPlanUnavailable" class="detail-state-card">
        <text class="detail-state-card__stamp">这页走丢了</text>
        <text class="detail-state-card__title">这份探索计划不存在，或暂时无法访问。</text>
        <text class="detail-state-card__action" @click="goCenter">返回探索中心</text>
      </view>

      <view v-else-if="planStore.error" class="detail-state-card">
        <text class="detail-state-card__stamp">小小提醒</text>
        <text class="detail-state-card__title">探索计划加载失败</text>
        <text class="detail-state-card__action" @click="restorePlan">重新试一次</text>
      </view>

      <view v-else-if="!displayPlan" class="detail-state-card">
        <text class="detail-state-card__stamp">空白一页</text>
        <text class="detail-state-card__title">这份探索计划暂时不可用。</text>
        <text class="detail-state-card__action" @click="goCenter">返回探索中心</text>
      </view>

      <template v-else>
        <view class="plan-hero">
          <view class="plan-hero__tape"></view>
          <view class="plan-hero__copy">
            <text class="plan-hero__kicker">本次亲子文化探索</text>
            <text class="plan-hero__title">{{ displayPlan.title }}</text>
            <view class="plan-hero__underline"></view>
            <text class="plan-hero__desc">和孩子一起，把好奇心装进旅行背包。</text>
            <view class="plan-hero__tags">
              <text class="plan-hero__tag plan-hero__tag--orange">{{ formattedAgeGroup }}</text>
              <text class="plan-hero__tag plan-hero__tag--blue">{{ formattedDuration }}</text>
              <text class="plan-hero__tag plan-hero__tag--green">{{ progressText }}</text>
            </view>
          </view>
          <image class="plan-hero__image" src="../../assets/plan/plan-cultural-watercolor.webp" mode="aspectFill" />
        </view>

        <view class="destination-card">
          <text class="destination-card__label">今天要去</text>
          <text class="destination-card__value">{{ displayPlan.destination }}</text>
          <text class="destination-card__status">{{ statusText }}</text>
        </view>

        <view class="interest-strip">
          <text class="interest-strip__label">探索关键词</text>
          <view class="interest-strip__items">
            <text v-for="interest in displayPlan.interests" :key="interest" class="interest-strip__item">{{ interest }}</text>
          </view>
        </view>

        <view class="section-heading">
          <text class="section-heading__title">随身探索清单</text>
          <text class="section-heading__note">准备好，就出发</text>
        </view>

        <view class="explore-sections">
          <view v-for="(section, index) in sections" :key="section.title" class="explore-section-card">
            <text class="explore-section-card__number">0{{ index + 1 }}</text>
            <view class="explore-section-card__content">
              <text class="explore-section-card__title">{{ section.title }}</text>
              <text class="explore-section-card__summary">{{ section.summary }}</text>
              <text class="explore-section-card__item">{{ section.items[0] }}</text>
            </view>
          </view>
        </view>

        <button class="detail-guide-action" @click="openGuide">查看景点讲解</button>
        <button class="detail-action" :disabled="isStarting" @click="startExploration">
          {{ isStarting ? '正在打开探索清单' : startActionText }}
        </button>
      </template>
    </view>

    <AppTabbar active="explore" />
  </view>
</template>

<script>
import AppTabbar from '../../components/AppTabbar.vue'
import { usePlanStore } from '../../stores/plan'
import { useTaskStore } from '../../stores/task'
import { useUserStore } from '../../stores/user'
import { ensureCurrentPlanReady } from '../../utils/planRecovery'
import { endUserSession } from '../../utils/sessionBoundary'

export default {
  components: { AppTabbar },
  data() {
    return {
      planId: '',
      isPlanUnavailable: false,
      isStarting: false,
      sections: [
        { title: '学习目标', summary: '认识眼前的地方', items: ['说说你发现了哪些特别的细节。'] },
        { title: '出发前准备', summary: '带着问题去旅行', items: ['准备好拍照和记录的小本子。'] },
        { title: '现场重点', summary: '慢慢看，仔细找', items: ['留意颜色、形状和有趣的标记。'] },
        { title: '亲子提问', summary: '分享你的新发现', items: ['你觉得这里以前发生过什么？'] },
      ],
    }
  },
  computed: {
    planStore() {
      return usePlanStore()
    },
    taskStore() {
      return useTaskStore()
    },
    userStore() {
      return useUserStore()
    },
    displayPlan() {
      return this.isPlanUnavailable ? null : this.planStore.currentPlan
    },
    isPageLoading() {
      return this.userStore.isRestoring || this.planStore.isLoading
    },
    formattedAgeGroup() {
      return `${this.displayPlan?.ageGroup || ''}岁`
    },
    formattedDuration() {
      return `约${this.displayPlan?.duration || ''}`
    },
    progressText() {
      const progress = this.displayPlan?.progress || { total: 0, completed: 0 }
      return `${progress.completed}/${progress.total} 个任务`
    },
    statusText() {
      const statusMap = { ready: '准备出发', 'in-progress': '探索中', completed: '已完成' }
      return statusMap[this.displayPlan?.status] || this.displayPlan?.status || ''
    },
    startActionText() {
      if (this.displayPlan?.status === 'completed') return '查看任务'
      return this.displayPlan?.status === 'in-progress' ? '继续探索' : '开始探索'
    },
  },
  onLoad(options) {
    this.planId = String(options?.planId || '').trim()
    this.isPlanUnavailable = !this.planId
  },
  async onShow() {
    if (this.planId) {
      await this.restorePlan()
    }
  },
  methods: {
    showToast(title) {
      uni.showToast({ title, icon: 'none' })
    },
    async handleAuthExpired() {
      await endUserSession()
    },
    async restorePlan() {
      try {
        const result = await ensureCurrentPlanReady({
          withTasks: false,
          force: true,
          planId: this.planId,
        })
        if (!result.user) {
          uni.reLaunch({ url: '/pages/login/index' })
          return
        }
        const selectedPlan = this.planStore.selectPlanById(this.planId)
        this.isPlanUnavailable = result.unavailable || !selectedPlan
      } catch (error) {
        if (['UNAUTHORIZED', 'TOKEN_EXPIRED', 'INVALID_TOKEN'].includes(error?.code) || error?.statusCode === 401) {
          await this.handleAuthExpired()
        }
      }
    },
    goCenter() {
      uni.reLaunch({ url: '/pages/plan/index' })
    },
    goTasks() {
      uni.reLaunch({ url: '/pages/tasks/index' })
    },
    openGuide() {
      const planId = this.displayPlan?.id
      if (planId === null || planId === undefined || String(planId).trim() === '') return

      uni.navigateTo({
        url: `/pages/guide/index?planId=${encodeURIComponent(String(planId))}`,
      })
    },
    async startExploration() {
      if (this.isStarting || !this.displayPlan) return

      this.isStarting = true
      try {
        let plan = this.displayPlan
        if (plan.status === 'ready') {
          plan = await this.planStore.startExploration(plan.id, this.userStore.userInfo?.id)
        }
        if (plan.status !== 'completed') {
          await this.taskStore.ensureTasks(plan.id, plan.status)
        }
        this.goTasks()
      } catch (error) {
        if (['UNAUTHORIZED', 'TOKEN_EXPIRED', 'INVALID_TOKEN'].includes(error?.code) || error?.statusCode === 401) {
          await this.handleAuthExpired()
          return
        }
        this.showToast(error?.message || '无法打开探索清单，请稍后重试')
      } finally {
        this.isStarting = false
      }
    },
  },
}
</script>

<style scoped>
.explore-detail-page { min-height: 100vh; color: var(--tl-text-main); background: radial-gradient(circle at 8% 10%, rgba(255, 236, 187, .72), transparent 180rpx), var(--tl-bg); }
.explore-detail-page__paper { width: 100%; max-width: var(--tl-content-max-width); min-height: 100vh; margin: 0 auto; padding: calc(var(--tl-page-padding) + var(--tl-safe-top)) var(--tl-page-padding) calc(var(--tl-tabbar-height) + var(--tl-safe-bottom) + 52rpx); }
.detail-header { display: flex; align-items: center; justify-content: space-between; min-height: 86rpx; margin-bottom: 30rpx; }
.detail-header__back,.detail-header__spacer { flex: 0 0 64rpx; width: 64rpx; height: 64rpx; }
.detail-header__back { padding: 0 0 8rpx; font-size: 64rpx; line-height: 1; color: var(--tl-text-main); background: transparent; }
.detail-header__copy { display: flex; flex: 1; flex-direction: column; align-items: center; }
.detail-header__eyebrow { font-size: 16rpx; font-weight: 800; color: var(--tl-primary); letter-spacing: 3rpx; }
.detail-header__title { font-size: 46rpx; font-weight: 900; }
.detail-state-card { padding: 54rpx 34rpx; text-align: center; background: var(--tl-paper); border: 3rpx dashed var(--tl-line); border-radius: var(--tl-radius-lg); box-shadow: var(--tl-shadow-card); }
.detail-state-card__stamp,.detail-state-card__title,.detail-state-card__action { display: block; }
.detail-state-card__stamp { margin-bottom: 16rpx; font-size: 22rpx; font-weight: 900; color: var(--tl-primary-deep); }
.detail-state-card__title { font-size: 30rpx; font-weight: 800; }
.detail-state-card__action { margin-top: 20rpx; font-size: 25rpx; font-weight: 800; color: var(--tl-primary-deep); text-decoration: underline; }
.plan-hero { position: relative; min-height: 394rpx; margin-bottom: 22rpx; overflow: hidden; background: var(--tl-paper); border: 3rpx solid var(--tl-line); border-radius: var(--tl-radius-lg); box-shadow: var(--tl-shadow-card); }
.plan-hero__copy { position: relative; z-index: 2; width: 58%; padding: 48rpx 12rpx 24rpx 30rpx; }
.plan-hero__tape { position: absolute; top: 18rpx; right: 48rpx; z-index: 3; width: 104rpx; height: 28rpx; background: rgba(243, 205, 114, .66); transform: rotate(8deg); }
.plan-hero__image { position: absolute; top: 0; right: 0; width: 54%; height: 100%; }
.plan-hero__kicker { display: block; font-size: 20rpx; font-weight: 800; color: var(--tl-primary-deep); letter-spacing: 2rpx; }
.plan-hero__title { display: block; margin-top: 12rpx; font-size: 44rpx; font-weight: 900; line-height: 1.22; }
.plan-hero__underline { width: 84rpx; height: 8rpx; margin: 18rpx 0; background: var(--tl-primary); border-radius: 99rpx; }
.plan-hero__desc { display: block; max-width: 286rpx; font-size: 25rpx; line-height: 1.6; color: var(--tl-text-secondary); }
.plan-hero__tags { display: flex; flex-wrap: wrap; gap: 9rpx; margin-top: 22rpx; }
.plan-hero__tag { padding: 8rpx 12rpx; font-size: 19rpx; font-weight: 800; border-radius: 18rpx; }
.plan-hero__tag--orange { color: var(--tl-primary-deep); background: #fff0d2; }.plan-hero__tag--blue { color: var(--tl-blue-deep); background: var(--tl-blue); }.plan-hero__tag--green { color: var(--tl-green-deep); background: var(--tl-green); }
.destination-card,.explore-section-card { background: var(--tl-paper); border: 2rpx solid var(--tl-line); border-radius: var(--tl-radius-md); box-shadow: 0 8rpx 14rpx rgba(92, 60, 29, .05); }
.destination-card { display: flex; gap: 12rpx; align-items: center; padding: 20rpx; }
.destination-card__label { flex: 0 0 auto; font-size: 21rpx; color: var(--tl-text-secondary); }.destination-card__value { flex: 1; min-width: 0; overflow: hidden; font-size: 30rpx; font-weight: 900; text-overflow: ellipsis; white-space: nowrap; }.destination-card__status { padding: 8rpx 12rpx; font-size: 20rpx; font-weight: 800; color: var(--tl-green-deep); background: var(--tl-green); border-radius: 999rpx; }
.interest-strip { display: flex; gap: 12rpx; margin: 20rpx 4rpx 30rpx; }.interest-strip__label { flex: 0 0 auto; padding-top: 7rpx; font-size: 21rpx; font-weight: 800; color: var(--tl-text-secondary); }.interest-strip__items { display: flex; flex: 1; flex-wrap: wrap; gap: 8rpx; }.interest-strip__item { padding: 7rpx 13rpx; font-size: 20rpx; font-weight: 800; color: var(--tl-blue-deep); background: rgba(210, 232, 242, .72); border-radius: 999rpx; }
.section-heading { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 16rpx; padding: 0 6rpx; }.section-heading__title { font-size: 34rpx; font-weight: 900; }.section-heading__note { font-size: 20rpx; color: var(--tl-text-secondary); }
.explore-sections { display: flex; flex-direction: column; gap: 16rpx; }.explore-section-card { position: relative; padding: 22rpx 28rpx 22rpx 78rpx; }.explore-section-card__number { position: absolute; top: 22rpx; left: 24rpx; font-size: 24rpx; font-weight: 900; color: var(--tl-primary); }.explore-section-card__title,.explore-section-card__summary,.explore-section-card__item { display: block; }.explore-section-card__title { font-size: 30rpx; font-weight: 900; }.explore-section-card__summary { margin-top: 6rpx; font-size: 24rpx; color: var(--tl-text-secondary); }.explore-section-card__item { margin-top: 10rpx; font-size: 20rpx; color: var(--tl-primary-deep); }
.detail-guide-action { width: 100%; min-height: 88rpx; margin-top: 30rpx; font-size: 28rpx; font-weight: 900; color: var(--tl-primary-deep); background: #fff3d9; border: 3rpx solid var(--tl-primary); border-radius: var(--tl-radius-md); }
.detail-action { width: 100%; min-height: 100rpx; margin-top: 24rpx; font-size: 32rpx; font-weight: 900; color: var(--tl-paper); background: var(--tl-primary); border: 3rpx solid var(--tl-primary-deep); border-radius: var(--tl-radius-md); box-shadow: 0 12rpx 0 var(--tl-primary-deep); }.detail-action[disabled] { opacity: .7; }
</style>
