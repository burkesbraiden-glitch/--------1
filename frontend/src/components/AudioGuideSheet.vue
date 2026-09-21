<template>
  <view v-if="open" class="audio-guide-sheet" role="dialog" aria-modal="true" aria-label="景点讲解">
    <view class="audio-guide-sheet__mask" @click="closeSheet"></view>

    <view class="audio-guide-sheet__panel">
      <view class="audio-guide-sheet__handle" aria-hidden="true"></view>
      <view class="audio-guide-sheet__header">
        <view class="audio-guide-sheet__header-copy">
          <text class="audio-guide-sheet__eyebrow">语音讲解</text>
          <text class="audio-guide-sheet__header-note">和孩子一起慢慢发现</text>
        </view>
        <button class="audio-guide-sheet__close" aria-label="关闭讲解" @click="closeSheet">×</button>
      </view>

      <scroll-view class="audio-guide-sheet__scroll" scroll-y>
        <view v-if="sheetState === 'no-plan'" class="audio-guide-sheet__state audio-guide-sheet__state--empty">
          <text class="audio-guide-sheet__state-sticker">✦</text>
          <text class="audio-guide-sheet__state-title">暂无可查看的景点讲解</text>
          <text class="audio-guide-sheet__state-copy">先选择或开始一个探索计划，就可以查看对应讲解。</text>
          <button class="audio-guide-sheet__state-action" @click="goExplore">去探索</button>
        </view>

        <view v-else-if="sheetState === 'loading' || sheetState === 'generating'" class="audio-guide-sheet__state">
          <text class="audio-guide-sheet__state-sticker">✦</text>
          <text class="audio-guide-sheet__state-title">{{ sheetState === 'generating' ? '正在准备讲解…' : '正在打开讲解…' }}</text>
          <text class="audio-guide-sheet__state-copy">请稍等一下，旅行故事马上就来。</text>
        </view>

          <view v-else-if="sheetState === 'guide-unavailable'" class="audio-guide-sheet__state audio-guide-sheet__state--empty">
            <text class="audio-guide-sheet__state-sticker">✦</text>
            <text class="audio-guide-sheet__state-title">暂无可查看的讲解内容</text>
            <text class="audio-guide-sheet__state-copy">先去创建探索计划，就可以听到专属讲解。</text>
          </view>

          <view v-else-if="sheetState === 'guide-error'" class="audio-guide-sheet__state audio-guide-sheet__state--error">
          <text class="audio-guide-sheet__state-sticker">!</text>
          <text class="audio-guide-sheet__state-title">讲解暂时打不开</text>
          <text class="audio-guide-sheet__state-copy">{{ errorMessage }}</text>
          <button class="audio-guide-sheet__state-action audio-guide-sheet__state-action--secondary" @click="retryGuide">重试</button>
        </view>

        <view v-else-if="displayGuide" class="audio-guide-sheet__content">
          <view class="audio-guide-sheet__cover" :class="{ 'audio-guide-sheet__cover--blank': !coverImage }">
            <image v-if="coverImage" class="audio-guide-sheet__cover-image" :src="coverImage" mode="aspectFill" />
            <view v-else class="audio-guide-sheet__cover-watercolor" aria-hidden="true">
              <view class="audio-guide-sheet__cover-sun"></view>
              <view class="audio-guide-sheet__cover-hill audio-guide-sheet__cover-hill--back"></view>
              <view class="audio-guide-sheet__cover-hill audio-guide-sheet__cover-hill--front"></view>
            </view>
            <view class="audio-guide-sheet__cover-tape" aria-hidden="true"></view>
          </view>

          <view class="audio-guide-sheet__intro">
            <text class="audio-guide-sheet__label">语音讲解</text>
            <text class="audio-guide-sheet__destination">{{ displayGuide.destination || currentPlan?.destination || '景点讲解' }}</text>
          </view>

          <view v-if="canPlayAudio" class="audio-guide-sheet__audio-state">
            <view class="audio-guide-sheet__audio-heading">
              <view>
                <text class="audio-guide-sheet__audio-title">语音内容已准备</text>
                <text v-if="displayGuide.audioDurationSec" class="audio-guide-sheet__audio-copy">约 {{ formatAudioTime(displayGuide.audioDurationSec) }}</text>
              </view>
              <button class="audio-guide-sheet__play" :disabled="isRefreshingAudioUrl" @click="playAudio">
                {{ isRefreshingAudioUrl ? '正在更新…' : isPlaying ? '暂停' : audioContext ? '继续播放' : '播放讲解' }}
              </button>
            </view>
            <view class="audio-guide-sheet__progress-track" aria-hidden="true">
              <view class="audio-guide-sheet__progress-value" :style="{ width: `${audioProgressPercent}%` }"></view>
            </view>
            <text class="audio-guide-sheet__audio-time">
              {{ formatAudioTime(currentTime) }} / {{ duration > 0 ? formatAudioTime(duration) : '--:--' }}
            </text>
            <text v-if="audioError" class="audio-guide-sheet__audio-notice">{{ audioError }}</text>
          </view>
          <view v-else class="audio-guide-sheet__audio-state audio-guide-sheet__audio-state--no-audio">
            <text class="audio-guide-sheet__audio-title">{{ audioUnavailableTitle }}</text>
            <text class="audio-guide-sheet__audio-copy">{{ audioUnavailableCopy }}</text>
          </view>

          <view class="audio-guide-sheet__tabs" role="tablist">
            <button
              class="audio-guide-sheet__tab"
              :class="{ 'audio-guide-sheet__tab--active': activeTab === 'content' }"
              @click="activeTab = 'content'"
            >讲解内容</button>
            <button
              class="audio-guide-sheet__tab"
              :class="{ 'audio-guide-sheet__tab--active': activeTab === 'images' }"
              @click="activeTab = 'images'"
            >相关图片</button>
          </view>

          <view v-if="activeTab === 'content'" class="audio-guide-sheet__transcript">
            <view class="audio-guide-sheet__section">
              <text class="audio-guide-sheet__section-title">一起看看</text>
              <text v-for="(paragraph, index) in displayGuide.childIntro" :key="`intro-${index}`" class="audio-guide-sheet__paragraph">
                {{ paragraph }}
              </text>
              <text v-if="!displayGuide.childIntro.length" class="audio-guide-sheet__paragraph audio-guide-sheet__paragraph--muted">这份讲解正在整理中。</text>
            </view>

            <view v-if="displayGuide.questions.length" class="audio-guide-sheet__section audio-guide-sheet__section--questions">
              <text class="audio-guide-sheet__section-title">可以问孩子</text>
              <text v-for="(question, index) in displayGuide.questions" :key="`question-${index}`" class="audio-guide-sheet__list-item">
                {{ index + 1 }}. {{ question }}
              </text>
            </view>

            <view v-if="displayGuide.focusItems.length" class="audio-guide-sheet__section audio-guide-sheet__section--focus">
              <text class="audio-guide-sheet__section-title">重点观察</text>
              <text v-for="(item, index) in displayGuide.focusItems" :key="`focus-${index}`" class="audio-guide-sheet__list-item">
                {{ item }}
              </text>
            </view>
          </view>

          <view v-if="activeTab === 'images' && coverImage" class="audio-guide-sheet__related-images">
            <image class="audio-guide-sheet__related-image" :src="coverImage" mode="aspectFill" />
            <text class="audio-guide-sheet__related-caption">来自本次探索计划的景点图片</text>
          </view>
          <view v-if="activeTab === 'images' && !coverImage" class="audio-guide-sheet__related-images-empty">
            <text class="audio-guide-sheet__related-empty-icon">✦</text>
            <text class="audio-guide-sheet__related-empty-title">暂无相关图片</text>
            <text class="audio-guide-sheet__related-empty-copy">这次探索还没有可展示的景点图片。</text>
          </view>
        </view>

        <view v-else class="audio-guide-sheet__state audio-guide-sheet__state--empty">
          <text class="audio-guide-sheet__state-sticker">✦</text>
          <text class="audio-guide-sheet__state-title">暂无可查看的讲解内容</text>
          <text class="audio-guide-sheet__state-copy">稍后再试试吧。</text>
        </view>
      </scroll-view>
    </view>
  </view>
