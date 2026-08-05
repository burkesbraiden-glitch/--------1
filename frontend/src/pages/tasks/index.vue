<template>
  <view class="tasks-page">
    <view class="tasks-page__paper">
      <view class="tasks-header">
        <view class="tasks-header__back" @click="goPlan">‹</view>
        <view class="tasks-header__title-wrap">
          <view class="tasks-header__spark"></view>
          <text class="tasks-header__title">观察任务</text>
        </view>
        <view class="tasks-header__notice" @click="openPetChat">
          <text>铃</text>
          <view class="tasks-header__dot"></view>
        </view>
      </view>

      <view class="tasks-hero">
        <view class="tasks-hero__copy">
          <text class="tasks-hero__title">{{ heroTitle }}</text>
          <text class="tasks-hero__desc">边走边看，发现细节</text>
          <view class="tasks-hero__tags">
            <view class="tasks-hero__tag tasks-hero__tag--orange">
              <text class="tasks-hero__tag-icon">包</text>
              <text>{{ displayPlan.ageGroup }}岁</text>
            </view>
            <view class="tasks-hero__tag tasks-hero__tag--blue">
              <text class="tasks-hero__tag-icon">时</text>
              <text>约30分钟</text>
            </view>
          </view>
        </view>
        <view class="tasks-hero__art">
          <view class="tasks-hero__cloud tasks-hero__cloud--one"></view>
          <view class="tasks-hero__cloud tasks-hero__cloud--two"></view>
          <view class="tasks-hero__branch"></view>
          <view class="tasks-palace">
            <view class="tasks-palace__roof"></view>
            <view class="tasks-palace__body"></view>
            <view class="tasks-palace__stairs"></view>
          </view>
        </view>
      </view>

      <view class="tasks-progress">
        <view class="tasks-progress__icon">
          <view class="tasks-progress__clip"></view>
          <view class="tasks-progress__line"></view>
          <view class="tasks-progress__line tasks-progress__line--short"></view>
        </view>
        <view class="tasks-progress__content">
          <text class="tasks-progress__text">今天完成 <text class="tasks-progress__count">{{ task.completedCount }}</text>/{{ totalTasks }}</text>
          <view class="tasks-progress__bar">
            <view class="tasks-progress__fill" :style="{ width: task.progress + '%' }"></view>
          </view>
        </view>
        <view class="tasks-progress__sprout">
          <view class="tasks-progress__leaf tasks-progress__leaf--left"></view>
          <view class="tasks-progress__leaf tasks-progress__leaf--right"></view>
        </view>
      </view>

      <view v-if="isPlanReady && task.currentPlanTasks.length" class="tasks-ready">
        <view class="tasks-ready__copy">
          <text class="tasks-ready__title">开始探索后即可记录任务</text>
          <text class="tasks-ready__desc">任务内容已经准备好，和孩子一起出发吧</text>
        </view>
        <button class="tasks-ready__button" :disabled="isStartingExploration" @click="startExploration">
          {{ isStartingExploration ? '启动中…' : '开始探索' }}
        </button>
      </view>

      <view v-if="taskStateMessage" class="tasks-state">
        <text class="tasks-state__text">{{ taskStateMessage }}</text>
        <button v-if="task.error" class="tasks-state__retry" @click="restorePlanAndTasks(true)">重试</button>
      </view>

      <view v-else class="tasks-page__list">
        <TaskCard v-for="item in task.currentPlanTasks" :key="item.id" :task="item" @select="goDetail" />
      </view>

      <view class="tasks-reward">
        <view class="tasks-reward__medal">
          <view class="tasks-reward__star"></view>
        </view>
        <view class="tasks-reward__copy">
          <text class="tasks-reward__title">奖励：小小观察家</text>
          <text class="tasks-reward__desc">完成全部任务可获得</text>
        </view>
        <view class="tasks-reward__gift">
          <view class="tasks-reward__ribbon"></view>
        </view>
      </view>
    </view>

    <AiPet />
    <AppTabbar active="tasks" />
  </view>
</template>

