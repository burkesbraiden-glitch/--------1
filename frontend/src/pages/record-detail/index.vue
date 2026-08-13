<template>
  <view class="record-detail-page">
    <view class="record-detail-page__paper">
      <view class="record-detail-header">
        <button class="record-detail-header__back" @click="goBack" aria-label="返回">
          <view aria-hidden="true"></view>
        </button>
        <view class="record-detail-header__title-wrap">
          <view class="record-detail-header__spark" aria-hidden="true"></view>
          <text class="record-detail-header__title">旅行记录</text>
        </view>
        <view class="record-detail-header__spacer"></view>
      </view>

      <view v-if="routeError" class="record-detail-state record-detail-state--error">
        <text class="record-detail-state__title">这份旅行记录暂时无法打开</text>
        <button class="record-detail-state__button" @click="backToRecordList">返回记录页</button>
      </view>

      <view v-else-if="isInitialLoading" class="record-detail-state">
        <view class="record-detail-state__spinner"></view>
        <text class="record-detail-state__title">正在翻开旅行手账…</text>
      </view>

      <view v-else-if="showFullError" class="record-detail-state record-detail-state--error">
        <text class="record-detail-state__title">旅行记录加载失败</text>
        <text class="record-detail-state__desc">{{ errorMessage }}</text>
        <button class="record-detail-state__button" @click="retryDetail">重新加载</button>
      </view>

      <template v-else-if="record">
        <view v-if="detailError" class="record-detail-refresh-error">
          <text>{{ errorMessage }}</text>
          <text @click="retryDetail">重试</text>
        </view>

        <view class="record-detail-title-card">
          <view class="record-detail-title-card__tape"></view>
          <text class="record-detail-title-card__title">{{ record.displayTitle }}</text>
          <text class="record-detail-title-card__destination">⌖ {{ record.destination || '目的地待补充' }}</text>
          <view class="record-detail-title-card__meta">
            <text class="record-detail-status" :class="`record-detail-status--${record.status}`">{{ statusText }}</text>
            <text v-if="record.status === 'finalized' && record.displayFinalizedAt">封存于 {{ record.displayFinalizedAt }}</text>
            <text v-if="record.displayUpdatedAt">更新于 {{ record.displayUpdatedAt }}</text>
          </view>
        </view>

        <view class="record-detail-overview">
          <PolaroidCard
            class="record-detail-overview__cover"
            :image-path="coverPhotoImage"
            :title="record.displayTitle"
            :description="record.destination"
            :date-label="record.displayUpdatedAt"
            placeholder-theme="roof"
            tape-theme="green"
            :rotation="-2"
          >
            <template v-if="coverPhotoState === 'loading'" #photo>
              <view class="record-detail-photo-state record-detail-photo-state--loading">
                <view class="record-detail-photo-state__wash"></view>
              </view>
            </template>
            <template v-else-if="coverPhotoState === 'error'" #photo>
              <view class="record-detail-photo-state record-detail-photo-state--error">
                <text>照片加载失败</text>
                <button @click.stop="retryDetail">重试加载</button>
              </view>
            </template>
          </PolaroidCard>
          <view class="record-detail-overview__stats">
            <GrowthBadge label="完成任务" :value="`${record.completedTaskCount} / ${record.taskCount}`" icon="✓" theme="yellow" />
            <GrowthBadge label="照片" :value="record.photoCount" icon="●" theme="blue" />
            <GrowthBadge label="笔记" :value="record.noteCount" icon="✎" theme="green" />
          </view>
        </view>

        <view class="record-detail-summary">
          <view class="record-detail-summary__tape"></view>
          <text class="record-detail-section-title">旅途小结</text>
          <text class="record-detail-summary__text">{{ record.summary || '这份旅行记录还没有写下旅途小结。' }}</text>
        </view>

        <view v-if="record.status === 'draft'" class="record-detail-editor">
          <view class="record-detail-editor__tape"></view>
          <view class="record-detail-editor__heading">
            <text class="record-detail-section-title">整理这页手账</text>
            <view class="record-detail-editor__spark" aria-hidden="true"></view>
          </view>

          <view v-if="saveError" class="record-detail-editor__error">
            <text>{{ saveErrorMessage }}</text>
          </view>

          <view class="record-detail-editor__field">
            <text class="record-detail-editor__label">旅行标题</text>
            <input
              v-model="customTitleDraft"
              class="record-detail-editor__input"
              maxlength="120"
              placeholder="给这次探索起个名字"
              @input="clearSaveError"
            />
            <text class="record-detail-editor__hint">清空后将恢复计划原始标题</text>
          </view>

          <view class="record-detail-editor__field">
            <view class="record-detail-editor__label-row">
              <text class="record-detail-editor__label">旅途小结</text>
              <text class="record-detail-editor__count">{{ summaryDraft.length }} / 2000</text>
            </view>
            <textarea
              v-model="summaryDraft"
              class="record-detail-editor__textarea"
              maxlength="2000"
              placeholder="写下孩子今天观察到的新发现吧…"
              @input="clearSaveError"
            />
          </view>

          <view class="record-detail-editor__field">
            <view class="record-detail-editor__label-row">
              <text class="record-detail-editor__label">手账封面</text>
              <text class="record-detail-editor__hint">从有照片的任务中挑选</text>
            </view>
            <view v-if="coverCandidates.length" class="record-detail-cover-list">
              <view
                v-for="entry in coverCandidates"
                :key="entry.submissionId"
                class="record-detail-cover-option"
                :class="{ 'record-detail-cover-option--selected': selectedCoverSubmissionId === entry.submissionId }"
                @click="selectCover(entry.submissionId)"
              >
                <image v-if="entry.displayImage" class="record-detail-cover-option__image" :src="entry.displayImage" mode="aspectFill" />
                <view v-else class="record-detail-cover-option__placeholder" aria-hidden="true"></view>
                <text class="record-detail-cover-option__title">{{ entry.title || '观察任务照片' }}</text>
                <text v-if="selectedCoverSubmissionId === entry.submissionId" class="record-detail-cover-option__mark">已选</text>
              </view>
            </view>
            <text v-else class="record-detail-editor__empty">完成带照片的观察任务后，就可以选择旅行记录封面。</text>
            <view class="record-detail-cover-list record-detail-cover-list--clear">
              <view
                class="record-detail-cover-option record-detail-cover-option--clear"
                :class="{ 'record-detail-cover-option--selected': selectedCoverSubmissionId === null }"
                @click="clearCover"
              >
                <view class="record-detail-cover-option__placeholder record-detail-cover-option__placeholder--clear" aria-hidden="true"></view>
                <text class="record-detail-cover-option__title">清除封面</text>
                <text v-if="selectedCoverSubmissionId === null" class="record-detail-cover-option__mark">已选</text>
              </view>
            </view>
          </view>

          <button class="record-detail-editor__save" :disabled="!hasDraftChanges || saving || finalizing" @click="saveDraftChanges">
            {{ saving ? '正在保存…' : '保存修改' }}
          </button>
        </view>

        <view v-if="record.status === 'draft'" class="record-detail-finalize-action">
          <text class="record-detail-finalize-action__hint">整理完成后可以封存，这一步将不能撤销。</text>
          <view v-if="finalizeError" class="record-detail-editor__error">
            <text>{{ finalizeErrorMessage }}</text>
          </view>
          <button class="record-detail-finalize-action__button" :disabled="saving || finalizing" @click="confirmFinalizeRecord">
            {{ finalizing ? '正在封存…' : '封存这份旅行记录' }}
          </button>
        </view>

        <view class="record-detail-section-head">
          <view class="record-detail-section-head__camera" aria-hidden="true"></view>
          <text>探索相册</text>
          <view class="record-detail-section-head__line"></view>
          <view class="record-detail-section-head__spark" aria-hidden="true"></view>
        </view>

        <view v-if="record.entries.length" class="record-detail-entry-list">
          <view v-for="(entry, index) in record.entries" :key="entry.submissionId || entry.taskId" class="record-detail-entry">
            <PolaroidCard
              class="record-detail-entry__photo"
              :image-path="entryPhotoImage(entry)"
              :title="entry.title"
              :description="entry.subtitle"
              :date-label="entry.displayCompletedAt"
              :placeholder-theme="index % 2 === 0 ? 'roof' : 'gate'"
              :tape-theme="tapeTheme(index)"
              :rotation="index % 2 === 0 ? -2 : 2"
            >
              <template v-if="entryPhotoState(entry) === 'loading'" #photo>
                <view class="record-detail-photo-state record-detail-photo-state--loading">
                  <view class="record-detail-photo-state__wash"></view>
                </view>
              </template>
              <template v-else-if="entryPhotoState(entry) === 'error'" #photo>
                <view class="record-detail-photo-state record-detail-photo-state--error">
                  <text>照片加载失败</text>
                  <button @click.stop="retryDetail">重试加载</button>
                </view>
              </template>
            </PolaroidCard>
            <view class="record-detail-entry__note">
              <view class="record-detail-entry__head">
                <text class="record-detail-entry__title">{{ entry.title }}</text>
                <text class="record-detail-entry__status">{{ entryStatusText(entry.status) }}</text>
              </view>
              <text v-if="entry.subtitle" class="record-detail-entry__subtitle">{{ entry.subtitle }}</text>
              <view class="record-detail-entry__dash"></view>
              <text v-if="entry.note" class="record-detail-entry__text">{{ entry.note }}</text>
              <text v-else class="record-detail-entry__text record-detail-entry__text--empty">这一站还没有留下文字发现。</text>
              <text v-if="entry.completedAt" class="record-detail-entry__date">{{ entry.displayCompletedAt }}</text>
            </view>
          </view>
        </view>
        <view v-else class="record-detail-empty-entries">
          <text>这份旅行记录里还没有可展示的任务内容。</text>
        </view>

        <view v-if="record.status === 'finalized'" class="record-detail-finalized">
          <text>这份旅行记录已经封存。</text>
        </view>
      </template>
    </view>

  </view>