</template>

<script>
import { shallowRef } from 'vue'
import { useGuideStore } from '../stores/guide'
import { usePlanStore } from '../stores/plan'

function samePlanId(left, right) {
  return String(left) === String(right)
}

export default {
  name: 'AudioGuideSheet',
  props: {
    open: {
      type: Boolean,
      default: false,
    },
    planId: {
      type: [String, Number],
      default: null,
    },
  },
  emits: ['update:open'],
  data() {
    return {
      activeTab: 'content',
      displayGuide: null,
      error: null,
      audioContext: shallowRef(null),
      audioEventHandlers: null,
      isPlaying: false,
      currentTime: 0,
      duration: 0,
      audioSessionSequence: 0,
      audioError: '',
      isRefreshingAudioUrl: false,
      audioUrlRefreshAttempted: false,
      requestSequence: 0,
      requestedPlanId: null,
      sheetState: 'closed',
    }
  },
  computed: {
    guideStore() {
      return useGuideStore()
    },
    planStore() {
      return usePlanStore()
    },
    currentPlan() {
      if (this.planId === null || this.planId === undefined || String(this.planId).trim() === '') {
        return null
      }
      return this.planStore.plans.find((plan) => samePlanId(plan.id, this.planId))
        || (samePlanId(this.planStore.currentPlan?.id, this.planId) ? this.planStore.currentPlan : null)
    },
    coverImage() {
      return this.currentPlan?.sourceSnapshot?.attraction?.coverImage || ''
    },
    errorMessage() {
      return this.error?.message || '请检查网络后再试一次。'
    },
    canPlayAudio() {
      return this.displayGuide?.audioStatus === 'ready'
        && typeof this.displayGuide?.audioUrl === 'string'
        && this.displayGuide.audioUrl.trim() !== ''
    },
    audioProgressPercent() {
      if (!Number.isFinite(this.duration) || this.duration <= 0) {
        return 0
      }
      const currentTime = Number.isFinite(this.currentTime) ? this.currentTime : 0
      return Math.min(100, Math.max(0, (currentTime / this.duration) * 100))
    },
    audioUnavailableTitle() {
      if (this.displayGuide?.audioStatus === 'pending') {
        return '语音讲解正在准备'
      }
      if (this.displayGuide?.audioStatus === 'failed') {
        return '语音讲解暂时不可用'
      }
      return '语音讲解暂未准备好'
    },
    audioUnavailableCopy() {
      if (this.displayGuide?.audioStatus === 'pending') {
        return '先看看下面的文字讲解吧。'
      }
      if (this.displayGuide?.audioStatus === 'failed') {
        return '先看看下面的文字讲解吧，稍后再试。'
      }
      return '先看看下面的文字讲解吧。'
    },
  },
  watch: {
    open(value) {
      if (value) {
        this.openForPlan()
        return
      }
      this.resetAfterClose()
    },
    planId() {
      if (this.open) {
        this.openForPlan()
      }
    },
  },
  beforeUnmount() {
    this.disposeAudioContext()
    this.invalidateRequest()
  },
  methods: {
    invalidateRequest() {
      this.requestSequence += 1
      this.requestedPlanId = null
    },
    resetAfterClose() {
      this.disposeAudioContext()
      this.invalidateRequest()
      this.displayGuide = null
      this.error = null
      this.audioError = ''
      this.isRefreshingAudioUrl = false
      this.audioUrlRefreshAttempted = false
      this.activeTab = 'content'
      this.sheetState = 'closed'
    },
    closeSheet() {
      this.disposeAudioContext()
      this.invalidateRequest()
      this.displayGuide = null
      this.error = null
      this.audioError = ''
      this.isRefreshingAudioUrl = false
      this.audioUrlRefreshAttempted = false
      this.activeTab = 'content'
      this.sheetState = 'closed'
      this.$emit('update:open', false)
    },
    canApplyRequest(requestToken, requestedPlanId) {
      if (!this.open || requestToken !== this.requestSequence) {
        return false
      }
      return samePlanId(requestedPlanId, this.requestedPlanId)
        && samePlanId(requestedPlanId, this.planId)
    },
    canApplyGuide(requestToken, requestedPlanId, guide) {
      const returnedPlanId = guide ? guide.planId : null
      return this.canApplyRequest(requestToken, requestedPlanId)
        && samePlanId(returnedPlanId, this.planId)
    },
    async openForPlan() {
      this.disposeAudioContext()
      const requestedPlanId = this.planId
      this.requestSequence += 1
      const requestToken = this.requestSequence
      this.requestedPlanId = requestedPlanId
      this.displayGuide = null
      this.error = null
      this.audioError = ''
      this.isRefreshingAudioUrl = false
      this.audioUrlRefreshAttempted = false
      this.activeTab = 'content'

      if (requestedPlanId === null || requestedPlanId === undefined || String(requestedPlanId).trim() === '') {
        this.sheetState = 'no-plan'
        return
      }

      this.sheetState = 'loading'
      const guidePromise = this.guideStore.fetchGuide(requestedPlanId)

      try {
        const guide = await guidePromise
        if (!this.canApplyGuide(requestToken, requestedPlanId, guide)) {
          return
        }
        this.displayGuide = guide
        this.sheetState = this.canPlayAudio ? 'ready' : 'no-audio'
      } catch (error) {
        if (!this.canApplyRequest(requestToken, requestedPlanId)) {
          return
        }
        if (error?.code === 'GUIDE_NOT_FOUND') {
          this.sheetState = 'guide-unavailable'
          return
        }
        this.error = error
        this.sheetState = 'guide-error'
      }
    },
    playAudio() {
      if (!this.canPlayAudio || this.isRefreshingAudioUrl) {
        return
      }
      if (this.audioContext) {
        if (this.isPlaying) {
          this.audioContext.pause()
          return
        }
        this.audioContext.play()
        return
      }

      this.audioError = ''
      this.audioSessionSequence += 1
      const sessionToken = this.audioSessionSequence
      const planId = this.planId
      const context = uni.createInnerAudioContext()
      this.audioContext = context
      context.autoplay = false
      const handlers = {
        onPlay: () => {
          if (this.isCurrentAudioSession(sessionToken, planId, context)) {
            this.isPlaying = true
          }
        },
        onPause: () => {
          if (this.isCurrentAudioSession(sessionToken, planId, context)) {
            this.isPlaying = false
          }
        },
        onCanplay: () => {
          if (!this.isCurrentAudioSession(sessionToken, planId, context)) {
            return
          }
          const duration = context.duration
          if (Number.isFinite(duration) && duration > 0) {
            this.duration = duration
          }
        },
        onTimeUpdate: () => {
          if (!this.isCurrentAudioSession(sessionToken, planId, context)) {
            return
          }
          const currentTime = context.currentTime
          if (Number.isFinite(currentTime) && currentTime >= 0) {
            this.currentTime = currentTime
          }
        },
        onEnded: () => {
          if (!this.isCurrentAudioSession(sessionToken, planId, context)) {
            return
          }
          this.disposeAudioContext()
        },
        onError: () => {
          if (!this.isCurrentAudioSession(sessionToken, planId, context)) {
            return null
          }
          return this.handleAudioError(planId)
        },
      }
      this.audioEventHandlers = handlers
      context.onPlay(handlers.onPlay)
      context.onPause(handlers.onPause)
      context.onCanplay(handlers.onCanplay)
      context.onTimeUpdate(handlers.onTimeUpdate)
      context.onEnded(handlers.onEnded)
      context.onError(handlers.onError)
      context.src = this.displayGuide.audioUrl
      context.play()
    },
    isCurrentAudioSession(sessionToken, planId, context) {
      return this.open
        && sessionToken === this.audioSessionSequence
        && context === this.audioContext
        && samePlanId(planId, this.planId)
        && samePlanId(planId, this.displayGuide?.planId)
    },
    disposeAudioContext() {
      this.audioSessionSequence += 1
      const context = this.audioContext
      const handlers = this.audioEventHandlers
      this.audioContext = null
      this.audioEventHandlers = null
      this.isPlaying = false
      this.currentTime = 0
      this.duration = 0

      if (!context) {
        return
      }

      try {
        context.stop()
      } catch (_error) {
        // Cleanup must continue even when a platform context has already stopped.
      }
      for (const [offMethod, handlerName] of [
        ['offPlay', 'onPlay'],
        ['offPause', 'onPause'],
        ['offCanplay', 'onCanplay'],
        ['offTimeUpdate', 'onTimeUpdate'],
        ['offEnded', 'onEnded'],
        ['offError', 'onError'],
      ]) {
        try {
          if (typeof context[offMethod] === 'function') {
            context[offMethod](handlers?.[handlerName])
          }
        } catch (_error) {
          // Continue the remaining cleanup calls for cross-platform safety.
        }
      }
      try {
        context.destroy()
      } catch (_error) {
        // A second disposal is intentionally harmless.
      }
    },
    markAudioUnavailable() {
      if (!this.displayGuide || !samePlanId(this.displayGuide.planId, this.planId)) {
        return
      }
      this.displayGuide = {
        ...this.displayGuide,
        audioStatus: 'failed',
        audioUrl: null,
        audioDurationSec: null,
      }
      this.sheetState = 'no-audio'
    },
    async handleAudioError(planId) {
      this.isPlaying = false
      if (this.audioUrlRefreshAttempted || !this.canPlayAudio) {
        this.disposeAudioContext()
        this.markAudioUnavailable()
        return
      }

      this.audioUrlRefreshAttempted = true
      this.isRefreshingAudioUrl = true
      this.audioError = '正在更新音频地址…'
      this.disposeAudioContext()

      this.requestSequence += 1
      const requestToken = this.requestSequence
      this.requestedPlanId = planId
      try {
        const refreshedGuide = await this.guideStore.fetchGuide(planId)
        if (!this.canApplyGuide(requestToken, planId, refreshedGuide)) {
          return
        }
        const hasFreshAudio = refreshedGuide?.audioStatus === 'ready'
          && typeof refreshedGuide?.audioUrl === 'string'
          && refreshedGuide.audioUrl.trim() !== ''
        if (!hasFreshAudio) {
          this.markAudioUnavailable()
          return
        }
        this.displayGuide = refreshedGuide
        this.sheetState = 'ready'
        this.audioError = '音频地址已刷新，请重新播放'
      } catch (_error) {
        if (!this.canApplyRequest(requestToken, planId)) {
          return
        }
        this.markAudioUnavailable()
      } finally {
        if (this.canApplyRequest(requestToken, planId)) {
          this.isRefreshingAudioUrl = false
        }
      }
    },
    formatAudioTime(value) {
      if (!Number.isFinite(value) || value < 0) {
        return '--:--'
      }
      const seconds = Math.floor(value)
      const minutes = Math.floor(seconds / 60)
      return `${String(minutes).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`
    },
    retryGuide() {
      this.openForPlan()
    },
    goExplore() {
      this.closeSheet()
      uni.reLaunch({ url: '/pages/plan/index' })
    },
  },
}
</script>