<script>
import AiPet from '../../components/AiPet.vue'
import AppTabbar from '../../components/AppTabbar.vue'
import TaskCard from '../../components/TaskCard.vue'
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
    TaskCard,
  },
  data() {
    return {
      isStartingExploration: false,
    }
  },
  computed: {
    planStore() {
      return usePlanStore()
    },
    task() {
      return useTaskStore()
    },
    userStore() {
      return useUserStore()
    },
    displayPlan() {
      return this.planStore.currentPlan || {}
    },
    heroTitle() {
      const destination = this.displayPlan.destination || '故宫'
      return destination.includes('故宫') ? '故宫观察任务' : `${destination}观察任务`
    },
    totalTasks() {
      return this.task.currentPlanTasks.length
    },
    isPlanReady() {
      return this.displayPlan.status === 'ready'
    },
    taskStateMessage() {
      if (this.task.isGenerating) {
        return '正在准备这次探索任务……'
      }
      if (this.task.isLoading && !this.task.currentPlanTasks.length) {
        return '正在加载观察任务……'
      }
      if (this.task.error?.code === 'TASK_SET_INCOMPLETE') {
        return '任务准备异常，请稍后重试'
      }
      if (this.task.error) {
        return '任务加载失败，请重试'
      }
      if (!this.task.currentPlanTasks.length) {
        return '还没有可用的观察任务'
      }
      return ''
    },
  },
  async onShow() {
    await this.restorePlanAndTasks()
    usePetStore().setPageContext('task-list', this.displayPlan?.id)
  },
  methods: {
    showToast(title) {
      uni.showToast({
        title,
        icon: 'none',
      })
    },
    taskErrorText(error, fallback = '操作失败，请稍后重试') {
      const messages = {
        PLAN_NOT_FOUND: '没有找到这次探索计划',
        PLAN_NOT_READY: '这次探索暂时不能开始',
        PLAN_NOT_STARTED: '请先开始探索再记录任务',
        PLAN_ALREADY_COMPLETED: '这次探索已经结束了',
        TASK_NOT_FOUND: '没有找到这个任务，请返回列表重试',
        TASK_ALREADY_COMPLETED: '这个任务已经完成了',
        VALIDATION_ERROR: '填写内容不符合要求，请检查后重试',
        UNAUTHORIZED: '登录状态已失效，请重新登录',
        TOKEN_EXPIRED: '登录状态已失效，请重新登录',
        INVALID_TOKEN: '登录状态已失效，请重新登录',
        NETWORK_ERROR: '网络连接失败，请稍后重试',
      }
      return messages[error?.code] || fallback
    },
    async restorePlanAndTasks(force = false) {
      try {
        await ensureCurrentPlanReady({ withTasks: false, force })
        if (this.planStore.currentPlan) {
          await this.task.ensureTasks(this.planStore.currentPlan.id, this.planStore.currentPlan.status)
        }
      } catch (error) {
        if (['UNAUTHORIZED', 'TOKEN_EXPIRED', 'INVALID_TOKEN'].includes(error?.code) || error?.statusCode === 401) {
          await endUserSession()
        }
      }
    },
    async startExploration() {
      if (this.isStartingExploration || !this.planStore.currentPlan) {
        return
      }

      this.isStartingExploration = true
      try {
        const startedPlan = await this.planStore.startExploration(
          this.planStore.currentPlan.id,
          this.userStore.userInfo?.id,
        )
        await this.task.ensureTasks(startedPlan.id, startedPlan.status)
        this.showToast('探索已开始，可以记录任务了')
      } catch (error) {
        if (['UNAUTHORIZED', 'TOKEN_EXPIRED', 'INVALID_TOKEN'].includes(error?.code) || error?.statusCode === 401) {
          await endUserSession()
          return
        }
        this.showToast(this.taskErrorText(error, '无法开始探索，请稍后重试'))
      } finally {
        this.isStartingExploration = false
      }
    },
    goPlan() {
      uni.reLaunch({
        url: '/pages/plan/index',
      })
    },
    openPetChat() {
      const petStore = usePetStore()
      petStore.setPageContext('task-list', this.displayPlan?.id)
      petStore.openChat()
    },
    goDetail(item) {
      this.task.setCurrentTask(item.id)
      uni.navigateTo({
        url: `/pages/task-detail/index?id=${item.id}`,
      })
    },
  },
}
</script>

<style>
.tasks-page {
  min-height: 100vh;
  overflow-x: hidden;
  color: #4a2f1b;
  background:
    radial-gradient(circle at 14% 10%, rgba(255, 240, 189, 0.48) 0, rgba(255, 240, 189, 0) 112rpx),
    linear-gradient(135deg, rgba(148, 104, 48, 0.05) 0 1rpx, transparent 1rpx 22rpx),
    #f8efd9;
}

