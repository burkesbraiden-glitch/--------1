<template>
  <view class="record-page">
    <view class="record-page__content">
      <view class="record-header">
        <text class="record-header__title">探索记录</text>
        <text class="record-header__subtitle">记录孩子的每一次探索与成长</text>
      </view>

      <view v-if="isChildLoading" class="record-state">
        <view class="record-state__spinner" aria-hidden="true"></view>
        <text class="record-state__title">正在加载孩子资料</text>
      </view>
      <view v-else-if="showChildError" class="record-state record-state--error">
        <text class="record-state__title">孩子资料加载失败</text>
        <text class="record-state__desc">{{ childErrorMessage }}</text>
        <button class="record-state__action" @click="retryRecords">重新加载</button>
      </view>
      <view v-else-if="showNoChild" class="record-state">
        <text class="record-state__title">还没有选择孩子</text>
        <text class="record-state__desc">请前往“我的”添加或选择孩子档案。</text>
      </view>
      <view v-else-if="isInitialLoading" class="record-state">
        <view class="record-state__spinner" aria-hidden="true"></view>
        <text class="record-state__title">正在加载探索记录</text>
      </view>
      <view v-else-if="showFullError" class="record-state record-state--error">
        <text class="record-state__title">记录暂时加载失败</text>
        <text class="record-state__desc">{{ errorMessage }}</text>
        <button class="record-state__action" @click="retryRecords">重新加载</button>
      </view>
      <view v-else-if="isEmpty" class="record-state record-state--empty">
        <view class="record-state__album-mark" aria-hidden="true"></view>
        <text class="record-state__title">还没有留下探索记录</text>
        <text class="record-state__desc">完成一次探索后，这里会保存孩子的任务、照片和发现。</text>
        <button class="record-state__action" @click="goExplore">去探索</button>
      </view>

      <template v-else>
        <view v-if="error" class="record-refresh-error">
          <text>{{ errorMessage }}</text>
          <text class="record-refresh-error__retry" @click="retryRecords">重新加载</text>
        </view>

        <view v-for="yearGroup in recordsByYear" :key="yearGroup.recordYear" class="record-year-group">
          <text class="record-year-group__title">{{ yearGroup.recordYear }}年</text>
          <view class="record-list">
            <view
              v-for="record in yearGroup.records"
              :key="record.id"
              class="record-card"
              hover-class="record-card--pressed"
              @click="openRecordDetail(record)"
            >
              <view class="record-card__media">
                <image
                  v-if="record.displayCoverImage"
                  class="record-card__image"
                  :src="record.displayCoverImage"
                  mode="aspectFill"
                />
                <view v-else class="record-card__media-placeholder" aria-hidden="true">
                  <view class="record-card__media-placeholder-mark"></view>
                  <text>探索瞬间</text>
                </view>
              </view>

              <view class="record-card__body">
                <view class="record-card__route-row">
                  <text class="record-card__title">{{ recordRouteLabel(record) }}</text>
                  <text class="record-card__arrow" aria-hidden="true">›</text>
                </view>
                <text v-if="record.recordDateLabel" class="record-card__date">{{ record.recordDateLabel }}</text>
                <text v-if="record.taskCount" class="record-card__progress">{{ taskProgressText(record) }}</text>
                <view v-if="record.taskCount" class="record-card__progress-track" aria-hidden="true">
                  <view class="record-card__progress-value" :style="{ width: taskCompletionWidth(record) }"></view>
                </view>
                <view v-if="record.taskCount || record.photoCount || record.noteCount" class="record-card__stats">
                  <view v-if="record.taskCount" class="record-card__stat">
                    <text class="record-card__stat-icon" aria-hidden="true">✓</text>
                    <text>{{ record.taskCount }} 个任务</text>
                  </view>
                  <view v-if="record.photoCount" class="record-card__stat">
                    <text class="record-card__stat-icon" aria-hidden="true">▣</text>
                    <text>{{ record.photoCount }} 张照片</text>
                  </view>
                  <view v-if="record.noteCount" class="record-card__stat">
                    <text class="record-card__stat-icon" aria-hidden="true">✎</text>
                    <text>{{ record.noteCount }} 条笔记</text>
                  </view>
                </view>
              </view>
            </view>
          </view>
        </view>
      </template>
    </view>

    <AppTabbar active="record" />
  </view>
</template>

<script>
import AppTabbar from '../../components/AppTabbar.vue'
import { useChildStore } from '../../stores/child'
import { useRecordStore } from '../../stores/record'
import { useUserStore } from '../../stores/user'
import { endUserSession } from '../../utils/sessionBoundary'

function isAuthenticationError(error) {
  return ['UNAUTHORIZED', 'TOKEN_EXPIRED', 'INVALID_TOKEN'].includes(error?.code) || error?.statusCode === 401
}

