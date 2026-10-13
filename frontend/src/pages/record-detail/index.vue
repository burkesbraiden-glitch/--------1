<template>
  <view class="record-detail-page">
    <view class="record-detail-page__content">
      <view class="record-detail-header">
        <button class="record-detail-header__back" aria-label="返回" @click="goBack">←</button>
        <text class="record-detail-header__title">{{ record ? recordRouteLabel(record) : '探索记录' }}</text>
      </view>

      <view v-if="routeError" class="record-detail-state record-detail-state--error">
        <text class="record-detail-state__title">这份记录暂时无法打开</text>
        <button class="record-detail-state__action" @click="goBack">返回</button>
      </view>
      <view v-else-if="isInitialLoading" class="record-detail-state">
        <view class="record-detail-state__spinner" aria-hidden="true"></view>
        <text class="record-detail-state__title">正在加载探索成果</text>
      </view>
      <view v-else-if="showFullError" class="record-detail-state record-detail-state--error">
        <text class="record-detail-state__title">记录暂时加载失败</text>
        <text class="record-detail-state__desc">{{ errorMessage }}</text>
        <button class="record-detail-state__action" @click="retryDetail">重新加载</button>
      </view>

      <template v-else-if="record">
        <view v-if="detailError" class="record-detail-refresh-error">
          <text>{{ errorMessage }}</text>
          <text @click="retryDetail">重新加载</text>
        </view>

        <view class="record-detail-hero">
          <image
            v-if="record.displayCoverImage"
            class="record-detail-hero__image"
            :src="record.displayCoverImage"
            mode="aspectFill"
            @click="previewCoverImage"
          />
          <view v-else class="record-detail-hero__placeholder" aria-hidden="true">
            <view class="record-detail-hero__placeholder-mark"></view>
            <text>探索记录</text>
          </view>
        </view>

        <view class="record-detail-summary-card">
          <text v-if="recordDateLabel" class="record-detail-summary-card__date">{{ recordDateLabel }}</text>
          <text class="record-detail-summary-card__title">{{ recordRouteLabel(record) }}</text>
          <text v-if="record.taskCount" class="record-detail-summary-card__progress">{{ taskProgressText(record) }}</text>
          <view v-if="record.taskCount" class="record-detail-summary-card__progress-track" aria-hidden="true">
            <view class="record-detail-summary-card__progress-value" :style="{ width: taskCompletionWidth(record) }"></view>
          </view>
          <view v-if="record.taskCount || record.photoCount || record.noteCount" class="record-detail-summary-card__stats">
            <view v-if="record.taskCount" class="record-detail-summary-card__stat">
              <text class="record-detail-summary-card__stat-icon" aria-hidden="true">✓</text>
              <text>{{ record.taskCount }} 个任务</text>
            </view>
            <view v-if="record.photoCount" class="record-detail-summary-card__stat">
              <text class="record-detail-summary-card__stat-icon" aria-hidden="true">▣</text>
              <text>{{ record.photoCount }} 张照片</text>
            </view>
            <view v-if="record.noteCount" class="record-detail-summary-card__stat">
              <text class="record-detail-summary-card__stat-icon" aria-hidden="true">✎</text>
              <text>{{ record.noteCount }} 条笔记</text>
            </view>
          </view>
          <text v-if="remainingTaskCount" class="record-detail-summary-card__remaining">还有 {{ remainingTaskCount }} 个任务未完成</text>
        </view>

        <view v-if="record.summary" class="record-summary">
          <text class="record-section-title">旅途小结</text>
          <text class="record-summary__text">{{ record.summary }}</text>
        </view>

        <view class="record-section-head">
          <text class="record-section-title">任务记录</text>
          <text v-if="record.entries.length" class="record-section-head__count">{{ record.entries.length }} 项成果</text>
        </view>

        <view v-if="record.entries.length" class="record-entry-list">
          <view v-for="entry in record.entries" :key="entry.submissionId || entry.taskId" class="record-entry">
            <view class="record-entry__head">
              <view class="record-entry__identity">
                <text class="record-entry__mark" :class="{ 'record-entry__mark--complete': entry.status === 'completed' }" aria-hidden="true">{{ entryStatusMark(entry.status) }}</text>
                <view class="record-entry__copy">
                  <text class="record-entry__title">{{ entry.title || '观察任务' }}</text>
                  <text v-if="entry.displayCompletedAt" class="record-entry__date">{{ entry.displayCompletedAt }}</text>
                </view>
              </view>
              <text class="record-entry__status" :class="{ 'record-entry__status--complete': entry.status === 'completed' }">{{ entryStatusText(entry.status) }}</text>
            </view>
            <text v-if="entry.subtitle" class="record-entry__subtitle">{{ entry.subtitle }}</text>

            <view v-if="entry.displayImage" class="record-entry__media">
              <image
                class="record-entry__photo"
                :src="entry.displayImage"
                mode="aspectFill"
                @click="previewEntryImage(entry)"
              />
            </view>
            <text v-else-if="entry.imageUrl" class="record-entry__photo-unavailable">照片暂时无法显示</text>

            <view v-if="entry.note" class="record-entry__note">
              <text class="record-entry__note-label">笔记</text>
              <text class="record-entry__note-text">{{ entry.note }}</text>
            </view>
          </view>
        </view>
        <view v-else class="record-empty-artifacts">
          <text>这次探索还没有可回顾的任务成果。</text>
        </view>
      </template>
    </view>
  </view>