.tasks-page__paper {
  width: 100%;
  max-width: 430px;
  min-height: 100vh;
  margin: 0 auto;
  padding: calc(28rpx + env(safe-area-inset-top)) 34rpx calc(190rpx + env(safe-area-inset-bottom));
}

.tasks-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 30rpx;
}

.tasks-header__back,
.tasks-header__notice {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 64rpx;
  height: 64rpx;
  font-weight: 900;
  color: #4a2f1b;
}

.tasks-header__back {
  font-size: 64rpx;
}

.tasks-header__notice {
  position: relative;
  font-size: 24rpx;
  border: 3rpx solid #4a2f1b;
  border-radius: 30rpx 30rpx 24rpx 24rpx;
}

.tasks-header__dot {
  position: absolute;
  top: -6rpx;
  right: -2rpx;
  width: 16rpx;
  height: 16rpx;
  background: #f26a21;
  border-radius: 50%;
}

.tasks-header__title-wrap {
  position: relative;
  flex: 1;
  text-align: center;
}

.tasks-header__spark {
  position: absolute;
  top: -22rpx;
  left: 78rpx;
  font-size: 20rpx;
  font-weight: 900;
  color: #f4aa23;
  transform: rotate(-20deg);
}

.tasks-header__title {
  font-size: 48rpx;
  font-weight: 900;
  line-height: 1;
}

.tasks-hero {
  position: relative;
  display: flex;
  min-height: 292rpx;
  margin-bottom: 22rpx;
  overflow: hidden;
  background: rgba(255, 247, 232, 0.92);
  border: 4rpx solid rgba(223, 189, 131, 0.62);
  border-radius: 34rpx;
  box-shadow: 0 16rpx 28rpx rgba(97, 63, 28, 0.1);
}

.tasks-hero__copy {
  position: relative;
  z-index: 2;
  width: 50%;
  padding: 62rpx 10rpx 26rpx 28rpx;
}

.tasks-hero__title {
  display: block;
  margin-bottom: 16rpx;
  font-size: 44rpx;
  font-weight: 900;
  line-height: 1.14;
}

.tasks-hero__desc {
  display: block;
  margin-bottom: 42rpx;
  font-size: 30rpx;
  color: #5e3c22;
}

.tasks-hero__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 14rpx;
}

.tasks-hero__tag {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 58rpx;
  padding: 0 18rpx;
  font-size: 25rpx;
  font-weight: 800;
  border: 2rpx solid rgba(190, 142, 78, 0.28);
  border-radius: 22rpx;
}

.tasks-hero__tag-icon {
  margin-right: 8rpx;
  font-size: 20rpx;
}

.tasks-hero__tag--orange {
  color: #d94b12;
  background: #fff1d8;
}

.tasks-hero__tag--blue {
  color: #235b83;
  background: #dfeff8;
}

.tasks-hero__art {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 58%;
  background: #bfe1f5;
}

.tasks-hero__cloud {
  position: absolute;
  height: 28rpx;
  background: rgba(255, 250, 240, 0.86);
  border-radius: 999rpx;
}

.tasks-hero__cloud--one {
  top: 54rpx;
  left: 26rpx;
  width: 146rpx;
}

.tasks-hero__cloud--two {
  top: 96rpx;
  right: 42rpx;
  width: 92rpx;
}

.tasks-hero__branch {
  position: absolute;
  top: 26rpx;
  right: -12rpx;
  width: 170rpx;
  height: 46rpx;
  border-top: 7rpx solid #8a6d54;
  border-radius: 50%;
  transform: rotate(12deg);
}

.tasks-palace {
  position: absolute;
  right: 24rpx;
  bottom: 32rpx;
  width: 310rpx;
}

.tasks-palace__roof {
  height: 74rpx;
  background: #ee9d1f;
  border: 4rpx solid rgba(126, 82, 35, 0.24);
  border-radius: 70rpx 70rpx 16rpx 16rpx;
}

.tasks-palace__body {
  height: 96rpx;
  margin: -4rpx 24rpx 0;
  background:
    repeating-linear-gradient(90deg, rgba(90, 51, 26, 0.24) 0 8rpx, transparent 8rpx 32rpx),
    #d45528;
  border-radius: 8rpx;
}

.tasks-palace__stairs {
  width: 210rpx;
  height: 38rpx;
  margin: 10rpx auto 0;
  background: rgba(255, 250, 240, 0.86);
  border-radius: 12rpx;
}