</template>

<script>
import GrowthBadge from '../../components/GrowthBadge.vue'
import PolaroidCard from '../../components/PolaroidCard.vue'
import recordWatercolorFallback from '../../assets/record/record-watercolor-fallback.webp'
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

function normalizeDraftText(value) {
  const text = typeof value === 'string' ? value.trim() : ''
  return text || null
}

function normalizeSubmissionId(value) {
  const submissionId = Number(value)
  return Number.isInteger(submissionId) && submissionId > 0 ? submissionId : null
}

export default {
  components: {
    GrowthBadge,
    PolaroidCard,
  },
  data() {
    return {
      routePlanId: null,
      routeError: false,
      customTitleDraft: '',
      summaryDraft: '',
      selectedCoverSubmissionId: null,
      draftInitializedPlanId: null,
    }
  },
  computed: {
    detailError() {
      return this.recordStore.detailError
    },
    saveError() {
      return this.recordStore.saveError
    },
    saveErrorMessage() {
      return this.saveError?.message || '保存失败，请稍后重试'
    },
    finalizeError() {
      return this.recordStore.finalizeError
    },
    finalizeErrorMessage() {
      return this.finalizeError?.message || '封存失败，请稍后重试'
    },
    errorMessage() {
      return this.detailError?.message || '请检查网络后再试一次。'
    },
    isInitialLoading() {
      return this.recordStore.detailLoading && !this.record
    },
    record() {
      return this.recordStore.currentRecord
    },
    recordStore() {
      return useRecordStore()
    },
    saving() {
      return this.recordStore.saving
    },
    finalizing() {
      return this.recordStore.finalizing
    },
    showFullError() {
      return Boolean(this.detailError) && !this.record
    },
    statusText() {
      return this.record?.status === 'finalized' ? '已封存' : '整理中'
    },
    coverCandidates() {
      const entries = Array.isArray(this.record?.entries) ? this.record.entries : []
      return entries
        .filter((entry) => normalizeSubmissionId(entry?.submissionId) && typeof entry?.imageUrl === 'string' && entry.imageUrl.trim())
        .map((entry) => ({ ...entry, submissionId: normalizeSubmissionId(entry.submissionId) }))
    },
    coverPhotoState() {
      return this.photoState(this.record?.coverImageUrl, this.record?.displayCoverImage)
    },
    coverPhotoImage() {
      if (this.coverPhotoState === 'no-image') {
        return recordWatercolorFallback
      }
      return this.record?.displayCoverImage || ''
    },
    hasDraftChanges() {
      return Object.keys(this.buildDraftChanges()).length > 0
    },
    userStore() {
      return useUserStore()
    },
  },
  onLoad(options) {
    this.routePlanId = normalizePlanId(options?.planId)
    this.routeError = !this.routePlanId
    if (!this.routeError) {
      this.loadDetail()
    }
  },
  onUnload() {
    this.recordStore.clearJourneyRecordDetail()
  },
  watch: {
    record: {
      immediate: true,
      handler(record) {
        if (record && record.planId !== this.draftInitializedPlanId) {
          this.syncDraftFromRecord(record)
        }
      },
    },
  },
  methods: {
    syncDraftFromRecord(record) {
      this.customTitleDraft = record?.customTitle || ''
      this.summaryDraft = record?.summary || ''
      this.selectedCoverSubmissionId = normalizeSubmissionId(record?.coverSubmissionId)
      this.draftInitializedPlanId = record?.planId || null
    },
    buildDraftChanges() {
      if (!this.record) {
        return {}
      }

      const changes = {}
      const customTitle = normalizeDraftText(this.customTitleDraft)
      const summary = normalizeDraftText(this.summaryDraft)
      const coverSubmissionId = normalizeSubmissionId(this.selectedCoverSubmissionId)
      if (customTitle !== normalizeDraftText(this.record.customTitle)) {
        changes.customTitle = customTitle
      }
      if (summary !== normalizeDraftText(this.record.summary)) {
        changes.summary = summary
      }
      if (coverSubmissionId !== normalizeSubmissionId(this.record.coverSubmissionId)) {
        changes.coverSubmissionId = coverSubmissionId
      }
      return changes
    },
    clearCover() {
      this.selectedCoverSubmissionId = null
      this.clearSaveError()
    },
    clearSaveError() {
      if (this.recordStore.saveError) {
        this.recordStore.saveError = null
      }
    },
    selectCover(submissionId) {
      const normalizedSubmissionId = normalizeSubmissionId(submissionId)
      if (!normalizedSubmissionId) {
        return
      }
      this.selectedCoverSubmissionId = normalizedSubmissionId
      this.clearSaveError()
    },
    async saveDraftChanges() {
      if (!this.record || this.record.status !== 'draft' || this.saving || this.finalizing) {
        return
      }

      const changes = this.buildDraftChanges()
      if (!Object.keys(changes).length) {
        uni.showToast({ title: '还没有需要保存的修改', icon: 'none' })
        return
      }

      this.clearSaveError()
      try {
        const result = await this.recordStore.saveJourneyRecordDraft(this.routePlanId, changes)
        if (!result?.saved || !result.journeyRecord) {
          uni.showToast({ title: '还没有需要保存的修改', icon: 'none' })
          return
        }
        this.syncDraftFromRecord(result.journeyRecord)
        uni.showToast({ title: '旅行记录已保存', icon: 'success' })
      } catch (error) {
        if (isAuthenticationError(error)) {
          await endUserSession()
          return
        }
        uni.showToast({ title: this.saveErrorMessage, icon: 'none' })
      }
    },
    confirmFinalizeRecord() {
      if (!this.record || this.record.status !== 'draft' || this.saving || this.finalizing) {
        return
      }
      uni.showModal({
        title: '确认封存',
        content: '封存后将不能再修改标题、摘要和封面。',
        confirmText: '确认封存',
        cancelText: '再想想',
        success: (result) => {
          if (result.confirm) {
            this.finalizeRecord()
          }
        },
      })
    },
    async finalizeRecord() {
      if (!this.record || this.record.status !== 'draft' || this.saving || this.finalizing) {
        return
      }
      try {
        const result = await this.recordStore.finalizeJourneyRecordDraft(this.routePlanId)
        if (!result?.finalized || !result.journeyRecord) {
          return
        }
        uni.showToast({ title: '旅行记录已封存', icon: 'success' })
      } catch (error) {
        if (isAuthenticationError(error)) {
          await endUserSession()
          return
        }
        uni.showToast({ title: this.finalizeErrorMessage, icon: 'none' })
      }
    },
    async handleAuthExpired() {
      await endUserSession()
    },
    async loadDetail() {
      if (!this.routePlanId) {
        return
      }
      if (!this.userStore.isAuthReady || this.userStore.isRestoring) {
        await this.userStore.restoreSession()
      }
      if (!this.userStore.isLoggedIn || !this.userStore.userInfo?.id) {
        this.recordStore.resetRecordState()
        uni.reLaunch({
          url: '/pages/login/index',
        })
        return
      }
      try {
        await this.recordStore.loadJourneyRecordDetail(this.routePlanId)
      } catch (error) {
        if (isAuthenticationError(error)) {
          await this.handleAuthExpired()
        }
      }
    },
    entryStatusText(status) {
      return status === 'completed' ? '已完成' : '记录中'
    },
    goBack() {
      const pages = getCurrentPages()
      if (Array.isArray(pages) && pages.length > 1) {
        uni.navigateBack({
          delta: 1,
          fail: () => this.backToRecordList(),
        })
        return
      }
      this.backToRecordList()
    },
    backToRecordList() {
      uni.switchTab({
        url: '/pages/record/index',
        fail: () => {
          uni.reLaunch({
            url: '/pages/record/index',
          })
        },
      })
    },
    async retryDetail() {
      try {
        await this.recordStore.retryJourneyRecordDetail()
      } catch (error) {
        if (isAuthenticationError(error)) {
          await this.handleAuthExpired()
        }
      }
    },
    tapeTheme(index) {
      return ['green', 'pink', 'blue'][index % 3]
    },
    photoState(imageUrl, displayImage) {
      if (!imageUrl) {
        return 'no-image'
      }
      if (displayImage) {
        return 'image'
      }
      return this.recordStore.detailLoading ? 'loading' : 'error'
    },
    entryPhotoState(entry) {
      return this.photoState(entry?.imageUrl, entry?.displayImage)
    },
    entryPhotoImage(entry) {
      const state = this.entryPhotoState(entry)
      if (state === 'no-image') {
        return recordWatercolorFallback
      }
      return entry?.displayImage || ''
    },
  },
}
</script>

