<template>
  <view class="guide-page">
    <view class="guide-page__paper">
      <view class="guide-header">
        <view class="guide-header__spacer"></view>
        <view class="guide-header__title-wrap">
          <text class="guide-header__spark">小旅</text>
          <text class="guide-header__title">讲解卡</text>
        </view>
        <button class="guide-header__notice" @click="openAiShortcut('讲简单一点')">
          <text>铃</text>
          <view class="guide-header__dot"></view>
        </button>
      </view>

      <view v-if="!displayPlan" class="guide-card guide-card--listen">
        <view class="guide-card__body">
          <text class="guide-card__title">还没有探索计划</text>
          <text class="guide-card__text">先创建计划，再准备专属讲解卡。</text>
        </view>
      </view>

      <template v-else>
      <view class="guide-hero">
        <view class="guide-hero__copy">
          <text class="guide-hero__eyebrow">给孩子的旅行讲解</text>
          <text class="guide-hero__title">{{ guideDestination }}</text>
          <text class="guide-hero__desc">家长轻松讲给孩子听</text>

          <button class="guide-audio" @click="toggleAudio">
            <view class="guide-audio__icon">
              <text v-if="audioState === 'playing'">停</text>
              <text v-else>播</text>
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
            <view class="guide-polaroid__image">
              <view class="guide-palace">
                <view class="guide-palace__sky"></view>
                <view class="guide-palace__roof"></view>
                <view class="guide-palace__hall"></view>
                <view class="guide-palace__stairs"></view>
              </view>
            </view>
            <view class="guide-polaroid__line"></view>
            <view class="guide-polaroid__line guide-polaroid__line--short"></view>
            <view class="guide-polaroid__star">星</view>
          </view>
        </view>
      </view>

      <view v-if="isGuideBusy" class="guide-card guide-card--listen">
        <view class="guide-card__body">
          <text class="guide-card__title">{{ guideLoadingTitle }}</text>
          <text class="guide-card__text">请稍等，小旅正在整理适合孩子听的讲解内容。</text>
        </view>
      </view>

      <view v-else-if="guideStore.error" class="guide-card guide-card--listen">
        <view class="guide-card__body">
          <text class="guide-card__title">{{ guideErrorTitle }}</text>
          <text class="guide-card__text">{{ guideErrorText }}</text>
          <button class="guide-retry" @click="reloadGuide">重新加载</button>
        </view>
      </view>

      <template v-else-if="currentGuide.id">
      <view class="guide-card guide-card--listen">
        <view class="guide-card__avatar">
          <view class="guide-card__circle"></view>
        </view>
        <view class="guide-card__body">
          <text class="guide-card__title">讲给孩子听</text>
          <text v-for="intro in currentGuide.childIntro" :key="intro" class="guide-card__text">{{ intro }}</text>
        </view>
      </view>

      <view class="guide-card guide-card--ask">
        <view class="guide-card__avatar">
          <view class="guide-card__circle"></view>
        </view>
        <view class="guide-card__body">
          <text class="guide-card__title">可以先问孩子</text>
          <view class="guide-question-list">
            <text v-for="question in currentGuide.questions" :key="question" class="guide-question-list__item">{{ question }}</text>
          </view>
        </view>
      </view>

      <view class="guide-card guide-card--focus">
        <view class="guide-card__avatar">
          <view class="guide-card__circle"></view>
        </view>
        <view class="guide-card__body">
          <text class="guide-card__title">今天重点看</text>
          <view class="guide-focus-list">
            <view v-for="focus in currentGuide.focusItems" :key="focus" class="guide-focus-list__item">
              <text>{{ focus }}</text>
            </view>
          </view>
        </view>
      </view>

      <view class="guide-ai-grid">
        <button
          v-for="shortcut in aiShortcuts"
          :key="shortcut.title"
          class="guide-ai-card"
          :class="`guide-ai-card--${shortcut.theme}`"
          @click="openAiShortcut(shortcut.title)"
        >
          <view class="guide-ai-card__icon">{{ shortcut.icon }}</view>
          <text class="guide-ai-card__text">{{ shortcut.title }}</text>
        </button>
      </view>
      </template>
      </template>
    </view>

    <AiPet />
    <AppTabbar active="plan" />
  </view>