.tasks-progress {
  display: flex;
  align-items: center;
  min-height: 112rpx;
  margin-bottom: 20rpx;
  padding: 18rpx 24rpx;
  background: rgba(255, 250, 240, 0.82);
  border: 3rpx solid rgba(223, 189, 131, 0.54);
  border-radius: 28rpx;
}

.tasks-progress__icon {
  position: relative;
  flex-shrink: 0;
  width: 70rpx;
  height: 78rpx;
  margin-right: 22rpx;
  background: #fff7e8;
  border: 5rpx solid #df8b22;
  border-radius: 16rpx;
}

.tasks-progress__clip {
  position: absolute;
  top: -16rpx;
  left: 20rpx;
  width: 30rpx;
  height: 24rpx;
  border: 5rpx solid #df8b22;
  border-bottom: 0;
  border-radius: 12rpx 12rpx 0 0;
}

.tasks-progress__line {
  width: 34rpx;
  height: 5rpx;
  margin: 22rpx auto 0;
  background: #df8b22;
  border-radius: 999rpx;
}

.tasks-progress__line--short {
  width: 24rpx;
  margin-top: 12rpx;
}

.tasks-progress__content {
  flex: 1;
  min-width: 0;
}

.tasks-progress__text {
  display: block;
  margin-bottom: 14rpx;
  font-size: 34rpx;
  font-weight: 800;
}

.tasks-progress__count {
  color: #d94b12;
}

.tasks-progress__bar {
  height: 22rpx;
  overflow: hidden;
  background: #f8e8c5;
  border: 2rpx solid rgba(223, 189, 131, 0.42);
  border-radius: 999rpx;
}

.tasks-progress__fill {
  height: 100%;
  background: linear-gradient(90deg, #ff8a1c, #f26a21);
  border-radius: 999rpx;
  transition: width 0.2s ease;
}

.tasks-progress__sprout {
  position: relative;
  flex-shrink: 0;
  width: 74rpx;
  height: 66rpx;
  margin-left: 18rpx;
  border-bottom: 4rpx solid rgba(139, 95, 45, 0.38);
}

.tasks-progress__leaf {
  position: absolute;
  bottom: 18rpx;
  width: 34rpx;
  height: 18rpx;
  background: #88a85f;
  border-radius: 100% 0 100% 0;
}

.tasks-progress__leaf--left {
  left: 8rpx;
  transform: rotate(-28deg);
}

.tasks-progress__leaf--right {
  right: 8rpx;
  transform: rotate(22deg) scaleX(-1);
}

.tasks-page__list {
  display: flex;
  flex-direction: column;
  gap: 18rpx;
  margin-bottom: 24rpx;
}

.tasks-ready {
  display: flex;
  gap: 16rpx;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 22rpx;
  padding: 18rpx 20rpx;
  background: #eef6dc;
  border: 3rpx dashed rgba(123, 154, 80, 0.52);
  border-radius: 24rpx;
}

.tasks-ready__copy {
  flex: 1;
  min-width: 0;
}

.tasks-ready__title,
.tasks-ready__desc {
  display: block;
}

.tasks-ready__title {
  margin-bottom: 6rpx;
  font-size: 27rpx;
  font-weight: 900;
  color: #55753c;
}

.tasks-ready__desc {
  font-size: 22rpx;
  color: #6b7d51;
}

.tasks-ready__button {
  flex-shrink: 0;
  height: 62rpx;
  padding: 0 22rpx;
  font-size: 25rpx;
  font-weight: 900;
  line-height: 62rpx;
  color: #fff;
  background: #7b9a50;
  border-radius: 20rpx;
}

.tasks-reward {
  position: relative;
  display: flex;
  align-items: center;
  min-height: 132rpx;
  padding: 18rpx 26rpx;
  margin-right: 88rpx;
  overflow: hidden;
  background: rgba(255, 240, 189, 0.56);
  border: 3rpx solid rgba(223, 189, 131, 0.58);
  border-radius: 28rpx;
}

.tasks-reward__medal {
  position: relative;
  flex-shrink: 0;
  width: 82rpx;
  height: 82rpx;
  margin-right: 24rpx;
  background: #f4aa23;
  border: 6rpx solid #f7cf75;
  border-radius: 50%;
}

.tasks-reward__star {
  position: absolute;
  top: 25rpx;
  left: 22rpx;
  width: 32rpx;
  height: 32rpx;
  background: #fff0bd;
  border-radius: 50%;
}

.tasks-reward__copy {
  flex: 1;
  min-width: 0;
}

.tasks-reward__title {
  display: block;
  margin-bottom: 10rpx;
  font-size: 34rpx;
  font-weight: 900;
}

.tasks-reward__desc {
  display: block;
  font-size: 26rpx;
  color: #5e3c22;
}

.tasks-reward__gift {
  position: relative;
  flex-shrink: 0;
  width: 90rpx;
  height: 74rpx;
  background: #e6863b;
  border: 4rpx solid #f7c379;
  border-radius: 14rpx;
  transform: rotate(-8deg);
}

.tasks-reward__ribbon {
  position: absolute;
  top: 0;
  left: 36rpx;
  width: 16rpx;
  height: 100%;
  background: #fff0bd;
}

@media (min-width: 431px) {
  .tasks-page__paper {
    padding: calc(18px + env(safe-area-inset-top)) 18px calc(116px + env(safe-area-inset-bottom));
  }

  .tasks-header {
    margin-bottom: 16px;
  }

  .tasks-header__title {
    font-size: 28px;
  }

  .tasks-hero {
    min-height: 168px;
    border-width: 2px;
    border-radius: 20px;
  }

  .tasks-hero__title {
    font-size: 25px;
  }

  .tasks-hero__desc,
  .tasks-progress__text,
  .tasks-reward__title {
    font-size: 18px;
  }
}

.tasks-state {
  display: flex;
  flex-direction: column;
  gap: 18rpx;
  align-items: center;
  justify-content: center;
  min-height: 180rpx;
  margin-bottom: 24rpx;
  padding: 28rpx;
  background: rgba(255, 250, 240, 0.82);
  border: 3rpx solid rgba(223, 189, 131, 0.54);
  border-radius: 28rpx;
}

.tasks-state__text {
  font-size: 30rpx;
  font-weight: 800;
  color: #5e3c22;
}

.tasks-state__retry {
  height: 62rpx;
  padding: 0 28rpx;
  font-size: 26rpx;
  font-weight: 900;
  color: #fff;
  background: #f26a21;
  border-radius: 22rpx;
}

:global(.tasks-page) {
  min-height: 100vh;
  overflow-x: hidden;
  color: #4a2f1b;
  background: #f8efd9;
}

:global(.tasks-page__paper) {
  width: 100%;
  max-width: 430px;
  min-height: 100vh;
  margin: 0 auto;
  padding: calc(28rpx + env(safe-area-inset-top)) 34rpx calc(190rpx + env(safe-area-inset-bottom));
}

:global(.tasks-header) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 30rpx;
}