<style scoped>
.record-detail-page {
  min-height: 100vh;
  overflow-x: hidden;
  color: #4a2f1b;
  background:
    radial-gradient(circle at 14% 10%, rgba(255, 240, 189, 0.48) 0, rgba(255, 240, 189, 0) 112rpx),
    linear-gradient(135deg, rgba(148, 104, 48, 0.05) 0 1rpx, transparent 1rpx 22rpx),
    #f8efd9;
}

.record-detail-page__paper {
  width: 100%;
  max-width: 430px;
  min-height: 100vh;
  padding: calc(28rpx + env(safe-area-inset-top)) 30rpx calc(110rpx + env(safe-area-inset-bottom));
  margin: 0 auto;
}

.record-detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 28rpx;
}

.record-detail-header__back,
.record-detail-header__spacer {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  width: 64rpx;
  height: 64rpx;
  font-weight: 900;
  color: #4a2f1b;
}

.record-detail-header__back {
  position: relative;
  font-size: 64rpx;
}

.record-detail-header__back view::after {
  position: absolute;
  top: 23rpx;
  left: 27rpx;
  width: 16rpx;
  height: 16rpx;
  content: '';
  border-bottom: 4rpx solid currentColor;
  border-left: 4rpx solid currentColor;
  transform: rotate(45deg);
}

