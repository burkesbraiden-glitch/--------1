<template>
  <view class="plan-page">
    <view class="plan-page__paper">
      <view class="plan-header">
        <button class="plan-header__back" @click="goHome" aria-label="返回首页">‹</button>
        <view class="plan-header__title-wrap">
          <text class="plan-header__eyebrow">TRAVEL NOTEBOOK</text>
          <text class="plan-header__title">探索计划</text>
        </view>
        <view class="plan-header__spacer"></view>
      </view>

      <view v-if="isPageLoading" class="plan-state-card">
        <text class="plan-state-card__stamp">正在整理</text>
        <text class="plan-state-card__title">正在加载探索计划...</text>
      </view>

      <view v-else-if="planStore.error" class="plan-state-card">
        <text class="plan-state-card__stamp">小小提醒</text>
        <text class="plan-state-card__title">计划加载失败</text>
        <text class="plan-state-card__action" @click="loadPlans(true)">重新试一次</text>
      </view>

      <view v-else-if="!displayPlan" class="plan-state-card">
        <text class="plan-state-card__stamp">空白一页</text>
        <text class="plan-state-card__title">还没有探索计划</text>
        <text class="plan-state-card__action" @click="goHome">先去首页创建一次亲子探索吧</text>
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
              <view class="plan-hero__tag plan-hero__tag--orange">
                <view class="plan-hero__tag-mark plan-hero__tag-mark--age" aria-hidden="true"></view>
                <text>{{ formattedAgeGroup }}</text>
              </view>
              <view class="plan-hero__tag plan-hero__tag--blue">
                <view class="plan-hero__tag-mark plan-hero__tag-mark--time" aria-hidden="true"></view>
                <text>{{ formattedDuration }}</text>
              </view>
              <view class="plan-hero__tag plan-hero__tag--green">
                <view class="plan-hero__tag-mark plan-hero__tag-mark--tasks" aria-hidden="true"></view>
                <text>{{ realTaskCount }}个</text>
              </view>
            </view>
          </view>

          <view class="plan-hero__art">
            <image class="plan-hero__image" src="../../assets/plan/plan-cultural-watercolor.webp" mode="aspectFill" />
            <view class="plan-hero__postmark">出发</view>
          </view>
        </view>

        <view class="plan-destination-card">
          <view class="plan-destination-card__pin"></view>
          <view class="plan-destination-card__copy">
            <text class="plan-destination-card__label">今天要去</text>
            <text class="plan-destination-card__value">{{ displayPlan.destination }}</text>
          </view>
          <view class="plan-destination-card__status">{{ statusText }}</view>
        </view>

        <view class="plan-interest-strip">
          <text class="plan-interest-strip__label">探索关键词</text>
          <view class="plan-interest-strip__items">
            <text v-for="interest in displayPlan.interests" :key="interest" class="plan-interest-strip__item">{{ interest }}</text>
          </view>
        </view>

        <view class="plan-section-heading">
          <text class="plan-section-heading__title">随身探索清单</text>
          <text class="plan-section-heading__note">准备好，就出发</text>
        </view>

        <view class="plan-sections">
          <view
            v-for="(section, index) in sections"
            :key="section.title"
            class="plan-section-card"
            :class="`plan-section-card--${section.theme}`"
          >
            <view class="plan-section-card__number">0{{ index + 1 }}</view>
            <view class="plan-section-card__art">
              <view class="plan-section-card__paper"></view>
              <view class="plan-section-card__mark"></view>
            </view>
            <view class="plan-section-card__content">
              <text class="plan-section-card__title">{{ section.title }}</text>
              <text class="plan-section-card__summary">{{ section.summary }}</text>
              <view class="plan-section-card__items">
                <text v-for="item in section.items.slice(0, 2)" :key="item" class="plan-section-card__item">{{ item }}</text>
              </view>
            </view>
            <text class="plan-section-card__arrow">›</text>
          </view>
        </view>

        <button class="plan-start" :disabled="isStarting" @click="startExploration">
          <text class="plan-start__dot"></text>
          <text>{{ isStarting ? '正在打开探索清单' : '开始今天的探索' }}</text>
          <view class="plan-start__star" aria-hidden="true"></view>
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
  components: {
    AppTabbar,
  },
  data() {
    return {
      isStarting: false,
      sections: [
        {
          title: '学习目标',
          summary: '认识皇宫是什么地方',
          theme: 'book',
          items: ['认识古代皇宫里的生活', '发现古建筑中的礼仪和智慧', '学会认真观察并主动表达'],
        },
        {
          title: '出发前准备',
          summary: '提前了解，轻装出发',
          theme: 'bag',
          items: ['提前了解故宫是什么地方', '提醒孩子留意屋顶和宫门', '准备拍照和简单记录'],
        },
        {
          title: '现场重点',
          summary: '看屋顶、宫门、台阶',
          theme: 'palace',
          items: ['屋顶上的小兽', '红色宫门', '宫殿布局', '建筑颜色'],
        },
        {
          title: '亲子提问',
          summary: '你觉得谁会住在这里？',
          theme: 'question',
          items: ['你觉得屋顶上的小兽在做什么？', '为什么宫门这么高？', '你最喜欢哪一种建筑颜色？'],
        },
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
      return this.planStore.currentPlan
    },
    isPageLoading() {
      return this.userStore.isRestoring || this.planStore.isLoading || this.taskStore.isLoading
    },
    realTaskCount() {
      return Number(this.displayPlan?.taskCount) || this.taskStore.currentPlanTasks.length || 0
    },
    formattedAgeGroup() {
      return `${this.displayPlan?.ageGroup || ''}岁`
    },
    formattedDuration() {
      return `约${this.displayPlan?.duration || ''}`
    },
    statusText() {
      const statusMap = {
        ready: '准备出发',
        'in-progress': '探索中',
        completed: '已完成',
      }
      return statusMap[this.displayPlan?.status] || this.displayPlan?.status || ''
    },
  },
  async onShow() {
    await this.loadPlans()
  },
  methods: {
    showToast(title) {
      uni.showToast({
        title,
        icon: 'none',
      })
    },
    async handleAuthExpired() {
      await endUserSession()
    },
    async loadPlans(force = false) {
      try {
        const result = await ensureCurrentPlanReady({ withTasks: true, force })
        if (!result.user) {
          uni.reLaunch({
            url: '/pages/login/index',
          })
          return
        }
      } catch (error) {
        if (['UNAUTHORIZED', 'TOKEN_EXPIRED', 'INVALID_TOKEN'].includes(error?.code) || error?.statusCode === 401) {
          await this.handleAuthExpired()
        }
      }
    },
    goHome() {
      uni.reLaunch({
        url: '/pages/home/index',
      })
    },
    async startExploration() {
      if (this.isStarting || !this.displayPlan) {
        return
      }

      this.isStarting = true
      try {
        await this.taskStore.ensureTasks(this.displayPlan.id, this.displayPlan.status)
        const startedPlan = await this.planStore.startExploration(this.displayPlan.id, this.userStore.userInfo.id)
        await this.taskStore.ensureTasks(startedPlan.id, startedPlan.status)
        uni.reLaunch({
          url: '/pages/tasks/index',
        })
      } catch (error) {
        if (['UNAUTHORIZED', 'TOKEN_EXPIRED', 'INVALID_TOKEN'].includes(error?.code) || error?.statusCode === 401) {
          await this.handleAuthExpired()
          return
        }
        this.showToast(error?.message || '无法开始探索，请稍后重试')
      } finally {
        this.isStarting = false
      }
    },
  },
}
</script>

