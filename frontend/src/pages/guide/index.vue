<template>
  <view class="guide-page">
    <view class="guide-page__paper">
      <view class="guide-header">
        <view class="guide-header__seal">童旅记</view>
        <view class="guide-header__title-wrap">
          <text class="guide-header__eyebrow">MUSEUM NOTEBOOK</text>
          <text class="guide-header__title">讲解卡</text>
        </view>
        <view class="guide-header__star" aria-hidden="true"></view>
      </view>

      <view v-if="!displayPlan" class="guide-state-card">
        <text class="guide-state-card__stamp">空白讲解卡</text>
        <text class="guide-state-card__title">还没有探索计划</text>
        <text class="guide-state-card__text">先创建计划，再准备专属讲解卡。</text>
      </view>

      <template v-else>
        <view class="guide-hero">
          <view class="guide-hero__copy">
            <text class="guide-hero__eyebrow">给孩子的旅行讲解</text>
            <text class="guide-hero__title">{{ guideDestination }}</text>
            <text class="guide-hero__desc">把眼前的文化故事，讲成孩子听得懂的发现。</text>

            <button class="guide-audio" @click="toggleAudio">
              <view class="guide-audio__icon" :class="{ 'guide-audio__icon--playing': audioState === 'playing' }" aria-hidden="true">
                <view></view>
              </view>
              <view class="guide-audio__copy">
                <text class="guide-audio__title">{{ audioTitle }}</text>
                <text class="guide-audio__status">{{ audioStatus }}</text>
              </view>
            </button>
          </view>

          <view class="guide-polaroid-stack">
            <view class="guide-polaroid guide-polaroid--back"></view>
            <view class="guide-polaroid guide-polaroid--middle"></view>
            <view class="guide-polaroid guide-polaroid--front">
              <view class="guide-polaroid__tape"></view>
              <image class="guide-polaroid__image" src="../../assets/guide/guide-palace-detail.webp" mode="aspectFill" />
              <view class="guide-polaroid__caption">
                <text>今天的发现</text>
                <view class="guide-polaroid__caption-spark" aria-hidden="true"></view>
              </view>
            </view>
          </view>
        </view>

        <view v-if="isGuideBusy" class="guide-state-card">
          <text class="guide-state-card__stamp">正在准备</text>
          <text class="guide-state-card__title">{{ guideLoadingTitle }}</text>
          <text class="guide-state-card__text">请稍等，正在整理适合孩子听的讲解内容。</text>
        </view>

        <view v-else-if="guideStore.error" class="guide-state-card">
          <text class="guide-state-card__stamp">小小提醒</text>
          <text class="guide-state-card__title">{{ guideErrorTitle }}</text>
          <text class="guide-state-card__text">{{ guideErrorText }}</text>
          <button class="guide-retry" @click="reloadGuide">重新加载</button>
        </view>

        <template v-else-if="currentGuide.id">
          <view class="guide-section-heading">
            <text>翻开今天的讲解</text>
            <text>01</text>
          </view>

          <view class="guide-card guide-card--listen">
            <view class="guide-card__tape"></view>
            <view class="guide-card__avatar">
              <view class="guide-card__circle">
                <view class="guide-card__icon guide-card__icon--listen" aria-hidden="true"></view>
              </view>
            </view>
            <view class="guide-card__body">
              <text class="guide-card__eyebrow">故事时间</text>
              <text class="guide-card__title">讲给孩子听</text>
              <text v-for="intro in currentGuide.childIntro" :key="intro" class="guide-card__text">{{ intro }}</text>
            </view>
          </view>

          <view class="guide-card guide-card--ask">
            <view class="guide-card__avatar">
              <view class="guide-card__circle">
                <view class="guide-card__icon guide-card__icon--ask" aria-hidden="true"></view>
              </view>
            </view>
            <view class="guide-card__body">
              <text class="guide-card__eyebrow">一起想一想</text>
              <text class="guide-card__title">可以先问孩子</text>
              <view class="guide-question-list">
                <text v-for="(question, index) in currentGuide.questions" :key="question" class="guide-question-list__item">
                  <text class="guide-question-list__number">0{{ index + 1 }}</text>
                  {{ question }}
                </text>
              </view>
            </view>
          </view>

          <view class="guide-card guide-card--focus">
            <view class="guide-card__avatar">
              <view class="guide-card__circle">
                <view class="guide-card__icon guide-card__icon--focus" aria-hidden="true"></view>
              </view>
            </view>
            <view class="guide-card__body">
              <text class="guide-card__eyebrow">观察小任务</text>
              <text class="guide-card__title">今天重点看</text>
              <view class="guide-focus-list">
                <view v-for="(focus, index) in currentGuide.focusItems" :key="focus" class="guide-focus-list__item">
                  <view class="guide-focus-list__dot" aria-hidden="true"></view>
                  <text>{{ focus }}</text>
                  <text class="guide-focus-list__index">0{{ index + 1 }}</text>
                </view>
              </view>
            </view>
          </view>
        </template>
      </template>
    </view>

    <AppTabbar active="explore" />
  </view>