</template>

<script>
import AiPet from '../../components/AiPet.vue'
import AppTabbar from '../../components/AppTabbar.vue'
import { useGuideStore } from '../../stores/guide'
import { usePetStore } from '../../stores/pet'
import { usePlanStore } from '../../stores/plan'
import { useUserStore } from '../../stores/user'
import { ensureCurrentPlanReady } from '../../utils/planRecovery'

export default {
  components: {
    AiPet,
    AppTabbar,
  },
  data() {
    return {
      audioState: 'idle',
      aiShortcuts: [
        { title: '简单一点', icon: '简', theme: 'blue' },
        { title: '孩子能懂', icon: '懂', theme: 'green' },
        { title: '讲个故事', icon: '故', theme: 'orange' },
      ],
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
    usePetStore().setPageContext('guide', this.displayPlan?.id)
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
          this.planStore.resetSessionState()
          this.guideStore.resetSessionState()
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
    openAiShortcut(text) {
      const petStore = usePetStore()
      petStore.setPageContext('guide', this.displayPlan?.id)
      petStore.openChat()
      this.lastShortcut = text
    },
  },
}
</script>

<style scoped>
.guide-page {
  min-height: 100vh;
  overflow-x: hidden;
  color: #4a2f1b;
  background:
    radial-gradient(circle at 14% 10%, rgba(255, 238, 181, 0.55) 0, rgba(255, 238, 181, 0) 110rpx),
    linear-gradient(135deg, rgba(148, 104, 48, 0.05) 0 1rpx, transparent 1rpx 22rpx),
    #f8efd9;
}

.guide-page__paper {
  width: 100%;
  max-width: 430px;
  min-height: 100vh;
  margin: 0 auto;
  padding: calc(28rpx + env(safe-area-inset-top)) 34rpx calc(260rpx + env(safe-area-inset-bottom));
}

.guide-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 30rpx;
}

.guide-header__spacer,
.guide-header__notice {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 64rpx;
  height: 64rpx;
  font-weight: 900;
  color: #4a2f1b;
}

.guide-header__notice {
  position: relative;
  font-size: 24rpx;
  border: 3rpx solid #4a2f1b;
  border-radius: 30rpx 30rpx 24rpx 24rpx;
}

.guide-header__dot {
  position: absolute;
  top: -6rpx;
  right: -2rpx;
  width: 16rpx;
  height: 16rpx;
  background: #f26a21;
  border-radius: 50%;
}

.guide-header__title-wrap {
  position: relative;
  flex: 1;
  text-align: center;
}

.guide-header__spark {
  position: absolute;
  top: -18rpx;
  left: 88rpx;
  font-size: 20rpx;
  font-weight: 900;
  color: #f4aa23;
  transform: rotate(-22deg);
}

.guide-header__title {
  font-size: 48rpx;
  font-weight: 900;
  line-height: 1;
}

.guide-hero {
  position: relative;
  display: flex;
  min-height: 350rpx;
  margin-bottom: 22rpx;
  padding: 54rpx 26rpx 32rpx;
  overflow: hidden;
  background: rgba(255, 247, 232, 0.92);
  border: 4rpx solid rgba(190, 142, 78, 0.42);
  border-radius: 36rpx;
  box-shadow: 0 16rpx 28rpx rgba(97, 63, 28, 0.1);
}

.guide-hero__copy {
  position: relative;
  z-index: 2;
  width: 48%;
}

.guide-hero__eyebrow {
  display: block;
  margin-bottom: 12rpx;
  font-size: 28rpx;
  font-weight: 800;
  color: #8a6d54;
}

.guide-hero__title {
  display: block;
  font-size: 50rpx;
  font-weight: 900;
  line-height: 1.1;
}

.guide-hero__desc {
  display: block;
  margin-top: 18rpx;
  font-size: 28rpx;
  line-height: 1.45;
  color: #5e3c22;
}