<style scoped>
.plan-page {
  min-height: 100vh;
  overflow-x: hidden;
  color: var(--tl-text-main);
  background:
    radial-gradient(circle at 9% 8%, rgba(255, 239, 184, 0.72) 0, rgba(255, 239, 184, 0) 180rpx),
    linear-gradient(135deg, rgba(141, 101, 49, 0.04) 0 1rpx, transparent 1rpx 24rpx),
    var(--tl-bg);
}

.plan-page__paper {
  width: 100%;
  max-width: var(--tl-content-max-width);
  min-height: 100vh;
  margin: 0 auto;
  padding: calc(var(--tl-page-padding) + var(--tl-safe-top)) var(--tl-page-padding) calc(var(--tl-tabbar-height) + var(--tl-safe-bottom) + 56rpx);
}

.plan-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 86rpx;
  margin-bottom: 30rpx;
}

.plan-header__back,
.plan-header__spacer {
  display: flex;
  flex: 0 0 64rpx;
  align-items: center;
  justify-content: center;
  width: 64rpx;
  height: 64rpx;
}

.plan-header__back {
  padding: 0 0 8rpx;
  font-size: 64rpx;
  font-weight: 500;
  line-height: 1;
  color: var(--tl-text-main);
  background: transparent;
}

.plan-header__title-wrap {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
}