</template>

<script>
import AppTabbar from '../../components/AppTabbar.vue'
import { useGuideStore } from '../../stores/guide'
import { usePlanStore } from '../../stores/plan'
import { useUserStore } from '../../stores/user'
import { ensureCurrentPlanReady } from '../../utils/planRecovery'
import { endUserSession } from '../../utils/sessionBoundary'

export default {
  components: {
    AppTabbar,
  },
  data() {
    return {
      audioState: 'idle',
    }
  },
  computed: {
    guideStore() {
      return useGuideStore()
    },
    planStore() {
      return usePlanStore()
    },
    userStore() {
      return useUserStore()
    },
    displayPlan() {
      return this.planStore.currentPlan
    },
    currentGuide() {
      return this.guideStore.currentGuide || {}
    },
    guideDestination() {
      return this.currentGuide.destination || this.displayPlan?.destination || ''
    },
    isGuideBusy() {
      return this.guideStore.isLoading || this.guideStore.isGenerating
    },
    guideLoadingTitle() {
      return this.guideStore.isGenerating ? '正在准备专属讲解卡...' : '正在加载讲解卡...'
    },
    guideErrorTitle() {
      return this.guideStore.error?.code === 'PLAN_NOT_FOUND' ? '没有找到当前计划' : '讲解卡加载失败'
    },
    guideErrorText() {
      const messages = {
        NETWORK_ERROR: '暂时无法连接服务，请稍后重试。',
        PLAN_NOT_FOUND: '当前计划可能已经不存在。',
        PLAN_NOT_READY: '当前计划还没有准备好讲解卡。',
        UNAUTHORIZED: '登录状态已失效，请重新登录。',
        TOKEN_EXPIRED: '登录状态已失效，请重新登录。',
        INVALID_TOKEN: '登录状态已失效，请重新登录。',
      }
      return messages[this.guideStore.error?.code] || '讲解卡加载失败，请重试。'
    },
    audioTitle() {
      if (!this.currentGuide.audioUrl) {
        return '语音讲解'
      }
      if (this.audioState === 'playing') {
        return '暂停讲解'
      }
      if (this.audioState === 'paused') {
        return '继续讲解'
      }
      return '播放讲解'
    },
    audioStatus() {
      if (!this.currentGuide.audioUrl) {
        return '暂不提供语音讲解'
      }
      if (this.audioState === 'playing') {
        return '正在播放'
      }
      if (this.audioState === 'paused') {
        return '已暂停'
      }
      return '点击播放语音'
    },
  },
  async onShow() {
    await this.restoreCurrentPlan()
  },
  methods: {
    async restoreCurrentPlan() {
      try {
        const result = await ensureCurrentPlanReady()
        const planId = result.currentPlan?.id
        if (!planId) {
          this.guideStore.resetSessionState()
          return
        }
        await this.guideStore.ensureGuide(planId)
      } catch (error) {
        if (['UNAUTHORIZED', 'TOKEN_EXPIRED', 'INVALID_TOKEN'].includes(error?.code) || error?.statusCode === 401) {
          await endUserSession()
        }
      }
    },
    async reloadGuide() {
      await this.restoreCurrentPlan()
    },
    showToast(title) {
      uni.showToast({
        title,
        icon: 'none',
      })
    },
    toggleAudio() {
      if (!this.currentGuide.audioUrl) {
        this.showToast('语音讲解暂未提供')
        return
      }
      if (this.audioState === 'playing') {
        this.audioState = 'paused'
        return
      }
      this.audioState = 'playing'
    },
  },
}
</script>

