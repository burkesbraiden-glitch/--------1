<template>
  <view class="plan-page">
    <view class="plan-page__paper">
      <view class="plan-header">
        <button class="plan-header__back" @click="goHome">‹</button>
        <view class="plan-header__title-wrap">
          <text class="plan-header__spark">小旅</text>
          <text class="plan-header__title">探索计划</text>
        </view>
        <button class="plan-header__notice" @click="openPetChat">
          <text>铃</text>
          <view class="plan-header__dot"></view>
        </button>
      </view>

      <view v-if="isPageLoading" class="plan-basic">
        <text class="plan-basic__value">正在加载探索计划...</text>
      </view>

      <view v-else-if="planStore.error" class="plan-basic">
        <text class="plan-basic__value">计划加载失败</text>
        <text class="plan-basic__status" @click="loadPlans(true)">重试</text>
      </view>

      <view v-else-if="!displayPlan" class="plan-basic">
        <text class="plan-basic__value">还没有探索计划</text>
        <text class="plan-basic__status" @click="goHome">先去首页创建一次亲子探索吧</text>
      </view>

      <template v-else>
      <view class="plan-hero">
        <view class="plan-hero__copy">
          <text class="plan-hero__title">{{ displayPlan.title }}</text>
          <view class="plan-hero__underline"></view>
          <text class="plan-hero__desc">和孩子一起先做好这次旅行的小计划</text>

          <view class="plan-hero__tags">
            <view class="plan-hero__tag plan-hero__tag--orange">
              <text class="plan-hero__tag-mark">童</text>
              <text>{{ formattedAgeGroup }}</text>
            </view>
            <view class="plan-hero__tag plan-hero__tag--blue">
              <text class="plan-hero__tag-mark">时</text>
              <text>{{ formattedDuration }}</text>
            </view>
            <view class="plan-hero__tag plan-hero__tag--green">
              <text class="plan-hero__tag-mark">任</text>
              <text>{{ realTaskCount }}个任务</text>
            </view>
          </view>
        </view>

        <view class="plan-hero__scene">
          <view class="plan-scene">
            <view class="plan-scene__sky"></view>
            <view class="plan-scene__cloud plan-scene__cloud--one"></view>
            <view class="plan-scene__cloud plan-scene__cloud--two"></view>
            <view class="plan-scene__palace">
              <view class="plan-scene__roof"></view>
              <view class="plan-scene__hall"></view>
              <view class="plan-scene__stairs"></view>
            </view>
            <view class="plan-scene__leaf plan-scene__leaf--one"></view>
            <view class="plan-scene__leaf plan-scene__leaf--two"></view>
          </view>
        </view>
      </view>

      <view class="plan-basic">
        <text class="plan-basic__label">今天要去</text>
        <text class="plan-basic__value">{{ displayPlan.destination }}</text>
        <text class="plan-basic__status">状态：{{ statusText }}</text>
      </view>

      <view class="plan-sections">
        <view
          v-for="section in sections"
          :key="section.title"
          class="plan-section-card"
          :class="`plan-section-card--${section.theme}`"
        >
          <view class="plan-section-card__art">
            <view class="plan-section-card__paper"></view>
            <view class="plan-section-card__mark"></view>
          </view>
          <view class="plan-section-card__content">
            <text class="plan-section-card__title">{{ section.title }}</text>
            <text class="plan-section-card__summary">{{ section.summary }}</text>
            <view class="plan-section-card__items">
              <text v-for="item in section.items" :key="item" class="plan-section-card__item">{{ item }}</text>
            </view>
          </view>
          <text class="plan-section-card__arrow">›</text>
        </view>
      </view>

      <button class="plan-ai" @click="openPetChat">
        <view class="plan-ai__badge">AI建议</view>
        <text class="plan-ai__text">先让孩子猜一猜，再一起寻找答案</text>
        <text class="plan-ai__arrow">›</text>
      </button>

      <button class="plan-start" :disabled="isStarting" @click="startExploration">
        <text>{{ isStarting ? '启动中' : '开始今天的探索' }}</text>
        <text class="plan-start__star">星</text>
      </button>
      </template>
    </view>

    <AiPet />
    <AppTabbar active="plan" />
  </view>