.plan-header__eyebrow {
  margin-bottom: 5rpx;
  font-size: 16rpx;
  font-weight: 800;
  color: var(--tl-primary);
  letter-spacing: 3rpx;
}

.plan-header__title {
  position: relative;
  font-size: 48rpx;
  font-weight: 900;
  line-height: 1.1;
  color: var(--tl-text-main);
}

.plan-header__title::after {
  display: inline-block;
  width: 14rpx;
  height: 14rpx;
  margin: 0 0 18rpx 10rpx;
  content: '';
  background: var(--tl-yellow);
  border: 3rpx solid var(--tl-primary);
  border-radius: 4rpx 12rpx;
  transform: rotate(28deg);
}

.plan-state-card {
  padding: 52rpx 36rpx;
  text-align: center;
  background: var(--tl-paper);
  border: 3rpx dashed var(--tl-line);
  border-radius: var(--tl-radius-lg);
  box-shadow: var(--tl-shadow-card);
}

.plan-state-card__stamp {
  display: inline-flex;
  margin-bottom: 16rpx;
  padding: 8rpx 18rpx;
  font-size: 22rpx;
  font-weight: 900;
  color: var(--tl-primary-deep);
  background: var(--tl-yellow);
  border: 2rpx solid var(--tl-primary);
  border-radius: var(--tl-radius-sm);
  transform: rotate(-3deg);
}

.plan-state-card__title {
  display: block;
  font-size: 32rpx;
  font-weight: 800;
}

.plan-state-card__action {
  display: inline-block;
  margin-top: 20rpx;
  padding-bottom: 4rpx;
  font-size: 26rpx;
  font-weight: 800;
  color: var(--tl-primary-deep);
  border-bottom: 2rpx solid currentColor;
}

.plan-hero {
  position: relative;
  display: flex;
  min-height: 394rpx;
  margin-bottom: 22rpx;
  overflow: hidden;
  background: var(--tl-paper);
  border: 3rpx solid var(--tl-line);
  border-radius: var(--tl-radius-lg);
  box-shadow: var(--tl-shadow-card);
}

.plan-hero::before {
  position: absolute;
  top: -56rpx;
  left: -30rpx;
  width: 180rpx;
  height: 180rpx;
  content: '';
  background: rgba(255, 235, 170, 0.42);
  border-radius: 50%;
}

.plan-hero__tape {
  position: absolute;
  top: 18rpx;
  right: 48rpx;
  z-index: 3;
  width: 104rpx;
  height: 28rpx;
  background: rgba(243, 205, 114, 0.66);
  transform: rotate(8deg);
}

.plan-hero__copy {
  position: relative;
  z-index: 2;
  display: flex;
  flex: 0 0 55%;
  flex-direction: column;
  align-items: flex-start;
  padding: 48rpx 12rpx 24rpx 28rpx;
}

.plan-hero__kicker {
  margin-bottom: 10rpx;
  font-size: 20rpx;
  font-weight: 800;
  color: var(--tl-primary-deep);
  letter-spacing: 2rpx;
}

.plan-hero__title {
  display: -webkit-box;
  max-width: 326rpx;
  overflow: hidden;
  font-size: 44rpx;
  font-weight: 900;
  line-height: 1.22;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.plan-hero__underline {
  width: 84rpx;
  height: 8rpx;
  margin: 18rpx 0;
  background: var(--tl-primary);
  border-radius: 99rpx;
  transform: rotate(-2deg);
}

.plan-hero__desc {
  display: block;
  max-width: 284rpx;
  margin-bottom: 24rpx;
  font-size: 26rpx;
  line-height: 1.6;
  color: var(--tl-text-secondary);
}

.plan-hero__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
}

.plan-hero__tag {
  display: flex;
  gap: 7rpx;
  align-items: center;
  height: 52rpx;
  padding: 0 12rpx;
  font-size: 20rpx;
  font-weight: 800;
  border: 2rpx solid rgba(151, 109, 59, 0.22);
  border-radius: 18rpx;
}