<style scoped>
.guide-page {
  min-height: 100vh;
  overflow-x: hidden;
  color: var(--tl-text-main);
  background:
    radial-gradient(circle at 85% 5%, rgba(211, 232, 242, 0.58) 0, rgba(211, 232, 242, 0) 200rpx),
    linear-gradient(135deg, rgba(141, 101, 49, 0.04) 0 1rpx, transparent 1rpx 24rpx),
    var(--tl-bg);
}

.guide-page__paper {
  width: 100%;
  max-width: var(--tl-content-max-width);
  min-height: 100vh;
  margin: 0 auto;
  padding: calc(var(--tl-page-padding) + var(--tl-safe-top)) var(--tl-page-padding) calc(var(--tl-tabbar-height) + var(--tl-safe-bottom) + 56rpx);
}

.guide-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 86rpx;
  margin-bottom: 30rpx;
}

.guide-header__seal {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64rpx;
  height: 64rpx;
  font-size: 17rpx;
  font-weight: 900;
  color: var(--tl-primary-deep);
  background: var(--tl-yellow);
  border: 2rpx solid var(--tl-primary);
  border-radius: 50%;
  transform: rotate(-9deg);
}

.guide-header__title-wrap {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
}

.guide-header__eyebrow {
  margin-bottom: 5rpx;
  font-size: 16rpx;
  font-weight: 800;
  color: var(--tl-primary);
  letter-spacing: 3rpx;
}

.guide-header__title {
  font-size: 48rpx;
  font-weight: 900;
  line-height: 1.1;
}