function recordDate(record) {
  const value = record?.finalizedAt || record?.updatedAt || record?.createdAt
  if (typeof value !== 'string' || !value.trim()) return null
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

function formatRecordDate(value) {
  return value ? `${value.getFullYear()}年${value.getMonth() + 1}月${value.getDate()}日` : ''
}

export default {
  components: { AppTabbar },
  computed: {
    childStore() { return useChildStore() },
    childErrorMessage() { return this.childStore.error?.message || '请检查网络后重新加载孩子资料' },
    error() { return this.recordStore.error },
    errorMessage() { return this.error?.message || '请检查网络后再试一次' },
    hasActiveChild() {
      const childId = Number(this.childStore.activeChild?.id)
      return this.childStore.isLoaded
        && !this.childStore.error
        && this.childStore.hasRemoteChild
        && String(this.childStore.loadedForUserId) === String(this.userStore.userInfo?.id)
        && Number.isInteger(childId)
        && childId > 0
    },
    isChildLoading() { return this.childStore.isLoading || (!this.childStore.isLoaded && !this.childStore.error) },
    isEmpty() { return this.recordStore.hasLoaded && !this.loading && !this.error && this.records.length === 0 },
    isInitialLoading() { return this.loading && this.records.length === 0 && !this.recordStore.hasLoaded },
    loading() { return this.recordStore.loading },
    records() { return this.recordStore.records },
    recordsByYear() {
      const groups = new Map()
      this.records.forEach((record) => {
        const date = recordDate(record)
        const recordYear = date ? String(date.getFullYear()) : '未标注日期'
        const datedRecord = { ...record, recordDateLabel: formatRecordDate(date), recordSortTime: date?.getTime() || 0 }
        if (!groups.has(recordYear)) groups.set(recordYear, [])
        groups.get(recordYear).push(datedRecord)
      })
      return [...groups.entries()]
        .map(([recordYear, records]) => ({ recordYear, records: records.sort((left, right) => right.recordSortTime - left.recordSortTime) }))
        .sort((left, right) => {
          if (left.recordYear === '未标注日期') return 1
          if (right.recordYear === '未标注日期') return -1
          return Number(right.recordYear) - Number(left.recordYear)
        })
    },
    recordStore() { return useRecordStore() },
    showChildError() { return !this.isChildLoading && Boolean(this.childStore.error) },
    showFullError() { return Boolean(this.error) && this.records.length === 0 },
    showNoChild() { return !this.isChildLoading && !this.childStore.error && this.childStore.isLoaded && !this.hasActiveChild },
    userStore() { return useUserStore() },
  },
  async onShow() {
    await this.loadRecords()
  },
  methods: {
    async handleAuthExpired() { await endUserSession() },
    async loadRecords() {
      if (!this.userStore.isAuthReady || this.userStore.isRestoring) await this.userStore.restoreSession()
      if (!this.userStore.isLoggedIn || !this.userStore.userInfo?.id) {
        this.recordStore.resetRecordState()
        uni.reLaunch({ url: '/pages/login/index' })
        return
      }
      try {
        await this.childStore.fetchChildren(this.userStore.userInfo.id)
      } catch (error) {
        if (isAuthenticationError(error)) await this.handleAuthExpired()
        return
      }
      if (!this.hasActiveChild) return
      try {
        await this.recordStore.loadJourneyRecords({ childId: this.childStore.activeChild.id, limit: 20, offset: 0 })
      } catch (error) {
        if (isAuthenticationError(error)) await this.handleAuthExpired()
      }
    },
    goExplore() {
      uni.reLaunch({ url: '/pages/explore/index' })
    },
    openRecordDetail(record) {
      const planId = Number(record?.planId)
      if (Number.isInteger(planId) && planId > 0) uni.navigateTo({ url: `/pages/record-detail/index?planId=${planId}` })
    },
    recordRouteLabel(record) {
      const title = record?.displayTitle || '一次探索'
      return record?.destination ? `${title} · ${record.destination}` : title
    },
    async retryRecords() {
      await this.loadRecords()
    },
    taskCompletionWidth(record) {
      const total = Number(record?.taskCount) || 0
      const completed = Math.min(Number(record?.completedTaskCount) || 0, total)
      return total ? `${Math.round((completed / total) * 100)}%` : '0%'
    },
    taskProgressText(record) {
      const total = Number(record?.taskCount) || 0
      const completed = Math.min(Number(record?.completedTaskCount) || 0, total)
      if (!total) return ''
      return `${completed} / ${total} 个任务已完成`
    },
  },
}
</script>

<style scoped>
.record-page { min-height: 100vh; overflow-x: hidden; color: var(--tl-text-main); background: var(--tl-bg); }
.record-page__content { width: 100%; max-width: var(--tl-content-max-width); min-height: 100vh; padding: calc(48rpx + var(--tl-safe-top)) var(--tl-page-padding) calc(var(--tl-tabbar-height) + 56rpx + var(--tl-safe-bottom)); margin: 0 auto; }
.record-header { margin-bottom: 56rpx; }
.record-header__title, .record-year-group__title, .record-state__title, .record-card__title { display: block; font-weight: var(--tl-weight-section-title); }
.record-header__title { font-size: 48rpx; font-weight: var(--tl-weight-page-title); line-height: 1.25; letter-spacing: 1rpx; }
.record-header__subtitle { display: block; margin-top: 10rpx; font-size: var(--tl-type-meta); line-height: 1.5; color: var(--tl-text-secondary); }
.record-year-group + .record-year-group { margin-top: 64rpx; }
.record-year-group__title { margin-bottom: 24rpx; font-size: 34rpx; line-height: 1.3; }
.record-list { display: flex; flex-direction: column; gap: 28rpx; }
.record-card { overflow: hidden; background: var(--tl-surface); border: 1rpx solid rgba(190, 142, 78, 0.14); border-radius: var(--tl-radius-sheet); box-shadow: var(--tl-shadow-media); transition: opacity 160ms ease, transform 160ms ease; }
.record-card--pressed { opacity: 0.76; transform: scale(0.988); }
.record-card__media { height: 316rpx; overflow: hidden; background: var(--tl-surface-muted); }
.record-card__image { display: block; width: 100%; height: 100%; }
.record-card__media-placeholder { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 12rpx; width: 100%; height: 100%; font-size: 22rpx; color: var(--tl-text-secondary); background: linear-gradient(145deg, #f3e8d1, #ebe0ca); }
.record-card__media-placeholder-mark { width: 48rpx; height: 38rpx; border: 3rpx solid rgba(138, 109, 84, 0.52); border-radius: 8rpx; }
.record-card__body { padding: 28rpx 28rpx 30rpx; }
.record-card__route-row { display: flex; gap: 16rpx; align-items: center; min-width: 0; }
.record-card__title { flex: 1; min-width: 0; overflow: hidden; font-size: 31rpx; line-height: 1.4; text-overflow: ellipsis; white-space: nowrap; }
.record-card__arrow { flex: 0 0 auto; font-size: 44rpx; line-height: 0.9; color: var(--tl-text-secondary); }
.record-card__date, .record-card__progress { display: block; margin-top: 14rpx; line-height: 1.4; }
.record-card__date { font-size: var(--tl-type-meta); color: var(--tl-text-secondary); }
.record-card__progress { font-size: 27rpx; font-weight: 500; color: var(--tl-green-deep); }
.record-card__progress-track { height: 12rpx; margin-top: 16rpx; overflow: hidden; background: #e8ecef; border-radius: 99rpx; }
.record-card__progress-value { height: 100%; min-width: 10rpx; background: #53b988; border-radius: inherit; transition: width 180ms ease; }
.record-card__stats { display: flex; flex-wrap: wrap; gap: 14rpx 28rpx; margin-top: 24rpx; padding-top: 22rpx; border-top: 1rpx solid var(--tl-divider); }
.record-card__stat { display: inline-flex; gap: 10rpx; align-items: center; font-size: 24rpx; line-height: 1.3; color: var(--tl-text-secondary); }
.record-card__stat-icon { display: inline-flex; align-items: center; justify-content: center; width: 28rpx; height: 28rpx; font-size: 20rpx; font-weight: 700; line-height: 1; color: #64748b; border: 2rpx solid currentColor; border-radius: 7rpx; }
.record-state { display: flex; flex-direction: column; align-items: center; padding: 104rpx var(--tl-space-lg); text-align: center; }
.record-state--error { color: var(--tl-primary-deep); }
.record-state__spinner { width: 48rpx; height: 48rpx; margin-bottom: var(--tl-space-md); border: 4rpx solid var(--tl-surface-muted); border-top-color: var(--tl-primary); border-radius: 50%; }
.record-state__album-mark { width: 58rpx; height: 46rpx; margin-bottom: var(--tl-space-md); border: 3rpx solid var(--tl-green-deep); border-radius: var(--tl-radius-small); }
.record-state__title { font-size: var(--tl-type-section-title); }
.record-state__desc { display: block; max-width: 440rpx; margin-top: var(--tl-space-sm); font-size: var(--tl-type-body); line-height: var(--tl-line-height-body); color: var(--tl-text-secondary); }
.record-state__action { min-width: 184rpx; min-height: var(--tl-control-min-height); margin-top: var(--tl-space-lg); font-size: var(--tl-type-primary-action); font-weight: var(--tl-weight-primary-action); color: var(--tl-paper); background: var(--tl-primary); border-radius: var(--tl-radius-control); }
.record-refresh-error { display: flex; justify-content: space-between; gap: var(--tl-space-sm); padding: var(--tl-space-sm) 0; margin-bottom: 28rpx; font-size: var(--tl-type-meta); color: var(--tl-primary-deep); border-bottom: 1rpx solid var(--tl-divider); }
.record-refresh-error__retry { flex-shrink: 0; text-decoration: underline; }
@media (min-width: 431px) { .record-page__content { padding-right: 18px; padding-left: 18px; } .record-header__title { font-size: 28px; } .record-card__media { height: 188px; } .record-card__body { padding: 16px; } }
@media (max-width: 350px) { .record-page__content { padding-right: 24rpx; padding-left: 24rpx; } .record-card__stats { gap: 12rpx 18rpx; } .record-card__stat { font-size: 22rpx; } }
</style>