.plan-hero__tag--orange { color: var(--tl-primary-deep); background: #fff0d2; }
.plan-hero__tag--blue { color: var(--tl-blue-deep); background: var(--tl-blue); }
.plan-hero__tag--green { color: var(--tl-green-deep); background: var(--tl-green); }

.plan-hero__tag-mark {
  position: relative;
  width: 18rpx;
  height: 18rpx;
  opacity: 0.82;
}

.plan-hero__tag-mark::before,
.plan-hero__tag-mark::after {
  position: absolute;
  box-sizing: border-box;
  content: '';
  border-color: currentColor;
}

.plan-hero__tag-mark--age::before,
.plan-hero__tag-mark--time::before {
  inset: 1rpx;
  border: 2rpx solid currentColor;
  border-radius: 50%;
}

.plan-hero__tag-mark--age::after {
  bottom: 0;
  left: 8rpx;
  width: 2rpx;
  height: 9rpx;
  background: currentColor;
}

.plan-hero__tag-mark--time::after {
  top: 4rpx;
  left: 8rpx;
  width: 2rpx;
  height: 7rpx;
  background: currentColor;
  transform-origin: bottom;
  transform: rotate(-35deg);
}

.plan-hero__tag-mark--tasks::before {
  inset: 2rpx;
  border: 2rpx solid currentColor;
  border-radius: 3rpx;
}

.plan-hero__tag-mark--tasks::after {
  top: 8rpx;
  left: 5rpx;
  width: 8rpx;
  height: 4rpx;
  border-bottom: 2rpx solid currentColor;
  border-left: 2rpx solid currentColor;
  transform: rotate(-45deg);
}

.plan-hero__art {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 52%;
  overflow: hidden;
  border-radius: 0 var(--tl-radius-lg) var(--tl-radius-lg) 0;
}

.plan-hero__art::after {
  position: absolute;
  inset: 0;
  content: '';
  background: linear-gradient(90deg, var(--tl-paper) 0, rgba(255, 251, 239, 0) 34%);
  pointer-events: none;
}

.plan-hero__image {
  width: 100%;
  height: 100%;
}

.plan-hero__postmark {
  position: absolute;
  right: 22rpx;
  bottom: 24rpx;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 62rpx;
  height: 62rpx;
  font-size: 19rpx;
  font-weight: 900;
  color: var(--tl-primary-deep);
  background: rgba(255, 248, 224, 0.86);
  border: 3rpx solid var(--tl-primary);
  border-radius: 50%;
  transform: rotate(-12deg);
}

.plan-destination-card {
  display: flex;
  gap: 16rpx;
  align-items: center;
  min-height: 104rpx;
  margin-bottom: 16rpx;
  padding: 18rpx 20rpx;
  background: var(--tl-paper);
  border: 2rpx solid var(--tl-line);
  border-radius: var(--tl-radius-md);
  box-shadow: 0 8rpx 14rpx rgba(92, 60, 29, 0.05);
}

.plan-destination-card__pin {
  position: relative;
  flex: 0 0 auto;
  width: 26rpx;
  height: 32rpx;
  margin-left: 4rpx;
  background: var(--tl-primary);
  border-radius: 50% 50% 50% 0;
  transform: rotate(-45deg);
}

.plan-destination-card__pin::after {
  position: absolute;
  top: 8rpx;
  left: 8rpx;
  width: 10rpx;
  height: 10rpx;
  content: '';
  background: var(--tl-paper);
  border-radius: 50%;
}

.plan-destination-card__copy {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
}

.plan-destination-card__label {
  margin-bottom: 4rpx;
  font-size: 20rpx;
  font-weight: 800;
  color: var(--tl-text-secondary);
}

.plan-destination-card__value {
  overflow: hidden;
  font-size: 30rpx;
  font-weight: 900;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.plan-destination-card__status {
  flex: 0 0 auto;
  padding: 8rpx 12rpx;
  font-size: 20rpx;
  font-weight: 800;
  color: var(--tl-green-deep);
  background: var(--tl-green);
  border-radius: 999rpx;
}

.plan-interest-strip {
  display: flex;
  gap: 12rpx;
  align-items: flex-start;
  margin-bottom: 30rpx;
  padding: 0 4rpx;
}

.plan-interest-strip__label {
  flex: 0 0 auto;
  padding-top: 7rpx;
  font-size: 21rpx;
  font-weight: 800;
  color: var(--tl-text-secondary);
}

.plan-interest-strip__items {
  display: flex;
  flex: 1;
  flex-wrap: wrap;
  gap: 8rpx;
}

.plan-interest-strip__item {
  padding: 7rpx 13rpx;
  font-size: 20rpx;
  font-weight: 800;
  color: var(--tl-blue-deep);
  background: rgba(210, 232, 242, 0.72);
  border-radius: 999rpx;
}

.plan-section-heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 16rpx;
  padding: 0 6rpx;
}

.plan-section-heading__title {
  font-size: 34rpx;
  font-weight: 900;
}

.plan-section-heading__note {
  font-size: 20rpx;
  color: var(--tl-text-secondary);
}

.plan-sections {
  display: flex;
  flex-direction: column;
  gap: 16rpx;
  margin-bottom: 28rpx;
}

.plan-section-card {
  position: relative;
  display: flex;
  align-items: center;
  min-height: 146rpx;
  padding: 18rpx 48rpx 18rpx 18rpx;
  overflow: hidden;
  background: var(--tl-paper);
  border: 2rpx solid var(--tl-line);
  border-radius: var(--tl-radius-md);
  box-shadow: 0 8rpx 14rpx rgba(92, 60, 29, 0.05);
}

.plan-section-card::after {
  position: absolute;
  right: -20rpx;
  bottom: -42rpx;
  width: 110rpx;
  height: 110rpx;
  content: '';
  opacity: 0.34;
  border: 3rpx solid currentColor;
  border-radius: 50%;
}

.plan-section-card__number {
  position: absolute;
  top: 12rpx;
  right: 24rpx;
  font-size: 16rpx;
  font-weight: 900;
  color: var(--tl-text-secondary);
  letter-spacing: 1rpx;
}

.plan-section-card__art {
  position: relative;
  flex: 0 0 98rpx;
  width: 98rpx;
  height: 98rpx;
  margin-right: 18rpx;
}

.plan-section-card__paper {
  position: absolute;
  top: 10rpx;
  right: 0;
  width: 70rpx;
  height: 76rpx;
  background: var(--tl-paper-deep);
  border: 2rpx solid var(--tl-line);
  border-radius: 10rpx;
  transform: rotate(7deg);
}

.plan-section-card__paper::after {
  position: absolute;
  top: 15rpx;
  left: 12rpx;
  width: 44rpx;
  height: 3rpx;
  content: '';
  background: var(--tl-line);
  box-shadow: 0 13rpx 0 var(--tl-line), 0 26rpx 0 var(--tl-line);
}

.plan-section-card__mark {
  position: absolute;
  bottom: 7rpx;
  left: 2rpx;
  width: 58rpx;
  height: 58rpx;
  border: 5rpx solid var(--tl-paper);
  border-radius: 50%;
  box-shadow: 0 5rpx 8rpx rgba(92, 60, 29, 0.08);
}

.plan-section-card--book { color: var(--tl-primary-deep); }
.plan-section-card--book .plan-section-card__mark { background: var(--tl-primary); }
.plan-section-card--bag { color: var(--tl-green-deep); }
.plan-section-card--bag .plan-section-card__mark { background: var(--tl-green-deep); }
.plan-section-card--palace { color: #a06a15; }
.plan-section-card--palace .plan-section-card__mark { background: var(--tl-yellow); }
.plan-section-card--question { color: var(--tl-blue-deep); }
.plan-section-card--question .plan-section-card__mark { background: var(--tl-blue-deep); }

.plan-section-card__content {
  position: relative;
  z-index: 1;
  flex: 1;
  min-width: 0;
}

.plan-section-card__title {
  display: block;
  margin-bottom: 6rpx;
  font-size: 31rpx;
  font-weight: 900;
  color: var(--tl-text-main);
}

.plan-section-card__summary {
  display: block;
  margin-bottom: 8rpx;
  font-size: 24rpx;
  line-height: 1.4;
  color: var(--tl-text-secondary);
}

.plan-section-card__items {
  display: flex;
  overflow: hidden;
  gap: 7rpx;
  max-height: 45rpx;
}

.plan-section-card__item {
  flex: 0 0 auto;
  max-width: 190rpx;
  padding: 5rpx 10rpx;
  overflow: hidden;
  font-size: 17rpx;
  font-weight: 700;
  line-height: 1.3;
  color: var(--tl-text-secondary);
  text-overflow: ellipsis;
  white-space: nowrap;
  background: var(--tl-paper-deep);
  border-radius: 999rpx;
}

.plan-section-card__arrow {
  position: absolute;
  top: 54%;
  right: 18rpx;
  z-index: 2;
  font-size: 48rpx;
  font-weight: 300;
  line-height: 1;
  color: currentColor;
  transform: translateY(-50%);
}

.plan-start {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 100rpx;
  padding: 0 28rpx;
  font-size: 32rpx;
  font-weight: 900;
  color: var(--tl-paper);
  letter-spacing: 1rpx;
  background: var(--tl-primary);
  border: 3rpx solid var(--tl-primary-deep);
  border-radius: var(--tl-radius-md);
  box-shadow: 0 12rpx 0 var(--tl-primary-deep), 0 18rpx 24rpx rgba(194, 91, 28, 0.22);
}

.plan-start[disabled] {
  opacity: 0.7;
}

.plan-start__dot {
  width: 13rpx;
  height: 13rpx;
  margin-right: 14rpx;
  background: var(--tl-yellow);
  border-radius: 50%;
}

.plan-start__star {
  position: relative;
  width: 18rpx;
  height: 18rpx;
  margin-left: 14rpx;
  color: currentColor;
  transform: rotate(45deg);
}

.plan-start__star::after {
  position: absolute;
  inset: 0;
  content: '';
  background: currentColor;
  border-radius: 5rpx;
}

@media (max-width: 360px) {
  .plan-page__paper {
    padding-right: 24rpx;
    padding-left: 24rpx;
  }

  .plan-hero {
    min-height: 378rpx;
  }

  .plan-hero__copy {
    flex-basis: 60%;
    padding-left: 22rpx;
  }

  .plan-hero__title {
    font-size: 40rpx;
  }

  .plan-hero__art {
    width: 54%;
  }

  .plan-hero__tag {
    padding: 0 9rpx;
    font-size: 18rpx;
  }

  .plan-interest-strip {
    display: block;
  }

  .plan-interest-strip__label {
    display: block;
    margin-bottom: 8rpx;
  }
}

@media (min-width: 431px) {
  .plan-page__paper {
    padding: calc(18px + var(--tl-safe-top)) 18px calc(var(--tl-tabbar-height) + var(--tl-safe-bottom) + 34px);
  }

  .plan-header {
    min-height: 44px;
    margin-bottom: 16px;
  }

  .plan-header__back,
  .plan-header__spacer {
    flex-basis: 32px;
    width: 32px;
    height: 32px;
  }

  .plan-header__back {
    font-size: 32px;
  }

  .plan-header__eyebrow {
    margin-bottom: 3px;
    font-size: 10px;
  }

  .plan-header__title {
    font-size: 28px;
  }

  .plan-hero {
    min-height: 224px;
    border-width: 2px;
  }

  .plan-hero__copy {
    padding: 28px 8px 15px 15px;
  }

  .plan-hero__kicker { font-size: 12px; }
  .plan-hero__title { max-width: 170px; font-size: 27px; }
  .plan-hero__desc { max-width: 158px; font-size: 14px; }
  .plan-hero__tag { height: 28px; font-size: 11px; }
  .plan-hero__postmark { width: 36px; height: 36px; font-size: 11px; }
  .plan-destination-card { min-height: 58px; padding: 10px 12px; }
  .plan-destination-card__value { font-size: 18px; }
  .plan-section-card { min-height: 84px; padding: 10px 32px 10px 10px; }
  .plan-section-card__art { flex-basis: 54px; width: 54px; height: 54px; margin-right: 12px; }
  .plan-section-card__paper { width: 40px; height: 42px; }
  .plan-section-card__mark { width: 33px; height: 33px; }
  .plan-section-card__title { font-size: 19px; }
  .plan-section-card__summary { font-size: 14px; }
  .plan-section-card__item { font-size: 10px; }
  .plan-start { min-height: 52px; font-size: 19px; }
}
</style>