.record-detail-header__title-wrap {
  position: relative;
  flex: 1;
  text-align: center;
}

.record-detail-header__title {
  font-size: 46rpx;
  font-weight: 900;
}

.record-detail-header__spark {
  position: absolute;
  top: -16rpx;
  margin-left: -28rpx;
  width: 18rpx;
  height: 18rpx;
  color: #f4aa23;
  transform: rotate(45deg);
}

.record-detail-header__spark::after,
.record-detail-editor__spark::after,
.record-detail-section-head__spark::after {
  position: absolute;
  inset: 0;
  content: '';
  background: currentColor;
  border-radius: 5rpx;
}

.record-detail-state,
.record-detail-title-card,
.record-detail-summary,
.record-detail-empty-entries,
.record-detail-finalized,
.record-detail-entry__note {
  position: relative;
  background: rgba(255, 247, 232, 0.92);
  border: 3rpx solid rgba(223, 189, 131, 0.68);
  box-shadow: 8rpx 10rpx 0 rgba(223, 189, 131, 0.13);
}

.record-detail-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 22rpx;
  padding: 72rpx 40rpx;
  text-align: center;
  border-radius: 30rpx;
}

.record-detail-state--error {
  border-color: rgba(217, 75, 18, 0.42);
}

.record-detail-state__spinner {
  width: 72rpx;
  height: 72rpx;
  border: 8rpx solid #fff0bd;
  border-top-color: #f26a21;
  border-radius: 50%;
}