.guide-header__title::after {
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

.guide-header__star {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 26rpx;
  height: 26rpx;
  color: var(--tl-primary);
  transform: rotate(14deg);
}

.guide-header__star::after,
.guide-polaroid__caption-spark::after,
.guide-focus-list__dot::after {
  position: absolute;
  inset: 0;
  content: '';
  background: currentColor;
  border-radius: 5rpx;
  transform: rotate(45deg);
}

.guide-state-card {
  padding: 52rpx 36rpx;
  text-align: center;
  background: var(--tl-paper);
  border: 3rpx dashed var(--tl-line);
  border-radius: var(--tl-radius-lg);
  box-shadow: var(--tl-shadow-card);
}

.guide-state-card__stamp {
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

.guide-state-card__title {
  display: block;
  font-size: 32rpx;
  font-weight: 900;
}

.guide-state-card__text {
  display: block;
  margin-top: 12rpx;
  font-size: 25rpx;
  line-height: 1.6;
  color: var(--tl-text-secondary);
}

.guide-hero {
  position: relative;
  display: flex;
  min-height: 356rpx;
  margin-bottom: 26rpx;
  overflow: hidden;
  background: var(--tl-paper);
  border: 3rpx solid var(--tl-line);
  border-radius: var(--tl-radius-lg);
  box-shadow: var(--tl-shadow-card);
}

.guide-hero::after {
  position: absolute;
  right: -22rpx;
  bottom: -44rpx;
  width: 130rpx;
  height: 130rpx;
  content: '';
  border: 3rpx solid var(--tl-green-deep);
  border-radius: 80% 20% 72% 28%;
  opacity: 0.4;
  transform: rotate(36deg);
}

.guide-hero__copy {
  position: relative;
  z-index: 2;
  display: flex;
  flex: 0 0 49%;
  flex-direction: column;
  align-items: flex-start;
  padding: 44rpx 6rpx 24rpx 28rpx;
}

.guide-hero__eyebrow {
  display: block;
  margin-bottom: 12rpx;
  font-size: 20rpx;
  font-weight: 800;
  color: var(--tl-primary-deep);
  letter-spacing: 1rpx;
}

.guide-hero__title {
  display: -webkit-box;
  max-width: 290rpx;
  overflow: hidden;
  font-size: 48rpx;
  font-weight: 900;
  line-height: 1.18;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.guide-hero__desc {
  display: block;
  max-width: 258rpx;
  margin-top: 14rpx;
  font-size: 25rpx;
  line-height: 1.6;
  color: var(--tl-text-secondary);
}

.guide-audio {
  display: flex;
  align-items: center;
  width: 100%;
  margin-top: auto;
  padding: 12rpx 13rpx;
  text-align: left;
  background: rgba(255, 241, 216, 0.72);
  border: 2rpx solid rgba(225, 123, 44, 0.28);
  border-radius: 18rpx;
}

.guide-audio__icon {
  position: relative;
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  width: 52rpx;
  height: 52rpx;
  margin-right: 10rpx;
  color: var(--tl-paper);
  background: var(--tl-primary);
  border-radius: 50%;
}

.guide-audio__icon view {
  width: 0;
  height: 0;
  margin-left: 5rpx;
  border-top: 10rpx solid transparent;
  border-bottom: 10rpx solid transparent;
  border-left: 15rpx solid currentColor;
}

.guide-audio__icon--playing view {
  width: 13rpx;
  height: 20rpx;
  margin-left: 0;
  border: 0;
  border-right: 4rpx solid currentColor;
  border-left: 4rpx solid currentColor;
}

.guide-audio__copy {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-width: 0;
}

.guide-audio__title {
  overflow: hidden;
  font-size: 20rpx;
  font-weight: 900;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.guide-audio__status {
  overflow: hidden;
  margin-top: 4rpx;
  font-size: 17rpx;
  line-height: 1.3;
  color: var(--tl-text-secondary);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.guide-polaroid-stack {
  position: absolute;
  top: 32rpx;
  right: 12rpx;
  z-index: 1;
  width: 298rpx;
  height: 258rpx;
}

.guide-polaroid {
  position: absolute;
  width: 208rpx;
  height: 232rpx;
  border: 2rpx solid var(--tl-line);
  border-radius: 16rpx;
  box-shadow: 0 10rpx 16rpx rgba(92, 60, 29, 0.09);
}

.guide-polaroid--back {
  top: 16rpx;
  right: 5rpx;
  background: rgba(198, 219, 175, 0.72);
  transform: rotate(10deg);
}

.guide-polaroid--middle {
  top: 5rpx;
  right: 35rpx;
  background: rgba(247, 195, 156, 0.7);
  transform: rotate(-8deg);
}

.guide-polaroid--front {
  top: 0;
  right: 22rpx;
  z-index: 2;
  padding: 12rpx 12rpx 16rpx;
  overflow: visible;
  background: var(--tl-paper);
  transform: rotate(5deg);
}

.guide-polaroid__tape {
  position: absolute;
  top: -11rpx;
  left: 50%;
  z-index: 2;
  width: 88rpx;
  height: 24rpx;
  background: rgba(243, 205, 114, 0.7);
  transform: translateX(-50%) rotate(-7deg);
}

.guide-polaroid__image {
  width: 100%;
  height: 144rpx;
  border-radius: 9rpx;
}

.guide-polaroid__caption {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 13rpx 5rpx 0;
  font-size: 18rpx;
  font-weight: 900;
  color: var(--tl-text-secondary);
}

.guide-polaroid__caption-spark {
  position: relative;
  width: 16rpx;
  height: 16rpx;
  color: var(--tl-primary);
  transform: rotate(45deg);
}

.guide-section-heading {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin: 0 6rpx 16rpx;
  font-size: 34rpx;
  font-weight: 900;
}

.guide-section-heading text:last-child {
  font-size: 19rpx;
  color: var(--tl-primary);
  letter-spacing: 2rpx;
}

.guide-card {
  position: relative;
  display: flex;
  gap: 18rpx;
  min-height: 164rpx;
  margin-bottom: 18rpx;
  padding: 22rpx 22rpx 22rpx 18rpx;
  overflow: hidden;
  background: var(--tl-paper);
  border: 2rpx solid var(--tl-line);
  border-radius: var(--tl-radius-md);
  box-shadow: 0 8rpx 14rpx rgba(92, 60, 29, 0.05);
}

.guide-card--listen {
  border-color: rgba(230, 147, 61, 0.54);
}

.guide-card--listen .guide-card__circle { color: var(--tl-primary-deep); background: #fff0d2; }
.guide-card--ask .guide-card__circle { color: var(--tl-blue-deep); background: var(--tl-blue); }
.guide-card--focus .guide-card__circle { color: var(--tl-green-deep); background: var(--tl-green); }

.guide-card__tape {
  position: absolute;
  top: 0;
  right: 44rpx;
  width: 84rpx;
  height: 18rpx;
  background: rgba(243, 205, 114, 0.68);
  transform: rotate(4deg);
}

.guide-card__avatar {
  flex: 0 0 auto;
  width: 86rpx;
  padding-top: 5rpx;
}

.guide-card__circle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 80rpx;
  height: 80rpx;
  border: 4rpx solid var(--tl-paper);
  border-radius: 50%;
  box-shadow: 0 5rpx 8rpx rgba(92, 60, 29, 0.08);
}

.guide-card__icon {
  position: relative;
  display: block;
  width: 26rpx;
  height: 26rpx;
}

.guide-card__icon::before,
.guide-card__icon::after {
  position: absolute;
  box-sizing: border-box;
  content: '';
}

.guide-card__icon--listen::before {
  top: 3rpx;
  left: 2rpx;
  width: 15rpx;
  height: 18rpx;
  border: 3rpx solid currentColor;
  border-radius: 8rpx;
}

.guide-card__icon--listen::after {
  right: 2rpx;
  bottom: 3rpx;
  width: 11rpx;
  height: 3rpx;
  background: currentColor;
  border-radius: 999rpx;
}

.guide-card__icon--ask::before,
.guide-card__icon--focus::before {
  inset: 2rpx;
  border: 3rpx solid currentColor;
  border-radius: 50%;
}

.guide-card__icon--ask::after {
  top: 7rpx;
  left: 12rpx;
  width: 3rpx;
  height: 10rpx;
  background: currentColor;
  border-radius: 999rpx;
}

.guide-card__icon--focus::after {
  top: 10rpx;
  left: 10rpx;
  width: 6rpx;
  height: 6rpx;
  background: currentColor;
  border-radius: 50%;
}

.guide-card__body {
  position: relative;
  z-index: 1;
  flex: 1;
  min-width: 0;
}

.guide-card__eyebrow {
  display: block;
  margin-bottom: 4rpx;
  font-size: 18rpx;
  font-weight: 800;
  color: var(--tl-text-secondary);
  letter-spacing: 1rpx;
}

.guide-card__title {
  display: block;
  margin-bottom: 10rpx;
  font-size: 31rpx;
  font-weight: 900;
}

.guide-card__text {
  display: block;
  margin-bottom: 6rpx;
  font-size: 24rpx;
  line-height: 1.55;
  color: var(--tl-text-secondary);
}

.guide-question-list {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
}

.guide-question-list__item {
  display: flex;
  gap: 9rpx;
  align-items: flex-start;
  font-size: 24rpx;
  line-height: 1.45;
  color: var(--tl-text-secondary);
}

.guide-question-list__number {
  flex: 0 0 auto;
  padding-top: 2rpx;
  font-size: 17rpx;
  font-weight: 900;
  color: var(--tl-primary);
}

.guide-focus-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10rpx;
}

.guide-focus-list__item {
  display: flex;
  gap: 6rpx;
  align-items: center;
  min-width: 126rpx;
  max-width: 100%;
  padding: 9rpx 12rpx;
  font-size: 21rpx;
  font-weight: 800;
  color: var(--tl-text-secondary);
  background: var(--tl-paper-deep);
  border: 2rpx solid rgba(151, 109, 59, 0.24);
  border-radius: 16rpx;
}

.guide-focus-list__dot {
  position: relative;
  flex: 0 0 auto;
  width: 11rpx;
  height: 11rpx;
  color: var(--tl-primary);
  transform: rotate(45deg);
}

.guide-focus-list__index {
  margin-left: auto;
  font-size: 14rpx;
  color: var(--tl-text-secondary);
  opacity: 0.75;
}

.guide-retry {
  display: inline-flex;
  min-height: 60rpx;
  margin-top: 20rpx;
  padding: 0 26rpx;
  font-size: 24rpx;
  font-weight: 900;
  line-height: 60rpx;
  color: var(--tl-paper);
  background: var(--tl-primary);
  border: 2rpx solid var(--tl-primary-deep);
  border-radius: var(--tl-radius-sm);
}

@media (max-width: 360px) {
  .guide-page__paper {
    padding-right: 24rpx;
    padding-left: 24rpx;
  }

  .guide-hero__copy {
    flex-basis: 53%;
    padding-left: 21rpx;
  }

  .guide-hero__title {
    font-size: 43rpx;
  }

  .guide-polaroid-stack {
    right: -14rpx;
    transform: scale(0.91);
    transform-origin: right top;
  }

  .guide-audio {
    padding: 9rpx;
  }

  .guide-audio__status {
    display: none;
  }

  .guide-card {
    gap: 12rpx;
    padding-right: 16rpx;
    padding-left: 14rpx;
  }

  .guide-card__avatar {
    width: 72rpx;
  }

  .guide-card__circle {
    width: 68rpx;
    height: 68rpx;
  }
}

@media (min-width: 431px) {
  .guide-page__paper {
    padding: calc(18px + var(--tl-safe-top)) 18px calc(var(--tl-tabbar-height) + var(--tl-safe-bottom) + 34px);
  }

  .guide-header {
    min-height: 44px;
    margin-bottom: 16px;
  }

  .guide-header__seal {
    width: 32px;
    height: 32px;
  }

  .guide-header__star { width: 13px; height: 13px; }

  .guide-header__seal { font-size: 10px; }
  .guide-header__eyebrow { margin-bottom: 3px; font-size: 10px; }
  .guide-header__title { font-size: 28px; }
  .guide-header__star { font-size: 0; }

  .guide-hero {
    min-height: 205px;
    border-width: 2px;
  }

  .guide-hero__copy {
    padding: 24px 4px 15px 15px;
  }

  .guide-hero__eyebrow { font-size: 12px; }
  .guide-hero__title { max-width: 158px; font-size: 28px; }
  .guide-hero__desc { max-width: 155px; font-size: 13px; }
  .guide-audio { padding: 7px; }
  .guide-audio__icon { width: 28px; height: 28px; font-size: 0; }
  .guide-audio__title { font-size: 11px; }
  .guide-audio__status { font-size: 9px; }
  .guide-polaroid-stack { top: 18px; right: 6px; transform: scale(0.59); transform-origin: right top; }
  .guide-section-heading { font-size: 20px; }
  .guide-card { min-height: 96px; padding: 13px; }
  .guide-card__avatar { width: 46px; }
  .guide-card__circle { width: 42px; height: 42px; }
  .guide-card__icon { font-size: 16px; }
  .guide-card__title { font-size: 19px; }
  .guide-card__text,
  .guide-question-list__item { font-size: 14px; }
  .guide-focus-list__item { font-size: 12px; }
}
</style>