<style scoped>
.audio-guide-sheet {
  position: fixed;
  z-index: 80;
  inset: 0;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  color: #4a2f1b;
}

.audio-guide-sheet__mask {
  position: absolute;
  inset: 0;
  background: rgba(54, 35, 18, 0.42);
}

.audio-guide-sheet__panel {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  width: min(100%, 430px);
  height: 78dvh;
  max-height: 82dvh;
  overflow: hidden;
  background:
    radial-gradient(circle at 92% 12%, rgba(179, 210, 197, 0.4) 0 54rpx, transparent 55rpx),
    radial-gradient(circle at 8% 28%, rgba(245, 190, 95, 0.19) 0 34rpx, transparent 35rpx),
    #fff8e9;
  border: 2rpx solid rgba(200, 149, 71, 0.58);
  border-bottom: 0;
  border-radius: 42rpx 42rpx 0 0;
  box-shadow: 0 -18rpx 42rpx rgba(53, 31, 15, 0.2);
}

.audio-guide-sheet__handle {
  flex: 0 0 auto;
  width: 78rpx;
  height: 9rpx;
  margin: 16rpx auto 8rpx;
  background: rgba(104, 76, 45, 0.42);
  border-radius: 999rpx;
}

.audio-guide-sheet__header {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: space-between;
  min-height: 88rpx;
  padding: 0 28rpx 14rpx;
}