:global(.tasks-header__back),
:global(.tasks-header__notice) {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 64rpx;
  height: 64rpx;
  font-weight: 900;
  color: #4a2f1b;
}

:global(.tasks-header__back) {
  font-size: 64rpx;
}

:global(.tasks-header__notice) {
  position: relative;
  font-size: 24rpx;
  border: 3rpx solid #4a2f1b;
  border-radius: 30rpx 30rpx 24rpx 24rpx;
}

:global(.tasks-header__dot) {
  position: absolute;
  top: -6rpx;
  right: -2rpx;
  width: 16rpx;
  height: 16rpx;
  background: #f26a21;
  border-radius: 50%;
}

:global(.tasks-header__title-wrap) {
  position: relative;
  flex: 1;
  text-align: center;
}

:global(.tasks-header__title) {
  font-size: 48rpx;
  font-weight: 900;
  line-height: 1;
}

:global(.tasks-hero) {
  position: relative;
  display: flex;
  min-height: 292rpx;
  margin-bottom: 22rpx;
  overflow: hidden;
  background: rgba(255, 247, 232, 0.92);
  border: 4rpx solid rgba(223, 189, 131, 0.62);
  border-radius: 34rpx;
  box-shadow: 0 16rpx 28rpx rgba(97, 63, 28, 0.1);
}

:global(.tasks-hero__copy) {
  position: relative;
  z-index: 2;
  width: 50%;
  padding: 62rpx 10rpx 26rpx 28rpx;
}

:global(.tasks-hero__title) {
  display: block;
  margin-bottom: 16rpx;
  font-size: 44rpx;
  font-weight: 900;
  line-height: 1.14;
}