</template>

<script>
import AiPet from '../../components/AiPet.vue'
import AppTabbar from '../../components/AppTabbar.vue'
import { usePetStore } from '../../stores/pet'
import { usePlanStore } from '../../stores/plan'
import { useTaskStore } from '../../stores/task'
import { useUserStore } from '../../stores/user'
import { ensureCurrentPlanReady } from '../../utils/planRecovery'
import { endUserSession } from '../../utils/sessionBoundary'

export default {
  components: {
    AiPet,
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
    usePetStore().setPageContext('plan', this.displayPlan?.id)
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
    openPetChat() {
      const petStore = usePetStore()
      petStore.setPageContext('plan', this.displayPlan?.id)
      petStore.openChat()
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
  color: #4a2f1b;
  background:
    radial-gradient(circle at 12% 8%, rgba(255, 238, 181, 0.55) 0, rgba(255, 238, 181, 0) 110rpx),
    linear-gradient(135deg, rgba(148, 104, 48, 0.05) 0 1rpx, transparent 1rpx 22rpx),
    #f8efd9;
}

.plan-page__paper {
  width: 100%;
  max-width: 430px;
  min-height: 100vh;
  margin: 0 auto;
  padding: calc(28rpx + env(safe-area-inset-top)) 34rpx calc(210rpx + env(safe-area-inset-bottom));
}

.plan-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 30rpx;
}

.plan-header__back,
.plan-header__notice {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 64rpx;
  height: 64rpx;
  font-weight: 900;
  color: #4a2f1b;
}

.plan-header__back {
  font-size: 56rpx;
}

.plan-header__notice {
  position: relative;
  font-size: 24rpx;
  border: 3rpx solid #4a2f1b;
  border-radius: 30rpx 30rpx 24rpx 24rpx;
}

.plan-header__dot {
  position: absolute;
  top: -6rpx;
  right: -2rpx;
  width: 16rpx;
  height: 16rpx;
  background: #f26a21;
  border-radius: 50%;
}

.plan-header__title-wrap {
  position: relative;
  flex: 1;
  text-align: center;
}

.plan-header__spark {
  position: absolute;
  top: -18rpx;
  left: 72rpx;
  font-size: 20rpx;
  font-weight: 900;
  color: #f4aa23;
  transform: rotate(-22deg);
}

.plan-header__title {
  font-size: 48rpx;
  font-weight: 900;
  line-height: 1;
  color: #4a2f1b;
}

.plan-hero {
  position: relative;
  display: flex;
  min-height: 382rpx;
  margin-bottom: 22rpx;
  overflow: hidden;
  background: rgba(255, 247, 232, 0.92);
  border: 4rpx solid rgba(190, 142, 78, 0.46);
  border-radius: 36rpx;
  box-shadow: 0 18rpx 30rpx rgba(97, 63, 28, 0.13);
}

.plan-hero__copy {
  position: relative;
  z-index: 2;
  width: 56%;
  padding: 56rpx 18rpx 30rpx 28rpx;
}

.plan-hero__title {
  display: block;
  max-width: 300rpx;
  font-size: 44rpx;
  font-weight: 900;
  line-height: 1.14;
}

.plan-hero__underline {
  width: 96rpx;
  height: 8rpx;
  margin: 18rpx 0 20rpx;
  background: #f26a21;
  border-radius: 999rpx;
}

.plan-hero__desc {
  display: block;
  margin-bottom: 28rpx;
  font-size: 28rpx;
  line-height: 1.6;
  color: #5e3c22;
}

.plan-hero__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 14rpx;
}

.plan-hero__tag {
  display: flex;
  gap: 8rpx;
  align-items: center;
  justify-content: center;
  min-width: 132rpx;
  height: 58rpx;
  padding: 0 16rpx;
  font-size: 25rpx;
  font-weight: 800;
  border: 2rpx solid rgba(190, 142, 78, 0.28);
  border-radius: 22rpx;
}