.audio-guide-sheet__header-copy {
  display: flex;
  flex-direction: column;
  gap: 3rpx;
}

.audio-guide-sheet__eyebrow,
.audio-guide-sheet__label {
  font-size: 24rpx;
  font-weight: 900;
  color: #d96a21;
  letter-spacing: 2rpx;
}

.audio-guide-sheet__header-note {
  font-size: 22rpx;
  color: #8a6d54;
}

.audio-guide-sheet__close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 68rpx;
  height: 68rpx;
  padding: 0;
  font-size: 48rpx;
  line-height: 1;
  color: #4a2f1b;
  background: rgba(255, 252, 244, 0.76);
  border: 2rpx solid rgba(183, 132, 63, 0.38);
  border-radius: 50%;
}

.audio-guide-sheet__scroll {
  flex: 1;
  min-height: 0;
  padding: 0 28rpx calc(34rpx + env(safe-area-inset-bottom));
  box-sizing: border-box;
}

.audio-guide-sheet__state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 520rpx;
  padding: 40rpx 30rpx;
  text-align: center;
}

.audio-guide-sheet__state-sticker {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 84rpx;
  height: 84rpx;
  margin-bottom: 22rpx;
  font-size: 50rpx;
  color: #d96a21;
  background: #fff0cf;
  border: 3rpx solid rgba(214, 155, 67, 0.45);
  border-radius: 50%;
  transform: rotate(-8deg);
}