</template>

<script>
import { useRecordStore } from '../../stores/record'
import { useUserStore } from '../../stores/user'
import { endUserSession } from '../../utils/sessionBoundary'

function isAuthenticationError(error) {
  return ['UNAUTHORIZED', 'TOKEN_EXPIRED', 'INVALID_TOKEN'].includes(error?.code) || error?.statusCode === 401
}

function normalizePlanId(value) {
  const planId = Number(value)
  return Number.isInteger(planId) && planId > 0 ? planId : null
}

function formatRecordDate(record) {
  const value = record?.finalizedAt || record?.updatedAt || record?.createdAt
  if (typeof value !== 'string' || !value.trim()) return ''
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`
}

export default {
  data() {
    return { routePlanId: null, routeError: false }
  },
  computed: {
    detailError() { return this.recordStore.detailError },
    errorMessage() { return this.detailError?.message || '请检查网络后再试一次' },
    isInitialLoading() { return this.recordStore.detailLoading && !this.record },
    record() { return this.recordStore.currentRecord },
    recordDateLabel() { return formatRecordDate(this.record) },
    remainingTaskCount() {
      const total = Number(this.record?.taskCount) || 0
      const completed = Math.min(Number(this.record?.completedTaskCount) || 0, total)
      return Math.max(total - completed, 0)
    },
    recordStore() { return useRecordStore() },
    showFullError() { return Boolean(this.detailError) && !this.record },
    userStore() { return useUserStore() },
  },
  onLoad(options) {
    this.routePlanId = normalizePlanId(options?.planId)
    this.routeError = !this.routePlanId
    if (!this.routeError) this.loadDetail()
  },
  onUnload() {
    this.recordStore.clearJourneyRecordDetail()
  },
  methods: {
    async handleAuthExpired() {
      await endUserSession()
    },
    async loadDetail() {
      if (!this.routePlanId) return
      if (!this.userStore.isAuthReady || this.userStore.isRestoring) await this.userStore.restoreSession()
      if (!this.userStore.isLoggedIn || !this.userStore.userInfo?.id) {
        this.recordStore.resetRecordState()
        uni.reLaunch({ url: '/pages/login/index' })
        return
      }
      try {
        await this.recordStore.loadJourneyRecordDetail(this.routePlanId)
      } catch (error) {
        if (isAuthenticationError(error)) await this.handleAuthExpired()
      }
    },
    entryStatusText(status) {
      if (status === 'completed') return '已完成'
      if (status === 'in-progress') return '进行中'
      return '未完成'
    },
    entryStatusMark(status) {
      return status === 'completed' ? '✓' : '○'
    },
    goBack() {
      uni.navigateBack({ delta: 1 })
    },
    previewCoverImage() {
      if (!this.record?.displayCoverImage) return
      this.previewImages(this.record.displayCoverImage)
    },
    previewEntryImage(entry) {
      if (!entry?.displayImage) return
      this.previewImages(entry.displayImage)
    },
    previewImages(current) {
      const urls = (this.record?.entries || []).map((entry) => entry.displayImage).filter(Boolean)
      if (this.record?.displayCoverImage && !urls.includes(this.record.displayCoverImage)) urls.unshift(this.record.displayCoverImage)
      if (urls.length) uni.previewImage({ current, urls })
    },
    async retryDetail() {
      try {
        await this.recordStore.retryJourneyRecordDetail()
      } catch (error) {
        if (isAuthenticationError(error)) await this.handleAuthExpired()
      }
    },
    recordRouteLabel(record) {
      const title = record?.displayTitle || '一次探索'
      return record?.destination ? `${title} · ${record.destination}` : title
    },
    taskCompletionWidth(record) {
      const total = Number(record?.taskCount) || 0
      const completed = Math.min(Number(record?.completedTaskCount) || 0, total)
      return total ? `${Math.round((completed / total) * 100)}%` : '0%'
    },
    taskProgressText(record) {
      const total = Number(record?.taskCount) || 0
      const completed = Math.min(Number(record?.completedTaskCount) || 0, total)
      return `${completed} / ${total} 个任务已完成`
    },
  },
}
</script>

<style scoped>
.record-detail-page { min-height: 100vh; overflow-x: hidden; color: var(--tl-text-main); background: var(--tl-bg); }
.record-detail-page__content { width: 100%; max-width: var(--tl-content-max-width); min-height: 100vh; padding: calc(18rpx + var(--tl-safe-top)) 0 calc(72rpx + var(--tl-safe-bottom)); margin: 0 auto; }
.record-detail-header { display: flex; gap: 18rpx; align-items: center; min-height: 88rpx; padding: 0 var(--tl-page-padding) 18rpx; background: var(--tl-bg); }
.record-detail-header__back { display: inline-flex; flex: 0 0 auto; align-items: center; justify-content: center; width: 56rpx; min-height: 64rpx; padding: 0; font-size: 45rpx; line-height: 1; color: var(--tl-text-main); }
.record-detail-header__title { flex: 1; min-width: 0; overflow: hidden; font-size: 29rpx; font-weight: var(--tl-weight-section-title); line-height: 1.35; text-align: center; text-overflow: ellipsis; white-space: nowrap; }
.record-detail-state { display: flex; flex-direction: column; align-items: center; padding: 120rpx var(--tl-space-lg); text-align: center; }
.record-detail-state--error { color: var(--tl-primary-deep); }
.record-detail-state__spinner { width: 48rpx; height: 48rpx; margin-bottom: var(--tl-space-md); border: 4rpx solid var(--tl-surface-muted); border-top-color: var(--tl-primary); border-radius: 50%; }
.record-detail-state__title, .record-section-title, .record-entry__title { display: block; font-weight: var(--tl-weight-section-title); }
.record-detail-state__title { font-size: var(--tl-type-section-title); }
.record-detail-state__desc { display: block; max-width: 440rpx; margin-top: var(--tl-space-sm); font-size: var(--tl-type-body); line-height: var(--tl-line-height-body); color: var(--tl-text-secondary); }
.record-detail-state__action { min-width: 184rpx; min-height: var(--tl-control-min-height); margin-top: var(--tl-space-lg); font-size: var(--tl-type-primary-action); color: var(--tl-paper); background: var(--tl-primary); border-radius: var(--tl-radius-control); }
.record-detail-refresh-error { display: flex; justify-content: space-between; gap: var(--tl-space-sm); padding: var(--tl-space-sm) var(--tl-page-padding); font-size: var(--tl-type-meta); color: var(--tl-primary-deep); border-bottom: 1rpx solid var(--tl-divider); }
.record-detail-refresh-error text:last-child { flex-shrink: 0; text-decoration: underline; }
.record-detail-hero { height: 340rpx; overflow: hidden; background: var(--tl-surface-muted); }
.record-detail-hero__image { display: block; width: 100%; height: 100%; }
.record-detail-hero__placeholder { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 14rpx; width: 100%; height: 100%; font-size: 24rpx; color: var(--tl-text-secondary); background: linear-gradient(145deg, #f3e8d1, #ebe0ca); }
.record-detail-hero__placeholder-mark { width: 72rpx; height: 54rpx; border: 4rpx solid rgba(138, 109, 84, 0.5); border-radius: 12rpx; }
.record-detail-summary-card { position: relative; z-index: 1; margin: -28rpx var(--tl-page-padding) 0; padding: 28rpx; background: var(--tl-surface); border: 1rpx solid rgba(190, 142, 78, 0.13); border-radius: var(--tl-radius-sheet); box-shadow: var(--tl-shadow-media); }
.record-detail-summary-card__date { display: block; font-size: var(--tl-type-meta); line-height: 1.4; color: var(--tl-text-secondary); }
.record-detail-summary-card__title { display: block; margin-top: 10rpx; font-size: 32rpx; font-weight: var(--tl-weight-section-title); line-height: 1.4; }
.record-detail-summary-card__progress { display: block; margin-top: 18rpx; font-size: 26rpx; font-weight: 500; color: var(--tl-green-deep); }
.record-detail-summary-card__progress-track { height: 12rpx; margin-top: 14rpx; overflow: hidden; background: #e8ecef; border-radius: 99rpx; }
.record-detail-summary-card__progress-value { height: 100%; min-width: 10rpx; background: #53b988; border-radius: inherit; transition: width 180ms ease; }
.record-detail-summary-card__stats { display: flex; flex-wrap: wrap; gap: 14rpx 28rpx; margin-top: 24rpx; padding-top: 22rpx; border-top: 1rpx solid var(--tl-divider); }
.record-detail-summary-card__stat { display: inline-flex; gap: 10rpx; align-items: center; font-size: 24rpx; line-height: 1.3; color: var(--tl-text-secondary); }
.record-detail-summary-card__stat-icon { display: inline-flex; align-items: center; justify-content: center; width: 28rpx; height: 28rpx; font-size: 20rpx; font-weight: 700; line-height: 1; color: #64748b; border: 2rpx solid currentColor; border-radius: 7rpx; }
.record-detail-summary-card__remaining { display: block; margin-top: 20rpx; font-size: 24rpx; color: var(--tl-text-secondary); }
.record-summary { padding: 48rpx var(--tl-page-padding) 0; }
.record-section-title { font-size: var(--tl-type-section-title); }
.record-summary__text { display: block; margin-top: var(--tl-space-sm); font-size: var(--tl-type-body); line-height: var(--tl-line-height-body); color: var(--tl-text-secondary); white-space: pre-wrap; }
.record-section-head { display: flex; align-items: baseline; justify-content: space-between; padding: 52rpx var(--tl-page-padding) 24rpx; }
.record-section-head__count { font-size: var(--tl-type-meta); color: var(--tl-text-secondary); }
.record-entry-list { display: flex; flex-direction: column; gap: 18rpx; padding: 0 var(--tl-page-padding); }
.record-entry { padding: 26rpx; background: var(--tl-surface); border: 1rpx solid rgba(190, 142, 78, 0.12); border-radius: var(--tl-radius-media); }
.record-entry__head { display: flex; align-items: flex-start; justify-content: space-between; gap: 18rpx; }
.record-entry__identity { display: flex; flex: 1; gap: 16rpx; align-items: flex-start; min-width: 0; }
.record-entry__mark { display: inline-flex; flex: 0 0 auto; align-items: center; justify-content: center; width: 44rpx; height: 44rpx; font-size: 29rpx; line-height: 1; color: #9ca3af; border: 2rpx solid currentColor; border-radius: 50%; }
.record-entry__mark--complete { color: #fff; background: #2ba56d; border-color: #2ba56d; }
.record-entry__copy { flex: 1; min-width: 0; }
.record-entry__title { overflow: hidden; font-size: 29rpx; line-height: 1.45; text-overflow: ellipsis; white-space: nowrap; }
.record-entry__date, .record-entry__subtitle, .record-entry__photo-unavailable { display: block; font-size: var(--tl-type-meta); color: var(--tl-text-secondary); }
.record-entry__date { margin-top: 6rpx; }
.record-entry__status { flex: 0 0 auto; padding: 7rpx 14rpx; font-size: 22rpx; line-height: 1.25; color: #8b95a1; background: #eef1f3; border-radius: 999rpx; }
.record-entry__status--complete { color: var(--tl-green-deep); background: var(--tl-green); }
.record-entry__subtitle { margin-top: 18rpx; line-height: 1.5; }
.record-entry__media { width: 260rpx; height: 214rpx; margin-top: 22rpx; overflow: hidden; border-radius: var(--tl-radius-small); }
.record-entry__photo { display: block; width: 100%; height: 100%; }
.record-entry__photo-unavailable { padding-top: 22rpx; }
.record-entry__note { margin-top: 22rpx; padding-top: 20rpx; border-top: 1rpx solid var(--tl-divider); }
.record-entry__note-label { display: block; font-size: 24rpx; font-weight: 500; color: var(--tl-text-secondary); }
.record-entry__note-text { display: block; margin-top: 10rpx; font-size: 27rpx; line-height: var(--tl-line-height-body); color: var(--tl-text-main); white-space: pre-wrap; }
.record-empty-artifacts { padding: 16rpx var(--tl-page-padding); font-size: var(--tl-type-body); line-height: var(--tl-line-height-body); color: var(--tl-text-secondary); }
@media (min-width: 431px) { .record-detail-page__content { padding-top: 9px; } .record-detail-header { padding-right: 18px; padding-left: 18px; } .record-detail-hero { height: 220px; } .record-detail-summary-card { margin-right: 18px; margin-left: 18px; padding: 16px; } .record-summary, .record-section-head { padding-right: 18px; padding-left: 18px; } .record-entry-list { padding-right: 18px; padding-left: 18px; } .record-entry { padding: 16px; } .record-entry__media { width: 130px; height: 107px; } }
@media (max-width: 350px) { .record-detail-header { padding-right: 24rpx; padding-left: 24rpx; } .record-detail-summary-card { margin-right: 24rpx; margin-left: 24rpx; } .record-summary, .record-section-head, .record-entry-list { padding-right: 24rpx; padding-left: 24rpx; } .record-detail-summary-card__stats { gap: 12rpx 18rpx; } .record-detail-summary-card__stat { font-size: 22rpx; } }
</style>