.guide-audio {
  display: flex;
  align-items: flex-start;
  width: 100%;
  margin-top: 34rpx;
  text-align: left;
}

.guide-audio__icon {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 76rpx;
  height: 76rpx;
  margin-right: 14rpx;
  font-size: 26rpx;
  font-weight: 900;
  color: #fffaf0;
  background: #f26a21;
  border: 5rpx solid rgba(255, 250, 240, 0.9);
  border-radius: 50%;
  box-shadow: 0 10rpx 16rpx rgba(217, 75, 18, 0.2);
}

.guide-audio__copy {
  flex: 1;
  min-width: 0;
}

.guide-audio__title,
.guide-audio__status {
  display: block;
}

.guide-audio__title {
  margin-bottom: 6rpx;
  font-size: 24rpx;
  font-weight: 900;
  line-height: 1.25;
}

.guide-audio__status {
  font-size: 19rpx;
  line-height: 1.35;
  color: #8a6d54;
}

.guide-polaroid-stack {
  position: absolute;
  top: 46rpx;
  right: 22rpx;
  width: 282rpx;
  height: 248rpx;
}

.guide-polaroid {
  position: absolute;
  width: 218rpx;
  height: 238rpx;
  background: #fffaf0;
  border: 3rpx solid rgba(190, 142, 78, 0.3);
  border-radius: 18rpx;
  box-shadow: 0 12rpx 20rpx rgba(97, 63, 28, 0.12);
}

.guide-polaroid--back {
  top: 8rpx;
  right: 8rpx;
  background: #dceecb;
  transform: rotate(8deg);
}

.guide-polaroid--middle {
  top: 4rpx;
  right: 34rpx;
  background: #f4c7a9;
  transform: rotate(-8deg);
}

.guide-polaroid--front {
  top: 0;
  right: 22rpx;
  z-index: 2;
  padding: 14rpx 14rpx 18rpx;
  transform: rotate(6deg);
}

.guide-polaroid__image {
  height: 128rpx;
  overflow: hidden;
  background: #cfe7f5;
  border: 2rpx solid rgba(126, 82, 35, 0.16);
  border-radius: 12rpx;
}

.guide-palace {
  position: relative;
  height: 100%;
}

.guide-palace__sky {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 30% 24%, rgba(255, 255, 255, 0.86) 0 28rpx, transparent 30rpx),
    #bfe1f5;
}

.guide-palace__roof {
  position: absolute;
  right: 18rpx;
  bottom: 58rpx;
  left: 18rpx;
  height: 30rpx;
  background: #ee9d1f;
  border-radius: 40rpx 40rpx 10rpx 10rpx;
}

.guide-palace__hall {
  position: absolute;
  right: 28rpx;
  bottom: 24rpx;
  left: 28rpx;
  height: 42rpx;
  background:
    repeating-linear-gradient(90deg, rgba(90, 51, 26, 0.25) 0 5rpx, transparent 5rpx 20rpx),
    #d45528;
  border-radius: 6rpx;
}

.guide-palace__stairs {
  position: absolute;
  right: 58rpx;
  bottom: 10rpx;
  left: 58rpx;
  height: 14rpx;
  background: rgba(255, 250, 240, 0.9);
  border-radius: 8rpx;
}

.guide-polaroid__line {
  width: 126rpx;
  height: 6rpx;
  margin: 18rpx auto 0;
  background: rgba(190, 142, 78, 0.28);
  border-radius: 999rpx;
}

.guide-polaroid__line--short {
  width: 84rpx;
  margin-top: 10rpx;
}

.guide-polaroid__star {
  position: absolute;
  right: 18rpx;
  bottom: 18rpx;
  font-size: 20rpx;
  font-weight: 900;
  color: #f4aa23;
  transform: rotate(18deg);
}

.guide-card {
  position: relative;
  display: flex;
  gap: 22rpx;
  min-height: 168rpx;
  margin-bottom: 18rpx;
  padding: 24rpx 24rpx 24rpx 22rpx;
  overflow: hidden;
  background: rgba(255, 247, 232, 0.92);
  border: 3rpx solid rgba(190, 142, 78, 0.34);
  border-radius: 28rpx;
  box-shadow: 0 10rpx 18rpx rgba(97, 63, 28, 0.08);
}