.audio-guide-sheet__state--error .audio-guide-sheet__state-sticker {
  color: #b6543c;
  background: #ffe6dc;
}

.audio-guide-sheet__state-title,
.audio-guide-sheet__related-empty-title {
  display: block;
  margin-bottom: 14rpx;
  font-size: 34rpx;
  font-weight: 900;
  line-height: 1.35;
}

.audio-guide-sheet__state-copy,
.audio-guide-sheet__related-empty-copy {
  display: block;
  font-size: 26rpx;
  line-height: 1.6;
  color: #785b42;
}

.audio-guide-sheet__state-action {
  min-width: 184rpx;
  min-height: 78rpx;
  padding: 0 32rpx;
  margin-top: 32rpx;
  font-size: 28rpx;
  font-weight: 900;
  line-height: 78rpx;
  color: #fffdf7;
  background: linear-gradient(180deg, #ff8c2a, #e96019);
  border-radius: 24rpx;
  box-shadow: 0 9rpx 0 rgba(174, 74, 22, 0.18);
}

.audio-guide-sheet__state-action--secondary {
  color: #a45520;
  background: #fff4dd;
  border: 2rpx solid rgba(211, 132, 50, 0.54);
  box-shadow: none;
}

.audio-guide-sheet__content {
  padding-bottom: 16rpx;
}

.audio-guide-sheet__cover {
  position: relative;
  height: 250rpx;
  margin-bottom: 26rpx;
  overflow: hidden;
  background: #dcecf1;
  border: 3rpx solid rgba(191, 139, 66, 0.46);
  border-radius: 28rpx;
  box-shadow: 0 10rpx 0 rgba(181, 120, 45, 0.08);
}

.audio-guide-sheet__cover-image,
.audio-guide-sheet__related-image {
  width: 100%;
  height: 100%;
}

.audio-guide-sheet__cover-watercolor {
  position: absolute;
  inset: 0;
  overflow: hidden;
  background: linear-gradient(180deg, #cfe9ef, #f8edd0);
}

.audio-guide-sheet__cover-sun {
  position: absolute;
  top: 34rpx;
  right: 60rpx;
  width: 54rpx;
  height: 54rpx;
  background: rgba(247, 184, 74, 0.75);
  border-radius: 50%;
}

.audio-guide-sheet__cover-hill {
  position: absolute;
  bottom: -68rpx;
  border-radius: 50% 50% 0 0;
  transform: rotate(-4deg);
}

.audio-guide-sheet__cover-hill--back {
  left: -42rpx;
  width: 460rpx;
  height: 180rpx;
  background: rgba(126, 166, 118, 0.48);
}

.audio-guide-sheet__cover-hill--front {
  right: -74rpx;
  width: 410rpx;
  height: 144rpx;
  background: rgba(88, 133, 85, 0.62);
}

.audio-guide-sheet__cover-tape {
  position: absolute;
  top: -6rpx;
  left: 50%;
  width: 138rpx;
  height: 28rpx;
  background: rgba(255, 231, 154, 0.7);
  transform: translateX(-50%) rotate(-2deg);
}

.audio-guide-sheet__intro {
  display: flex;
  flex-direction: column;
  gap: 9rpx;
  margin-bottom: 20rpx;
}

.audio-guide-sheet__destination {
  display: block;
  font-size: 42rpx;
  font-weight: 900;
  line-height: 1.25;
}

.audio-guide-sheet__audio-state {
  padding: 22rpx 24rpx;
  margin-bottom: 24rpx;
  background: #eff5df;
  border: 2rpx dashed rgba(104, 139, 70, 0.45);
  border-radius: 22rpx;
}

.audio-guide-sheet__audio-state--no-audio {
  background: #fff1d8;
  border-color: rgba(214, 125, 43, 0.48);
}

.audio-guide-sheet__audio-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18rpx;
}

.audio-guide-sheet__audio-title {
  display: block;
  margin-bottom: 6rpx;
  font-size: 29rpx;
  font-weight: 900;
}

.audio-guide-sheet__audio-copy {
  display: block;
  font-size: 24rpx;
  color: #7b5a3c;
}

.audio-guide-sheet__play {
  flex: 0 0 auto;
  min-width: 148rpx;
  height: 66rpx;
  padding: 0 22rpx;
  font-size: 25rpx;
  font-weight: 900;
  line-height: 66rpx;
  color: #fffdf7;
  background: linear-gradient(180deg, #ff8c2a, #e96019);
  border-radius: 999rpx;
  box-shadow: 0 6rpx 0 rgba(174, 74, 22, 0.16);
}

.audio-guide-sheet__play[disabled] {
  opacity: 0.72;
}

.audio-guide-sheet__progress-track {
  height: 8rpx;
  margin-top: 18rpx;
  overflow: hidden;
  background: rgba(130, 99, 65, 0.16);
  border-radius: 999rpx;
}

.audio-guide-sheet__progress-value {
  width: 0;
  height: 100%;
  background: #ed6d20;
  border-radius: inherit;
  transition: width 120ms linear;
}

.audio-guide-sheet__audio-time {
  display: block;
  margin-top: 10rpx;
  font-size: 22rpx;
  color: #8a6d54;
  text-align: right;
}

.audio-guide-sheet__audio-notice {
  display: block;
  margin-top: 10rpx;
  font-size: 22rpx;
  line-height: 1.45;
  color: #a45520;
}

.audio-guide-sheet__tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12rpx;
  margin-bottom: 22rpx;
  padding-bottom: 10rpx;
  border-bottom: 2rpx solid rgba(213, 168, 102, 0.32);
}

.audio-guide-sheet__tab {
  height: 66rpx;
  padding: 0;
  font-size: 27rpx;
  font-weight: 900;
  line-height: 66rpx;
  color: #765437;
  background: transparent;
  border-radius: 18rpx;
}

.audio-guide-sheet__tab--active {
  color: #c85e1d;
  background: #fff0d4;
}

.audio-guide-sheet__section {
  padding: 24rpx;
  margin-bottom: 20rpx;
  background: rgba(255, 253, 247, 0.75);
  border: 2rpx solid rgba(216, 176, 113, 0.34);
  border-radius: 22rpx;
}

.audio-guide-sheet__section--questions {
  background: #fff2dc;
}

.audio-guide-sheet__section--focus {
  background: #edf5df;
}

.audio-guide-sheet__section-title {
  display: block;
  margin-bottom: 12rpx;
  font-size: 30rpx;
  font-weight: 900;
}

.audio-guide-sheet__paragraph,
.audio-guide-sheet__list-item {
  display: block;
  margin-top: 10rpx;
  font-size: 27rpx;
  line-height: 1.65;
  color: #5f4129;
}

.audio-guide-sheet__paragraph--muted {
  color: #8a6d54;
}

.audio-guide-sheet__related-images,
.audio-guide-sheet__related-images-empty {
  min-height: 390rpx;
  overflow: hidden;
  background: #fffaf0;
  border: 2rpx dashed rgba(203, 148, 67, 0.54);
  border-radius: 24rpx;
}

.audio-guide-sheet__related-image {
  display: block;
  height: 330rpx;
}

.audio-guide-sheet__related-caption {
  display: block;
  padding: 18rpx 22rpx;
  font-size: 24rpx;
  color: #805f40;
}

.audio-guide-sheet__related-images-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 34rpx;
  text-align: center;
}

.audio-guide-sheet__related-empty-icon {
  margin-bottom: 16rpx;
  font-size: 56rpx;
  color: #d96a21;
}

@media (max-width: 360px) {
  .audio-guide-sheet__panel {
    height: 74dvh;
  }

  .audio-guide-sheet__scroll {
    padding-right: 20rpx;
    padding-left: 20rpx;
  }

  .audio-guide-sheet__destination {
    font-size: 38rpx;
  }

  .audio-guide-sheet__cover {
    height: 208rpx;
  }
}

@media (min-width: 431px) {
  .audio-guide-sheet__panel {
    border-width: 2px;
    border-radius: 24px 24px 0 0;
  }

  .audio-guide-sheet__scroll {
    padding-right: 18px;
    padding-left: 18px;
  }

  .audio-guide-sheet__destination {
    font-size: 26px;
  }

  .audio-guide-sheet__cover {
    height: 160px;
  }
}
</style>