.record-detail-state__title,
.record-detail-title-card__title,
.record-detail-section-title,
.record-detail-entry__title {
  font-size: 34rpx;
  font-weight: 900;
}

.record-detail-state__desc,
.record-detail-summary__text,
.record-detail-entry__text {
  font-size: 26rpx;
  line-height: 1.6;
  color: #5e3c22;
}

.record-detail-state__button {
  min-width: 190rpx;
  font-size: 27rpx;
  font-weight: 900;
  color: #fff;
  background: #f26a21;
  border-radius: 999rpx;
}

.record-detail-title-card {
  padding: 42rpx 30rpx 28rpx;
  margin-bottom: 28rpx;
  border-radius: 30rpx;
}

.record-detail-title-card__tape,
.record-detail-summary__tape {
  position: absolute;
  top: -16rpx;
  left: 42rpx;
  width: 88rpx;
  height: 38rpx;
  background: rgba(255, 208, 119, 0.74);
  border-radius: 8rpx;
  transform: rotate(9deg);
}

.record-detail-title-card__title,
.record-detail-title-card__destination,
.record-detail-summary__text,
.record-detail-entry__subtitle,
.record-detail-entry__date {
  display: block;
}

.record-detail-title-card__title {
  font-size: 42rpx;
}

.record-detail-title-card__destination {
  margin-top: 16rpx;
  font-size: 26rpx;
  color: #6b482d;
}

.record-detail-title-card__meta {
  display: flex;
  gap: 16rpx;
  align-items: center;
  margin-top: 22rpx;
  font-size: 22rpx;
  color: #8a6d54;
}

.record-detail-status,
.record-detail-entry__status {
  padding: 7rpx 14rpx;
  font-size: 21rpx;
  font-weight: 900;
  color: #d94b12;
  background: #fff1d8;
  border-radius: 999rpx;
}