.guide-card__avatar {
  position: relative;
  flex-shrink: 0;
  width: 118rpx;
  height: 118rpx;
}

.guide-card__circle {
  width: 118rpx;
  height: 118rpx;
  border: 5rpx solid rgba(255, 250, 240, 0.88);
  border-radius: 50%;
}

.guide-card--listen .guide-card__circle {
  background: #fff0bd;
}

.guide-card--ask .guide-card__circle {
  background: #f4c7a9;
}

.guide-card--focus .guide-card__circle {
  background: #dfeff8;
}

.guide-card__body {
  flex: 1;
  min-width: 0;
}

.guide-card__title {
  display: block;
  margin-bottom: 14rpx;
  font-size: 34rpx;
  font-weight: 900;
}

.guide-card__text {
  display: block;
  margin-bottom: 8rpx;
  font-size: 27rpx;
  line-height: 1.55;
  color: #4f3b28;
}

.guide-question-list {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
}

.guide-question-list__item {
  position: relative;
  display: block;
  padding-left: 24rpx;
  font-size: 27rpx;
  line-height: 1.45;
  color: #4f3b28;
}

.guide-question-list__item::before {
  position: absolute;
  top: 13rpx;
  left: 0;
  width: 10rpx;
  height: 10rpx;
  content: '';
  background: #f26a21;
  border-radius: 50%;
}

.guide-focus-list {
  display: flex;
  flex-wrap: wrap;
  gap: 16rpx;
}

.guide-focus-list__item {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 112rpx;
  height: 58rpx;
  padding: 0 24rpx;
  font-size: 27rpx;
  font-weight: 800;
  color: #5e3c22;
  background: #fff6dc;
  border: 2rpx solid rgba(190, 142, 78, 0.32);
  border-radius: 18rpx;
}

.guide-ai-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16rpx;
  padding-right: 92rpx;
  margin-top: 26rpx;
}

.guide-ai-card {
  min-width: 0;
  min-height: 116rpx;
  padding: 16rpx 10rpx;
  text-align: center;
  border: 3rpx solid rgba(190, 142, 78, 0.28);
  border-radius: 24rpx;
}

.guide-ai-card--blue {
  background: #dfeff8;
}

.guide-ai-card--green {
  background: #eef6dc;
}

.guide-ai-card--orange {
  background: #fff1d8;
}

.guide-ai-card__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 42rpx;
  height: 42rpx;
  margin: 0 auto 10rpx;
  font-size: 21rpx;
  font-weight: 900;
  color: #6b482d;
  background: rgba(255, 250, 240, 0.66);
  border-radius: 50%;
}

.guide-ai-card__text {
  display: block;
  font-size: 25rpx;
  line-height: 1.35;
  color: #4a2f1b;
}

@media (max-width: 360px) {
  .guide-page__paper {
    padding-right: 24rpx;
    padding-left: 24rpx;
  }

  .guide-hero__title {
    font-size: 44rpx;
  }

  .guide-polaroid-stack {
    right: 4rpx;
    transform: scale(0.9);
    transform-origin: right top;
  }
}

@media (min-width: 431px) {
  .guide-page__paper {
    padding: calc(18px + env(safe-area-inset-top)) 18px calc(144px + env(safe-area-inset-bottom));
  }

  .guide-header {
    margin-bottom: 16px;
  }

  .guide-header__title {
    font-size: 28px;
  }

  .guide-hero {
    min-height: 202px;
    padding: 30px 15px 18px;
    border-width: 2px;
    border-radius: 20px;
  }

  .guide-hero__title {
    font-size: 29px;
  }

  .guide-hero__desc {
    font-size: 16px;
  }

  .guide-card {
    min-height: 98px;
    padding: 14px;
    border-width: 2px;
    border-radius: 16px;
  }

  .guide-card__title {
    font-size: 20px;
  }

  .guide-card__text,
  .guide-question-list__item,
  .guide-focus-list__item {
    font-size: 15px;
  }
}
</style>