.plan-hero__tag--orange {
  color: #d94b12;
  background: #fff1d8;
}

.plan-hero__tag--blue {
  color: #235b83;
  background: #dfeff8;
}

.plan-hero__tag--green {
  color: #55753c;
  background: #eef6dc;
}

.plan-hero__tag-mark {
  font-size: 20rpx;
}

.plan-hero__scene {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 54%;
}

.plan-scene {
  position: relative;
  height: 100%;
  overflow: hidden;
  background: #cfe7f5;
}

.plan-scene__sky {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 30% 20%, rgba(255, 255, 255, 0.88) 0 44rpx, transparent 46rpx),
    radial-gradient(circle at 50% 18%, rgba(255, 255, 255, 0.7) 0 28rpx, transparent 30rpx),
    #bfe1f5;
}

.plan-scene__cloud {
  position: absolute;
  height: 24rpx;
  background: rgba(255, 250, 240, 0.8);
  border-radius: 999rpx;
}

.plan-scene__cloud--one {
  top: 92rpx;
  left: 44rpx;
  width: 120rpx;
}

.plan-scene__cloud--two {
  top: 128rpx;
  right: 28rpx;
  width: 86rpx;
}

.plan-scene__palace {
  position: absolute;
  right: 18rpx;
  bottom: 74rpx;
  left: 26rpx;
}

.plan-scene__roof {
  height: 66rpx;
  background: #ee9d1f;
  border: 4rpx solid rgba(126, 82, 35, 0.24);
  border-radius: 68rpx 68rpx 18rpx 18rpx;
  transform: skewX(-8deg);
}

.plan-scene__hall {
  height: 100rpx;
  margin: -4rpx 18rpx 0;
  background:
    repeating-linear-gradient(90deg, rgba(90, 51, 26, 0.26) 0 8rpx, transparent 8rpx 34rpx),
    #d45528;
  border: 4rpx solid rgba(126, 82, 35, 0.2);
  border-radius: 8rpx;
}

.plan-scene__stairs {
  width: 180rpx;
  height: 38rpx;
  margin: 10rpx auto 0;
  background: rgba(255, 250, 240, 0.86);
  border-radius: 12rpx;
}

.plan-scene__leaf {
  position: absolute;
  width: 48rpx;
  height: 18rpx;
  background: #88a85f;
  border-radius: 100% 0 100% 0;
}

.plan-scene__leaf--one {
  top: 36rpx;
  right: 24rpx;
  transform: rotate(-20deg);
}

.plan-scene__leaf--two {
  top: 72rpx;
  right: 68rpx;
  transform: rotate(24deg);
}

.plan-basic {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx 18rpx;
  align-items: center;
  margin-bottom: 20rpx;
  padding: 18rpx 22rpx;
  background: rgba(255, 250, 240, 0.82);
  border: 2rpx dashed rgba(190, 142, 78, 0.5);
  border-radius: 24rpx;
}

.plan-basic__label,
.plan-basic__status {
  font-size: 24rpx;
  font-weight: 800;
  color: #8a6d54;
}

.plan-basic__value {
  font-size: 30rpx;
  font-weight: 900;
  color: #4a2f1b;
}

.plan-sections {
  display: flex;
  flex-direction: column;
  gap: 18rpx;
  margin-bottom: 22rpx;
}

.plan-section-card {
  position: relative;
  display: flex;
  align-items: center;
  min-height: 140rpx;
  padding: 20rpx 58rpx 20rpx 20rpx;
  overflow: hidden;
  background: rgba(255, 247, 232, 0.92);
  border: 3rpx solid rgba(190, 142, 78, 0.34);
  border-radius: 28rpx;
  box-shadow: 0 10rpx 18rpx rgba(97, 63, 28, 0.08);
}

.plan-section-card__art {
  position: relative;
  flex-shrink: 0;
  width: 156rpx;
  height: 96rpx;
  margin-right: 20rpx;
}

.plan-section-card__paper {
  position: absolute;
  right: 18rpx;
  bottom: 6rpx;
  width: 104rpx;
  height: 76rpx;
  background: #fffaf0;
  border: 2rpx solid rgba(126, 82, 35, 0.2);
  border-radius: 16rpx;
  transform: rotate(-5deg);
}