.record-detail-status--finalized {
  color: #55753c;
  background: #dceecb;
}

.record-detail-overview {
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(0, 0.95fr);
  gap: 24rpx;
  align-items: center;
  margin-bottom: 28rpx;
}

.record-detail-overview__stats {
  display: grid;
  gap: 14rpx;
}

.record-detail-summary {
  padding: 38rpx 28rpx 28rpx;
  margin-bottom: 34rpx;
  border-radius: 26rpx;
}

.record-detail-summary__text {
  display: block;
  margin-top: 16rpx;
}

.record-detail-editor {
  position: relative;
  padding: 42rpx 28rpx 30rpx;
  margin-bottom: 34rpx;
  background: rgba(238, 246, 220, 0.78);
  border: 3rpx solid rgba(123, 154, 80, 0.42);
  border-radius: 26rpx;
  box-shadow: 8rpx 10rpx 0 rgba(123, 154, 80, 0.1);
}

.record-detail-editor__tape {
  position: absolute;
  top: -16rpx;
  right: 46rpx;
  width: 86rpx;
  height: 36rpx;
  background: rgba(164, 208, 157, 0.72);
  border-radius: 8rpx;
  transform: rotate(-8deg);
}

.record-detail-editor__heading,
.record-detail-editor__label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16rpx;
}

.record-detail-editor__heading {
  margin-bottom: 28rpx;
  color: #55753c;
}

.record-detail-editor__spark,
.record-detail-section-head__spark {
  position: relative;
  width: 17rpx;
  height: 17rpx;
  color: #f4aa23;
  transform: rotate(45deg);
}

.record-detail-editor__field + .record-detail-editor__field {
  margin-top: 26rpx;
}

.record-detail-editor__label {
  font-size: 27rpx;
  font-weight: 900;
  color: #4a2f1b;
}

.record-detail-editor__hint,
.record-detail-editor__count {
  font-size: 21rpx;
  color: #6b765a;
}

.record-detail-editor__input,
.record-detail-editor__textarea {
  box-sizing: border-box;
  width: 100%;
  margin-top: 12rpx;
  font-size: 26rpx;
  line-height: 1.5;
  color: #4a2f1b;
  background: rgba(255, 253, 244, 0.88);
  border: 2rpx dashed rgba(123, 154, 80, 0.5);
  border-radius: 16rpx;
}

.record-detail-editor__input {
  height: 76rpx;
  padding: 0 20rpx;
}

.record-detail-editor__input + .record-detail-editor__hint {
  display: block;
  margin-top: 10rpx;
}

.record-detail-editor__textarea {
  min-height: 176rpx;
  padding: 16rpx 20rpx;
}

.record-detail-editor__error {
  padding: 14rpx 18rpx;
  margin-bottom: 22rpx;
  font-size: 23rpx;
  color: #9a421b;
  background: #fff1d8;
  border: 2rpx dashed rgba(217, 75, 18, 0.42);
  border-radius: 14rpx;
}

.record-detail-cover-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16rpx;
  margin-top: 14rpx;
}

.record-detail-cover-list--clear {
  grid-template-columns: minmax(0, 1fr);
}

.record-detail-cover-option {
  position: relative;
  min-width: 0;
  padding: 12rpx;
  background: rgba(255, 253, 244, 0.82);
  border: 2rpx solid rgba(223, 189, 131, 0.62);
  border-radius: 16rpx;
}

.record-detail-cover-option--selected {
  background: #e0f0d5;
  border-color: #719b58;
  box-shadow: 0 0 0 3rpx rgba(113, 155, 88, 0.16);
}

.record-detail-cover-option__image,
.record-detail-cover-option__placeholder {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 112rpx;
  color: #8a6d54;
  background: #fff0bd;
  border-radius: 10rpx;
}

.record-detail-cover-option__placeholder::before,
.record-detail-cover-option__placeholder::after {
  position: absolute;
  box-sizing: border-box;
  content: '';
}

.record-detail-cover-option__placeholder::before {
  width: 42rpx;
  height: 32rpx;
  border: 3rpx solid currentColor;
  border-radius: 7rpx;
}

.record-detail-cover-option__placeholder::after {
  top: 34rpx;
  left: 50%;
  width: 12rpx;
  height: 12rpx;
  background: currentColor;
  border-radius: 50%;
  transform: translateX(-50%);
}

.record-detail-cover-option__image {
  display: block;
}

.record-detail-cover-option--clear .record-detail-cover-option__placeholder {
  color: #a3623e;
  background: #fff7e8;
  border: 2rpx dashed rgba(163, 98, 62, 0.38);
}