:global(.tasks-hero__desc) {
  display: block;
  margin-bottom: 42rpx;
  font-size: 30rpx;
  color: #5e3c22;
}

:global(.tasks-hero__tags) {
  display: flex;
  flex-wrap: wrap;
  gap: 14rpx;
}

:global(.tasks-hero__tag) {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 58rpx;
  padding: 0 18rpx;
  font-size: 25rpx;
  font-weight: 800;
  border: 2rpx solid rgba(190, 142, 78, 0.28);
  border-radius: 22rpx;
}

:global(.tasks-hero__tag-icon) {
  margin-right: 8rpx;
  font-size: 20rpx;
}

:global(.tasks-hero__tag--orange) {
  color: #d94b12;
  background: #fff1d8;
}

:global(.tasks-hero__tag--blue) {
  color: #235b83;
  background: #dfeff8;
}

:global(.tasks-hero__art) {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 58%;
  background: #bfe1f5;
}

:global(.tasks-palace) {
  position: absolute;
  right: 24rpx;
  bottom: 32rpx;
  width: 310rpx;
}

:global(.tasks-palace__roof) {
  height: 74rpx;
  background: #ee9d1f;
  border: 4rpx solid rgba(126, 82, 35, 0.24);
  border-radius: 70rpx 70rpx 16rpx 16rpx;
}

:global(.tasks-palace__body) {
  height: 96rpx;
  margin: -4rpx 24rpx 0;
  background: #d45528;
  border-radius: 8rpx;
}

:global(.tasks-palace__stairs) {
  width: 210rpx;
  height: 38rpx;
  margin: 10rpx auto 0;
  background: rgba(255, 250, 240, 0.86);
  border-radius: 12rpx;
}

:global(.tasks-progress) {
  display: flex;
  align-items: center;
  min-height: 112rpx;
  margin-bottom: 20rpx;
  padding: 18rpx 24rpx;
  background: rgba(255, 250, 240, 0.82);
  border: 3rpx solid rgba(223, 189, 131, 0.54);
  border-radius: 28rpx;
}

:global(.tasks-progress__icon) {
  position: relative;
  flex-shrink: 0;
  width: 70rpx;
  height: 78rpx;
  margin-right: 22rpx;
  background: #fff7e8;
  border: 5rpx solid #df8b22;
  border-radius: 16rpx;
}

:global(.tasks-progress__content) {
  flex: 1;
  min-width: 0;
}

:global(.tasks-progress__text) {
  display: block;
  margin-bottom: 14rpx;
  font-size: 34rpx;
  font-weight: 800;
}

:global(.tasks-progress__count) {
  color: #d94b12;
}

:global(.tasks-progress__bar) {
  height: 22rpx;
  overflow: hidden;
  background: #f8e8c5;
  border: 2rpx solid rgba(223, 189, 131, 0.42);
  border-radius: 999rpx;
}

:global(.tasks-progress__fill) {
  height: 100%;
  background: linear-gradient(90deg, #ff8a1c, #f26a21);
  border-radius: 999rpx;
}

:global(.tasks-page__list) {
  display: flex;
  flex-direction: column;
  gap: 18rpx;
  margin-bottom: 24rpx;
}

:global(.tasks-reward) {
  position: relative;
  display: flex;
  align-items: center;
  min-height: 132rpx;
  padding: 18rpx 26rpx;
  margin-right: 88rpx;
  overflow: hidden;
  background: rgba(255, 240, 189, 0.56);
  border: 3rpx solid rgba(223, 189, 131, 0.58);
  border-radius: 28rpx;
}

:global(.tasks-reward__medal) {
  position: relative;
  flex-shrink: 0;
  width: 82rpx;
  height: 82rpx;
  margin-right: 24rpx;
  background: #f4aa23;
  border: 6rpx solid #f7cf75;
  border-radius: 50%;
}

:global(.tasks-reward__copy) {
  flex: 1;
  min-width: 0;
}

:global(.tasks-reward__title) {
  display: block;
  margin-bottom: 10rpx;
  font-size: 34rpx;
  font-weight: 900;
}

:global(.tasks-reward__desc) {
  display: block;
  font-size: 26rpx;
  color: #5e3c22;
}

:global(.tasks-reward__gift) {
  position: relative;
  flex-shrink: 0;
  width: 90rpx;
  height: 74rpx;
  background: #e6863b;
  border: 4rpx solid #f7c379;
  border-radius: 14rpx;
}
</style>