.plan-section-card__mark {
  position: absolute;
  left: 12rpx;
  bottom: 16rpx;
  width: 58rpx;
  height: 58rpx;
  border: 6rpx solid rgba(255, 250, 240, 0.78);
  border-radius: 50%;
}

.plan-section-card--book .plan-section-card__mark {
  background: #f26a21;
}

.plan-section-card--bag .plan-section-card__mark {
  background: #7b9a50;
}

.plan-section-card--palace .plan-section-card__mark {
  background: #ee9d1f;
}

.plan-section-card--question .plan-section-card__mark {
  background: #7bb8d6;
}

.plan-section-card__content {
  flex: 1;
  min-width: 0;
}

.plan-section-card__title {
  display: block;
  margin-bottom: 8rpx;
  font-size: 34rpx;
  font-weight: 900;
}

.plan-section-card__summary {
  display: block;
  margin-bottom: 8rpx;
  font-size: 27rpx;
  line-height: 1.35;
  color: #5e3c22;
}

.plan-section-card__items {
  display: flex;
  flex-wrap: wrap;
  gap: 8rpx;
}

.plan-section-card__item {
  padding: 7rpx 12rpx;
  font-size: 21rpx;
  line-height: 1.2;
  color: #6b482d;
  background: rgba(255, 240, 189, 0.62);
  border-radius: 999rpx;
}

.plan-section-card__arrow {
  position: absolute;
  top: 50%;
  right: 24rpx;
  font-size: 58rpx;
  color: #6b482d;
  transform: translateY(-50%);
}

.plan-ai {
  display: flex;
  align-items: center;
  width: calc(100% - 92rpx);
  min-height: 76rpx;
  margin-bottom: 20rpx;
  padding: 12rpx 18rpx;
  text-align: left;
  background: #dfeff8;
  border: 3rpx solid rgba(47, 111, 148, 0.22);
  border-radius: 24rpx;
}

.plan-ai__badge {
  flex-shrink: 0;
  padding: 8rpx 16rpx;
  margin-right: 14rpx;
  font-size: 24rpx;
  font-weight: 900;
  color: #fff;
  background: #669bc2;
  border-radius: 16rpx;
}

.plan-ai__text {
  flex: 1;
  min-width: 0;
  font-size: 26rpx;
  line-height: 1.35;
  color: #235b83;
}

.plan-ai__arrow {
  flex-shrink: 0;
  margin-left: 12rpx;
  font-size: 42rpx;
  color: #235b83;
}

.plan-start {
  display: flex;
  align-items: center;
  justify-content: center;
  width: calc(100% - 96rpx);
  height: 96rpx;
  font-size: 34rpx;
  font-weight: 900;
  color: #fff;
  background: #f26a21;
  border-radius: 32rpx;
  box-shadow: 0 16rpx 22rpx rgba(217, 75, 18, 0.22);
}

.plan-start__star {
  margin-left: 14rpx;
  font-size: 22rpx;
  transform: rotate(18deg);
}

@media (min-width: 431px) {
  .plan-page__paper {
    padding: calc(18px + env(safe-area-inset-top)) 18px calc(120px + env(safe-area-inset-bottom));
  }

  .plan-header {
    margin-bottom: 16px;
  }

  .plan-header__title {
    font-size: 28px;
  }

  .plan-hero {
    min-height: 220px;
    border-width: 2px;
    border-radius: 20px;
  }

  .plan-hero__copy {
    padding: 32px 12px 18px 16px;
  }

  .plan-hero__title {
    font-size: 28px;
  }

  .plan-hero__desc {
    font-size: 16px;
  }

  .plan-section-card {
    min-height: 82px;
    padding: 12px 34px 12px 12px;
    border-width: 2px;
    border-radius: 16px;
  }

  .plan-section-card__title {
    font-size: 20px;
  }

  .plan-section-card__summary {
    font-size: 15px;
  }

  .plan-section-card__item {
    font-size: 12px;
  }
}
</style>