.record-detail-cover-option--clear .record-detail-cover-option__placeholder--clear::before,
.record-detail-cover-option--clear .record-detail-cover-option__placeholder--clear::after {
  top: 50%;
  left: 50%;
  width: 42rpx;
  height: 3rpx;
  background: currentColor;
  border: 0;
  border-radius: 999rpx;
  transform: translate(-50%, -50%) rotate(45deg);
}

.record-detail-cover-option--clear .record-detail-cover-option__placeholder--clear::after {
  transform: translate(-50%, -50%) rotate(-45deg);
}

.record-detail-photo-state {
  position: relative;
  display: flex;
  width: 100%;
  height: 100%;
  overflow: hidden;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #dceecb, #cfe7f5 58%, #fff0bd);
}

.record-detail-photo-state--loading {
  background: linear-gradient(115deg, #dceecb 0%, #eef6dc 42%, #cfe7f5 100%);
}

.record-detail-photo-state__wash {
  width: 66%;
  height: 56%;
  background: rgba(255, 250, 240, 0.46);
  border-radius: 50% 42% 48% 46%;
  box-shadow: 24rpx -10rpx 0 rgba(255, 240, 189, 0.4), -32rpx 18rpx 0 rgba(207, 231, 245, 0.5);
}

.record-detail-photo-state--error {
  flex-direction: column;
  gap: 12rpx;
  padding: 24rpx;
  text-align: center;
  color: #8a5a3d;
  background: linear-gradient(135deg, #fff0bd, #fff7e8 56%, #f5d9cd);
}

.record-detail-photo-state--error text {
  font-size: 23rpx;
  font-weight: 900;
}

.record-detail-photo-state--error button {
  min-width: 138rpx;
  min-height: 48rpx;
  padding: 0 18rpx;
  font-size: 22rpx;
  font-weight: 900;
  color: #fff;
  background: #d96b34;
  border-radius: 999rpx;
}

.record-detail-cover-option__title {
  display: block;
  overflow: hidden;
  margin-top: 10rpx;
  font-size: 22rpx;
  font-weight: 900;
  color: #5e3c22;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.record-detail-cover-option__mark {
  position: absolute;
  top: 18rpx;
  right: 18rpx;
  padding: 3rpx 10rpx;
  font-size: 19rpx;
  font-weight: 900;
  color: #fff;
  background: #719b58;
  border-radius: 999rpx;
}

.record-detail-editor__empty {
  display: block;
  margin-top: 14rpx;
  font-size: 24rpx;
  line-height: 1.5;
  color: #6b765a;
}

.record-detail-editor__save {
  width: 100%;
  margin-top: 32rpx;
  font-size: 28rpx;
  font-weight: 900;
  color: #fff;
  background: #f26a21;
  border-radius: 999rpx;
}

.record-detail-editor__save[disabled] {
  color: #9b8068;
  background: #ead8b8;
}

.record-detail-finalize-action {
  padding: 26rpx 24rpx;
  margin: -8rpx 0 34rpx;
  background: rgba(255, 245, 226, 0.9);
  border: 2rpx dashed rgba(163, 98, 62, 0.58);
  border-radius: 22rpx;
}

.record-detail-finalize-action__hint {
  display: block;
  margin-bottom: 18rpx;
  font-size: 23rpx;
  line-height: 1.5;
  color: #8a5a3d;
}

.record-detail-finalize-action__button {
  width: 100%;
  font-size: 27rpx;
  font-weight: 900;
  color: #995031;
  background: #fff6e7;
  border: 2rpx solid rgba(163, 98, 62, 0.62);
  border-radius: 999rpx;
}

.record-detail-finalize-action__button[disabled] {
  color: #9b8068;
  background: #ead8b8;
  border-color: #ead8b8;
}

.record-detail-section-head {
  display: flex;
  gap: 14rpx;
  align-items: center;
  margin: 18rpx 0 24rpx;
  font-size: 34rpx;
  font-weight: 900;
}

.record-detail-section-head__line {
  flex: 1;
  border-top: 3rpx dashed rgba(244, 170, 35, 0.5);
}

.record-detail-section-head__camera {
  position: relative;
  width: 28rpx;
  height: 22rpx;
  border: 3rpx solid #8a6d54;
  border-radius: 6rpx;
}

.record-detail-section-head__camera::before {
  position: absolute;
  top: -8rpx;
  left: 6rpx;
  width: 10rpx;
  height: 7rpx;
  content: '';
  background: #8a6d54;
  border-radius: 3rpx 3rpx 0 0;
}

.record-detail-section-head__camera::after {
  position: absolute;
  top: 5rpx;
  left: 8rpx;
  width: 7rpx;
  height: 7rpx;
  content: '';
  background: #8a6d54;
  border-radius: 50%;
}

.record-detail-entry-list {
  display: flex;
  flex-direction: column;
  gap: 28rpx;
}

.record-detail-entry {
  display: grid;
  grid-template-columns: minmax(0, 0.98fr) minmax(0, 1fr);
  gap: 22rpx;
  align-items: center;
}

.record-detail-entry:nth-child(even) .record-detail-entry__photo {
  order: 2;
}

.record-detail-entry:nth-child(even) .record-detail-entry__note {
  order: 1;
}

.record-detail-entry__note {
  min-width: 0;
  min-height: 230rpx;
  padding: 26rpx 22rpx;
  border-width: 2rpx;
  border-radius: 18rpx;
}

.record-detail-entry__head {
  display: flex;
  gap: 10rpx;
  align-items: flex-start;
  justify-content: space-between;
}

.record-detail-entry__title {
  min-width: 0;
  font-size: 30rpx;
  line-height: 1.28;
}

.record-detail-entry__status {
  flex-shrink: 0;
  color: #55753c;
  background: #dceecb;
}

.record-detail-entry__subtitle,
.record-detail-entry__date {
  margin-top: 12rpx;
  font-size: 23rpx;
  color: #6b482d;
}

.record-detail-entry__dash {
  height: 2rpx;
  margin: 16rpx 0;
  border-top: 3rpx dashed rgba(223, 189, 131, 0.55);
}

.record-detail-entry__text {
  display: block;
  font-size: 24rpx;
}

.record-detail-entry__text--empty {
  color: #8a6d54;
}

.record-detail-empty-entries,
.record-detail-finalized {
  padding: 34rpx 28rpx;
  margin-bottom: 28rpx;
  font-size: 27rpx;
  line-height: 1.55;
  color: #6b482d;
  border-radius: 24rpx;
}

.record-detail-finalized {
  color: #55753c;
  background: #eef6dc;
  border-color: rgba(123, 154, 80, 0.42);
}

.record-detail-refresh-error {
  display: flex;
  justify-content: space-between;
  gap: 16rpx;
  padding: 16rpx 22rpx;
  margin-bottom: 20rpx;
  font-size: 23rpx;
  color: #9a421b;
  background: #fff1d8;
  border: 2rpx dashed rgba(217, 75, 18, 0.42);
  border-radius: 18rpx;
}

.record-detail-refresh-error text:last-child {
  font-weight: 900;
  text-decoration: underline;
}

@media (min-width: 431px) {
  .record-detail-page__paper {
    padding: calc(18px + env(safe-area-inset-top)) 18px calc(70px + env(safe-area-inset-bottom));
  }

  .record-detail-header__title {
    font-size: 28px;
  }

  .record-detail-title-card__title {
    font-size: 25px;
  }

  .record-detail-entry__title,
  .record-detail-section-title {
    font-size: 18px;
  }

  .record-detail-summary__text,
  .record-detail-entry__text {
    font-size: 15px;
  }
}
.record-detail-page {
  position: relative;
  isolation: isolate;
}

.record-detail-page__paper {
  max-width: var(--tl-content-max-width, 430px);
}

.record-detail-title-card,
.record-detail-summary,
.record-detail-editor,
.record-detail-finalize-action,
.record-detail-entry__note {
  overflow: hidden;
  background-image: linear-gradient(90deg, transparent 0 22rpx, rgba(216, 171, 105, 0.12) 22rpx 24rpx, transparent 24rpx);
}

.record-detail-title-card::after,
.record-detail-summary::after,
.record-detail-editor::after {
  position: absolute;
  right: 18rpx;
  bottom: 16rpx;
  width: 46rpx;
  height: 24rpx;
  content: '';
  pointer-events: none;
  border-bottom: 3rpx solid rgba(123, 154, 80, 0.26);
  border-radius: 50%;
  transform: rotate(-12deg);
}

.record-detail-overview__cover,
.record-detail-entry__photo {
  filter: saturate(0.96);
}

.record-detail-editor {
  background-color: rgba(238, 246, 220, 0.88);
}

.record-detail-finalize-action {
  background-color: rgba(255, 247, 232, 0.95);
}

.record-detail-finalized {
  color: #55753c;
  background: rgba(231, 243, 215, 0.9);
}

@media (max-width: 370px) {
  .record-detail-page__paper {
    padding-right: 24rpx;
    padding-left: 24rpx;
  }

  .record-detail-overview,
  .record-detail-entry {
    grid-template-columns: 1fr;
  }

  .record-detail-overview__stats {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .record-detail-entry:nth-child(even) .record-detail-entry__photo,
  .record-detail-entry:nth-child(even) .record-detail-entry__note {
    order: initial;
  }
}
</style>
